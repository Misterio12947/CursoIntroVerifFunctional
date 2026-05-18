"""
==============================================================================
Lab 3 — Skeleton del alumno: Verificación de una ALU con pyUVM.
==============================================================================

OBJETIVO DEL LABORATORIO
------------------------
Implementar un testbench pyUVM completo para una ALU de 8 bits. Practicarás
la arquitectura UVM industrial completa:

    1. Modelo de referencia puro (golden_alu).
    2. Sequence + sequence_item: separar "qué hacer" de "cómo aplicarlo".
    3. Driver: aplicar transacciones al DUT vía sus señales.
    4. Monitor: observar el DUT y publicar transacciones vistas.
    5. TLM analysis_fifo: comunicación monitor → scoreboard.
    6. Scoreboard: comparar transacciones contra el modelo.
    7. Test/Env/Agent: árbol jerárquico de componentes.

CÓMO USAR ESTE ARCHIVO
----------------------
- Busca los marcadores `TODO N:` y rellena el código que falta.
- Lee los `HINT:` para orientarte.
- Si te bloqueas, consulta:
    - solutions/lab3_alu_uvm/alu_uvm_reference.md  (arquitectura).
    - solutions/lab3_alu_uvm/expected_output.log   (salida esperada).
    - solutions/lab3_alu_uvm/test_alu.py           (último recurso).

CÓMO EJECUTAR
-------------
Desde esta carpeta:

    make                              # ejecuta el testbench UVM
    make waves                        # con generación de VCD
    make clean                        # elimina artefactos

ARQUITECTURA QUE VAS A CONSTRUIR
--------------------------------
    AluTest (uvm_test)
      └─ AluEnv (uvm_env)
          ├─ AluAgent (uvm_agent)
          │   ├─ AluDriver (uvm_driver)        ← TODO 4a, 4b
          │   ├─ AluMonitor (uvm_monitor)      ← TODO 5a, 5b
          │   └─ AluSequencer (uvm_sequencer)  ← ya listo
          └─ AluScoreboard (uvm_component)     ← TODO 6, 7
    + AluTransaction (uvm_sequence_item)       ← TODO 2
    + AluSequence    (uvm_sequence)            ← TODO 3
    + golden_alu()   (modelo de referencia)    ← TODO 1
    + @cocotb.test() wrapper                   ← TODO 8

Lectura recomendada antes de empezar:
solutions/lab3_alu_uvm/alu_uvm_reference.md
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
# Constantes (no modifiques).
# ============================================================================
CLK_PERIOD_NS  = 10
N_TRANSACTIONS = 50
SEED           = 0xC0FFEE

# Códigos de operación (deben coincidir con rtl/alu.v).
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


# ============================================================================
# TODO 1: golden_alu
# ----------------------------------------------------------------------------
# Modelo de referencia puro. Devuelve (result, zero, carry) para cada op.
#
# Reglas (las mismas que el RTL):
#   ADD : result = (a + b) & 0xFF       carry = (a+b) >> 8
#   SUB : result = (a - b) & 0xFF       carry = 1 si b > a, sino 0
#   AND : result = a & b                carry = 0
#   OR  : result = a | b                carry = 0
#   XOR : result = a ^ b                carry = 0
#   SHL : result = (a << 1) & 0xFF      carry = (a >> 7) & 1
#   SHR : result = a >> 1               carry = a & 1
#   NOP : result = prev_result          carry = 0
#   zero = 1 si result == 0 sino 0
#
# HINT: usa if/elif sobre op. Termina cada rama con un valor para `result`
# y `carry`. zero se deduce al final.
# ============================================================================
def golden_alu(op, a, b, prev_result):
    """Modelo de referencia. Devuelve (result, zero, carry)."""
    # TODO 1: implementa cada operación.
    raise NotImplementedError("TODO 1: implementa golden_alu")


# ============================================================================
# Transaction: AluTransaction
# ============================================================================
class AluTransaction(uvm_sequence_item):
    """Transacción ALU: entradas (a, b, op) + salidas observadas."""

    def __init__(self, name="alu_tr"):
        super().__init__(name)
        # Entradas.
        self.a  = 0
        self.b  = 0
        self.op = 0
        # Salidas observadas (las llenará el monitor).
        self.result = 0
        self.zero   = 0
        self.carry  = 0

    # ------------------------------------------------------------------------
    # TODO 2: randomize
    # ------------------------------------------------------------------------
    # Genera valores aleatorios usando el RNG externo (`rng`, no `random`
    # global, para reproducibilidad con seed fija).
    #
    # HINT:
    #   self.a  = rng.randint(0, 0xFF)
    #   self.b  = rng.randint(0, 0xFF)
    #   self.op = rng.randint(0, 7)
    # ------------------------------------------------------------------------
    def randomize(self, rng):
        # TODO 2: implementa randomize.
        raise NotImplementedError("TODO 2: implementa AluTransaction.randomize")

    def __str__(self):
        return (
            f"AluTr(op={OP_NAMES.get(self.op, '?')}, "
            f"a=0x{self.a:02X}, b=0x{self.b:02X}, "
            f"result=0x{self.result:02X}, zero={self.zero}, carry={self.carry})"
        )


# ============================================================================
# Sequence: AluSequence
# ============================================================================
class AluSequence(uvm_sequence):
    """Genera transacciones aleatorias. Lee N y SEED de ConfigDB."""

    def __init__(self, name="alu_seq"):
        super().__init__(name)
        # Estos campos los lee el alumno del ConfigDB.
        self.n_transactions = ConfigDB().get(None, "", "N_TRANSACTIONS")
        seed                = ConfigDB().get(None, "", "SEED")
        self.rng            = random.Random(seed)

    # ------------------------------------------------------------------------
    # TODO 3: body
    # ------------------------------------------------------------------------
    # Loop que envía N transacciones al sequencer. Por cada iteración:
    #   1. Crea una AluTransaction.
    #   2. Llama a tr.randomize(self.rng).
    #   3. await self.start_item(tr)
    #   4. await self.finish_item(tr)
    #
    # HINT: for _ in range(self.n_transactions): ...
    # ------------------------------------------------------------------------
    async def body(self):
        # TODO 3: implementa el body de la sequence.
        raise NotImplementedError("TODO 3: implementa AluSequence.body")


# ============================================================================
# Driver: AluDriver
# ============================================================================
class AluDriver(uvm_driver):
    """Aplica AluTransactions al DUT vía sus señales a/b/op/start."""

    # ------------------------------------------------------------------------
    # TODO 4a: build_phase
    # ------------------------------------------------------------------------
    # Asigna self.dut. En pyUVM con cocotb, el DUT global está disponible
    # como cocotb.top.
    #
    # HINT:
    #   self.dut = cocotb.top
    # ------------------------------------------------------------------------
    def build_phase(self):
        # TODO 4a: asigna self.dut desde cocotb.top.
        raise NotImplementedError("TODO 4a: implementa AluDriver.build_phase")

    async def run_phase(self):
        # Estado inicial de las entradas del DUT.
        self.dut.start.value = 0
        self.dut.a.value     = 0
        self.dut.b.value     = 0
        self.dut.op.value    = 0

        while True:
            tr = await self.seq_item_port.get_next_item()
            await self._drive(tr)
            self.seq_item_port.item_done()

    # ------------------------------------------------------------------------
    # TODO 4b: _drive
    # ------------------------------------------------------------------------
    # Aplica una transacción al DUT durante 1 ciclo de start=1.
    #
    # Pasos:
    #   1. await RisingEdge(self.dut.clk)
    #   2. Carga a, b, op desde tr; pone start=1.
    #   3. await RisingEdge(self.dut.clk)
    #   4. Baja start=0.
    #   5. Un ciclo extra para que la próxima transacción no solape.
    # ------------------------------------------------------------------------
    async def _drive(self, tr):
        # TODO 4b: implementa _drive.
        raise NotImplementedError("TODO 4b: implementa AluDriver._drive")


# ============================================================================
# Monitor: AluMonitor
# ============================================================================
class AluMonitor(uvm_monitor):
    """Observa el DUT y publica AluTransaction al analysis_port."""

    # ------------------------------------------------------------------------
    # TODO 5a: build_phase
    # ------------------------------------------------------------------------
    # Asigna self.dut y crea el analysis_port "ap".
    #
    # HINT:
    #   self.dut = cocotb.top
    #   self.analysis_port = self.create_analysis_port("ap")
    # ------------------------------------------------------------------------
    def build_phase(self):
        # TODO 5a: implementa build_phase.
        raise NotImplementedError("TODO 5a: implementa AluMonitor.build_phase")

    def create_analysis_port(self, name):
        from pyuvm import uvm_analysis_port
        return uvm_analysis_port(name, self)

    # ------------------------------------------------------------------------
    # TODO 5b: run_phase
    # ------------------------------------------------------------------------
    # Observa el DUT cada flanco. Como el resultado llega un ciclo después
    # de start=1, necesitas un buffer (`pending`) que guarde las entradas
    # capturadas en el ciclo de start=1 y las recupere cuando done=1.
    #
    # Algoritmo:
    #   pending = deque()
    #   while True:
    #       await RisingEdge(dut.clk)
    #       await Timer(1, "ns")          # margen tras flanco
    #       if dut.start == 1:
    #           pending.append((int(dut.a), int(dut.b), int(dut.op)))
    #       if dut.done == 1 and len(pending) > 0:
    #           a, b, op = pending.popleft()
    #           tr = AluTransaction()
    #           tr.a = a; tr.b = b; tr.op = op
    #           tr.result = int(dut.result.value)
    #           tr.zero   = int(dut.zero.value)
    #           tr.carry  = int(dut.carry.value)
    #           self.analysis_port.write(tr)
    # ------------------------------------------------------------------------
    async def run_phase(self):
        # TODO 5b: implementa run_phase con buffer de pending entradas.
        raise NotImplementedError("TODO 5b: implementa AluMonitor.run_phase")


# ============================================================================
# Sequencer: AluSequencer  (NO MODIFICAR — sin lógica propia)
# ============================================================================
class AluSequencer(uvm_sequencer):
    pass


# ============================================================================
# Agent: AluAgent  (NO MODIFICAR — solo instancia hijos)
# ============================================================================
class AluAgent(uvm_agent):
    def build_phase(self):
        self.driver    = AluDriver("driver", self)
        self.monitor   = AluMonitor("monitor", self)
        self.sequencer = AluSequencer("sequencer", self)

    def connect_phase(self):
        self.driver.seq_item_port.connect(self.sequencer.seq_item_export)


# ============================================================================
# Scoreboard: AluScoreboard
# ============================================================================
class AluScoreboard(uvm_component):
    """Compara transacciones del monitor contra el modelo de referencia."""

    def build_phase(self):
        self.fifo = uvm_tlm_analysis_fifo("fifo", self)
        self.prev_result = 0
        self.n_received  = 0
        self.n_passed    = 0
        self.n_failed    = 0
        self.n_expected  = ConfigDB().get(None, "", "N_TRANSACTIONS")

    # ------------------------------------------------------------------------
    # TODO 6: run_phase
    # ------------------------------------------------------------------------
    # Loop infinito que:
    #   1. await self.fifo.get_export.get() para obtener una transacción.
    #   2. Incrementa self.n_received.
    #   3. Llama a self._check(tr).
    # ------------------------------------------------------------------------
    async def run_phase(self):
        # TODO 6: implementa run_phase.
        raise NotImplementedError("TODO 6: implementa AluScoreboard.run_phase")

    # ------------------------------------------------------------------------
    # TODO 7: _check
    # ------------------------------------------------------------------------
    # Compara la transacción contra golden_alu y actualiza prev_result.
    #
    # Pasos:
    #   1. exp_result, exp_zero, exp_carry = golden_alu(tr.op, tr.a, tr.b,
    #                                                  self.prev_result)
    #   2. ok = (tr.result == exp_result and tr.zero == exp_zero
    #            and tr.carry == exp_carry)
    #   3. Si ok: self.n_passed += 1, log debug.
    #      Si no: self.n_failed += 1, log error con valores.
    #   4. self.prev_result = exp_result  (actualiza estado del modelo).
    # ------------------------------------------------------------------------
    def _check(self, tr):
        # TODO 7: implementa _check.
        raise NotImplementedError("TODO 7: implementa AluScoreboard._check")

    def report_phase(self):
        """Reporte final. (Esta sección está completa, no la modifiques.)"""
        self.logger.info(
            "Scoreboard report: received=%d, passed=%d, failed=%d",
            self.n_received, self.n_passed, self.n_failed,
        )
        assert self.n_failed == 0, (
            f"Scoreboard detectó {self.n_failed} discrepancias."
        )
        assert self.n_received == self.n_expected, (
            f"Se esperaban {self.n_expected} transacciones, "
            f"recibidas {self.n_received}."
        )


# ============================================================================
# Env: AluEnv  (NO MODIFICAR)
# ============================================================================
class AluEnv(uvm_env):
    def build_phase(self):
        self.agent      = AluAgent("agent", self)
        self.scoreboard = AluScoreboard("scoreboard", self)

    def connect_phase(self):
        self.agent.monitor.analysis_port.connect(
            self.scoreboard.fifo.analysis_export
        )


# ============================================================================
# Test: AluTest  (NO MODIFICAR — solo construye env y arranca sequence)
# ============================================================================
class AluTest(uvm_test):
    def build_phase(self):
        self.env = AluEnv("env", self)

    async def run_phase(self):
        self.raise_objection()
        seq = AluSequence("alu_seq")
        await seq.start(self.env.agent.sequencer)
        await Timer(50, units="ns")
        self.drop_objection()


# ============================================================================
# TODO 8: wrapper @cocotb.test()
# ----------------------------------------------------------------------------
# Pasos:
#   1. Arranca el reloj: cocotb.start_soon(Clock(dut.clk, CLK_PERIOD_NS,
#                                                units="ns").start())
#   2. Reset síncrono durante 3 ciclos, luego baja rst.
#   3. ConfigDB().set(None, "*", "N_TRANSACTIONS", N_TRANSACTIONS)
#   4. ConfigDB().set(None, "*", "SEED",           SEED)
#   5. await uvm_root().run_test("AluTest")
# ============================================================================
@cocotb.test()
async def alu_uvm_test(dut):
    """Punto de entrada del testbench UVM."""
    # TODO 8: implementa el wrapper (reloj, reset, ConfigDB, run_test).
    raise NotImplementedError("TODO 8: implementa el wrapper @cocotb.test()")
