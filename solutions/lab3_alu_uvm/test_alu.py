"""
==============================================================================
Lab 3 — Solución Maestra: Verificación de una ALU con pyUVM.
==============================================================================

Esta solución introduce el patrón UVM industrial completo aplicado a una
ALU de 8 bits. Por primera vez en el curso usamos:

    1. Un test estructurado como árbol de componentes (Test → Env → Agent
       → Driver/Monitor/Sequencer + Scoreboard).
    2. Comunicación entre componentes vía TLM (Transaction-Level Modeling)
       usando uvm_tlm_analysis_fifo.
    3. Configuración vía ConfigDB (inyección del DUT a los componentes).
    4. Sequence + sequence_item: separación entre "qué se hace" (sequence)
       y "cómo se aplica al DUT" (driver).

Mapeo conceptual cocotb plano (Lab 1) → UVM (Lab 3):

    cocotb (Lab 1)                  | UVM (Lab 3)
    --------------------------------|-----------------------------------
    cocotb.start_soon(corrutina)    | uvm_component con run_phase async
    señales globales en el test     | ConfigDB.set / ConfigDB.get
    cola/lista compartida           | uvm_tlm_analysis_fifo
    test = corrutina única          | árbol Test → Env → Agent → ...
    helpers push/pop                | Driver + Sequence + Sequence_item

El mismo trabajo se hace, pero distribuido en componentes con
responsabilidades únicas. Esto es lo que escala a diseños grandes.

Componentes en este archivo:
    - AluTransaction       (uvm_sequence_item)
    - AluSequence          (uvm_sequence)
    - AluDriver            (uvm_driver)
    - AluMonitor           (uvm_monitor)
    - AluSequencer         (uvm_sequencer, sin lógica propia)
    - AluAgent             (uvm_agent)
    - AluScoreboard        (uvm_component)
    - AluEnv               (uvm_env)
    - AluTest              (uvm_test)

Más un wrapper @cocotb.test() que arranca uvm_root().run_test("AluTest").
==============================================================================
"""

import random
from collections import deque

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, Timer

from pyuvm import (
    uvm_sequence_item,
    uvm_sequence,
    uvm_driver,
    uvm_monitor,
    uvm_sequencer,
    uvm_agent,
    uvm_component,
    uvm_env,
    uvm_test,
    uvm_root,
    ConfigDB,
    uvm_tlm_analysis_fifo,
)


# ============================================================================
# Constantes y modelo de referencia
# ============================================================================
CLK_PERIOD_NS = 10
N_TRANSACTIONS = 50
SEED = 0xC0FFEE

# Códigos de operación (coinciden con rtl/alu.v).
OP_ADD = 0
OP_SUB = 1
OP_AND = 2
OP_OR  = 3
OP_XOR = 4
OP_SHL = 5
OP_SHR = 6
OP_NOP = 7

OP_NAMES = {
    OP_ADD: "ADD", OP_SUB: "SUB", OP_AND: "AND", OP_OR:  "OR",
    OP_XOR: "XOR", OP_SHL: "SHL", OP_SHR: "SHR", OP_NOP: "NOP",
}


def golden_alu(op, a, b, prev_result):
    """Modelo de referencia puro. Devuelve (result, zero, carry).

    NOP devuelve `prev_result` (la ALU mantiene su estado).
    """
    mask = 0xFF

    if op == OP_ADD:
        full = a + b
        result = full & mask
        carry  = (full >> 8) & 1
    elif op == OP_SUB:
        result = (a - b) & mask
        carry  = 1 if b > a else 0
    elif op == OP_AND:
        result = a & b
        carry  = 0
    elif op == OP_OR:
        result = a | b
        carry  = 0
    elif op == OP_XOR:
        result = a ^ b
        carry  = 0
    elif op == OP_SHL:
        result = (a << 1) & mask
        carry  = (a >> 7) & 1
    elif op == OP_SHR:
        result = a >> 1
        carry  = a & 1
    elif op == OP_NOP:
        result = prev_result
        carry  = 0
    else:
        raise ValueError(f"Operación desconocida: op={op}")

    zero = 1 if result == 0 else 0
    return result, zero, carry


# ============================================================================
# Transaction: AluTransaction
# ----------------------------------------------------------------------------
# Encapsula entradas (a, b, op) y salidas observadas (result, zero, carry).
# La sequence rellena las entradas; el monitor rellena las salidas; el
# scoreboard compara las salidas contra golden_alu(entradas).
# ============================================================================
class AluTransaction(uvm_sequence_item):
    """Transacción ALU: entradas + salidas observadas."""

    def __init__(self, name="alu_tr"):
        super().__init__(name)
        # Entradas.
        self.a  = 0
        self.b  = 0
        self.op = 0
        # Salidas observadas (las llena el monitor).
        self.result = 0
        self.zero   = 0
        self.carry  = 0

    def randomize(self, rng):
        """Genera valores aleatorios usando el RNG externo (seed reproducible)."""
        self.a  = rng.randint(0, 0xFF)
        self.b  = rng.randint(0, 0xFF)
        self.op = rng.randint(0, 7)

    def __str__(self):
        return (
            f"AluTr(op={OP_NAMES.get(self.op, '?')}, "
            f"a=0x{self.a:02X}, b=0x{self.b:02X}, "
            f"result=0x{self.result:02X}, zero={self.zero}, carry={self.carry})"
        )


# ============================================================================
# Sequence: AluSequence
# ----------------------------------------------------------------------------
# Genera N transacciones aleatorias y las envía al sequencer.
# Es una corrutina async porque puede esperar (await) entre transacciones
# si fuera necesario (no en este caso, pero el patrón lo soporta).
# ============================================================================
class AluSequence(uvm_sequence):
    """Genera N_TRANSACTIONS transacciones aleatorias."""

    def __init__(self, name="alu_seq"):
        super().__init__(name)
        self.rng = random.Random(SEED)

    async def body(self):
        for _ in range(N_TRANSACTIONS):
            tr = AluTransaction()
            tr.randomize(self.rng)
            await self.start_item(tr)
            await self.finish_item(tr)


# ============================================================================
# Driver: AluDriver
# ----------------------------------------------------------------------------
# En run_phase, espera transacciones del sequencer y las aplica al DUT.
# El DUT se recupera del ConfigDB (inyectado por el @cocotb.test wrapper).
# ============================================================================
class AluDriver(uvm_driver):
    """Aplica AluTransactions al DUT vía sus señales a/b/op/start."""

    def build_phase(self):
        # Recupera el dut del ConfigDB. La key "DUT" la pone el wrapper.
        self.dut = ConfigDB().get(self, "", "DUT")

    async def run_phase(self):
        # Estado inicial.
        self.dut.start.value = 0
        self.dut.a.value     = 0
        self.dut.b.value     = 0
        self.dut.op.value    = 0

        while True:
            tr = await self.seq_item_port.get_next_item()
            await self._drive(tr)
            self.seq_item_port.item_done()

    async def _drive(self, tr):
        """Aplica una transacción: pulso start=1 durante un ciclo."""
        await RisingEdge(self.dut.clk)
        self.dut.a.value     = tr.a
        self.dut.b.value     = tr.b
        self.dut.op.value    = tr.op
        self.dut.start.value = 1
        await RisingEdge(self.dut.clk)
        self.dut.start.value = 0
        # Damos un ciclo extra para separar transacciones consecutivas.
        await RisingEdge(self.dut.clk)


# ============================================================================
# Monitor: AluMonitor
# ----------------------------------------------------------------------------
# Observa el DUT. Cada vez que done=1, construye una transacción "vista"
# (con los valores reales que el DUT produjo) y la publica al analysis_port.
#
# Para reconstruir las entradas (a, b, op) del momento en que el cálculo se
# disparó, el monitor las captura cuando ve start=1, y las recupera cuando
# done=1 un ciclo después.
# ============================================================================
class AluMonitor(uvm_monitor):
    """Observa el DUT y publica AluTransaction al analysis_port."""

    def build_phase(self):
        self.dut = ConfigDB().get(self, "", "DUT")
        # Analysis port: el scoreboard se conecta aquí.
        self.analysis_port = self.create_analysis_port("ap")

    def create_analysis_port(self, name):
        from pyuvm import uvm_analysis_port
        return uvm_analysis_port(name, self)

    async def run_phase(self):
        # Buffer de entradas capturadas en el momento de start=1.
        # Necesario porque el resultado aparece un ciclo después.
        pending = deque()

        while True:
            await RisingEdge(self.dut.clk)
            # Pequeño margen tras el flanco para muestrear señales estables.
            await Timer(1, units="ns")

            # Captura entradas en el ciclo de start=1.
            if int(self.dut.start.value) == 1:
                pending.append((
                    int(self.dut.a.value),
                    int(self.dut.b.value),
                    int(self.dut.op.value),
                ))

            # Cuando done=1, construye la transacción vista y publícala.
            if int(self.dut.done.value) == 1 and len(pending) > 0:
                a, b, op = pending.popleft()
                tr = AluTransaction()
                tr.a      = a
                tr.b      = b
                tr.op     = op
                tr.result = int(self.dut.result.value)
                tr.zero   = int(self.dut.zero.value)
                tr.carry  = int(self.dut.carry.value)
                self.analysis_port.write(tr)


# ============================================================================
# Sequencer: AluSequencer
# ----------------------------------------------------------------------------
# Sin lógica propia. Solo nombre y herencia. Conecta sequences con drivers.
# ============================================================================
class AluSequencer(uvm_sequencer):
    """Sequencer estándar. Sin lógica adicional."""
    pass


# ============================================================================
# Agent: AluAgent
# ----------------------------------------------------------------------------
# Instancia driver + monitor + sequencer.
# Conecta driver.seq_item_port <-> sequencer.seq_item_export.
# ============================================================================
class AluAgent(uvm_agent):
    """Contiene driver, monitor y sequencer."""

    def build_phase(self):
        self.driver    = AluDriver("driver", self)
        self.monitor   = AluMonitor("monitor", self)
        self.sequencer = AluSequencer("sequencer", self)

    def connect_phase(self):
        self.driver.seq_item_port.connect(self.sequencer.seq_item_export)


# ============================================================================
# Scoreboard: AluScoreboard
# ----------------------------------------------------------------------------
# Recibe transacciones del monitor vía un uvm_tlm_analysis_fifo.
# En run_phase hace await fifo.get_export.get() para leer cada transacción
# y la compara contra el modelo de referencia (golden_alu).
#
# Mantiene estado:
#   - prev_result: necesario para verificar NOP (la ALU debe mantener el
#     resultado anterior).
#   - n_received, n_passed, n_failed: contadores para el reporte final.
# ============================================================================
class AluScoreboard(uvm_component):
    """Compara transacciones del monitor contra el modelo de referencia."""

    def build_phase(self):
        self.fifo = uvm_tlm_analysis_fifo("fifo", self)
        self.prev_result = 0
        self.n_received  = 0
        self.n_passed    = 0
        self.n_failed    = 0

    async def run_phase(self):
        while True:
            tr = await self.fifo.get_export.get()
            self.n_received += 1
            self._check(tr)

    def _check(self, tr):
        """Compara la transacción observada contra golden_alu."""
        exp_result, exp_zero, exp_carry = golden_alu(
            tr.op, tr.a, tr.b, self.prev_result,
        )

        ok = (
            tr.result == exp_result and
            tr.zero   == exp_zero   and
            tr.carry  == exp_carry
        )

        if ok:
            self.n_passed += 1
            self.logger.debug("[SBD PASS] %s", tr)
        else:
            self.n_failed += 1
            self.logger.error(
                "[SBD FAIL] %s | esperado: result=0x%02X zero=%d carry=%d",
                tr, exp_result, exp_zero, exp_carry,
            )

        # Actualiza el modelo: en NOP el resultado se mantiene, en cualquier
        # otra op se actualiza. Esto es lo que el DUT hace.
        self.prev_result = exp_result

    def report_phase(self):
        """Reporte final. Asserta que no hubo fallos."""
        self.logger.info(
            "Scoreboard report: received=%d, passed=%d, failed=%d",
            self.n_received, self.n_passed, self.n_failed,
        )
        assert self.n_failed == 0, (
            f"Scoreboard detectó {self.n_failed} discrepancias."
        )
        assert self.n_received == N_TRANSACTIONS, (
            f"Se esperaban {N_TRANSACTIONS} transacciones, "
            f"recibidas {self.n_received}."
        )


# ============================================================================
# Environment: AluEnv
# ----------------------------------------------------------------------------
# Instancia agent + scoreboard.
# Conecta monitor.analysis_port -> scoreboard.fifo.analysis_export.
# ============================================================================
class AluEnv(uvm_env):
    """Entorno: agente + scoreboard."""

    def build_phase(self):
        self.agent      = AluAgent("agent", self)
        self.scoreboard = AluScoreboard("scoreboard", self)

    def connect_phase(self):
        self.agent.monitor.analysis_port.connect(
            self.scoreboard.fifo.analysis_export
        )


# ============================================================================
# Test: AluTest
# ----------------------------------------------------------------------------
# Construye el env, arranca la sequence.
# ============================================================================
class AluTest(uvm_test):
    """Test principal. Lanza AluSequence sobre el sequencer del agent."""

    def build_phase(self):
        self.env = AluEnv("env", self)

    async def run_phase(self):
        self.raise_objection()
        seq = AluSequence("alu_seq")
        await seq.start(self.env.agent.sequencer)
        # Pequeño margen para que el monitor procese la última transacción.
        await Timer(50, units="ns")
        self.drop_objection()


# ============================================================================
# Wrapper @cocotb.test()
# ----------------------------------------------------------------------------
# - Arranca el reloj.
# - Aplica reset.
# - Registra el dut en ConfigDB para que driver y monitor lo encuentren.
# - Llama a uvm_root().run_test("AluTest").
# ============================================================================
@cocotb.test()
async def alu_uvm_test(dut):
    """Punto de entrada del testbench UVM."""

    # 1. Reloj.
    cocotb.start_soon(Clock(dut.clk, CLK_PERIOD_NS, units="ns").start())

    # 2. Reset síncrono.
    dut.rst.value   = 1
    dut.start.value = 0
    dut.a.value     = 0
    dut.b.value     = 0
    dut.op.value    = 0
    for _ in range(3):
        await RisingEdge(dut.clk)
    dut.rst.value = 0
    await RisingEdge(dut.clk)

    # 3. Inyecta el DUT en el ConfigDB.
    ConfigDB().set(None, "uvm_test_top.env.agent.driver",  "DUT", dut)
    ConfigDB().set(None, "uvm_test_top.env.agent.monitor", "DUT", dut)

    # 4. Arranca el test UVM.
    await uvm_root().run_test("AluTest")
