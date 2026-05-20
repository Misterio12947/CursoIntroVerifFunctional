"""
==============================================================================
Lab 4 — Solución Maestra: Verificación de una FPU IEEE 754 con pyUVM.
==============================================================================

Este lab extiende el patrón UVM del Lab 3 (ALU) a una FPU de suma flotante
32-bit. Conceptos nuevos:

    1. Modelo de referencia con numpy.float32 (en lugar de aritmética entera).
    2. Comparación con TOLERANCIA (±1 ULP) en lugar de igualdad exacta.
    3. Generación de operandos IEEE 754 "seguros" (evitando NaN, Inf, denormales).
    4. (Paso 5) Cobertura funcional con cocotb_coverage.

Reutiliza la arquitectura UVM del Lab 3:
    FpuTest → FpuEnv → FpuAgent (Driver+Monitor+Sequencer) + FpuScoreboard
    Comunicación monitor → scoreboard vía uvm_tlm_analysis_fifo.

Diferencias clave respecto al Lab 3:
    - Transacciones con operandos de 32 bits y resultado de 32 bits.
    - Modelo: numpy.float32 (no tabla de opcodes).
    - Tolerancia ±1 ULP en el scoreboard (no igualdad).
==============================================================================
"""

import random

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, Timer

import numpy as np

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
    uvm_tlm_analysis_fifo,
)


# ============================================================================
# Constantes.
# ============================================================================
CLK_PERIOD_NS  = 10
N_TRANSACTIONS = 200
SEED           = 0xC0FFEE


# ============================================================================
# Helpers IEEE 754.
# ============================================================================
def random_safe_float32(rng):
    """Genera un float32 aleatorio en formato IEEE 754 bits (uint32).

    Evita:
    - Exponente 0 (denormales o cero, problemáticos con flush-to-zero del DUT).
    - Exponente 255 (NaN/Inf, no soportados por el DUT).
    - Para mantener el rango razonable, exponente entre 60 y 200 (~10⁻²⁰ a 10²²).

    Signo y mantisa totalmente aleatorios.
    """
    sign     = rng.randint(0, 1)
    exponent = rng.randint(60, 200)
    mantissa = rng.randint(0, (1 << 23) - 1)
    return (sign << 31) | (exponent << 23) | mantissa


def bits_to_float32(bits):
    """uint32 → numpy.float32 (interpretación de bits)."""
    return np.frombuffer(np.uint32(bits).tobytes(), dtype=np.float32)[0]


def float32_to_bits(f):
    """numpy.float32 → uint32 (bits)."""
    return int(np.frombuffer(np.float32(f).tobytes(), dtype=np.uint32)[0])


def golden_fadd(a_bits, b_bits):
    """Modelo de referencia: suma flotante IEEE 754.

    Convierte ambos operandos a numpy.float32, los suma con numpy (que aplica
    round-to-nearest-even), y devuelve los bits del resultado.
    """
    a = bits_to_float32(a_bits)
    b = bits_to_float32(b_bits)
    r = np.float32(a + b)
    return float32_to_bits(r)


def within_1_ulp(dut_bits, ref_bits):
    """Tolerancia ±1 ULP: los bits difieren a lo sumo en 1 unidad.

    Justificación: el RTL trunca, numpy redondea. Diferencias de 1 LSB en la
    mantisa son esperadas y aceptadas.
    """
    return abs(int(dut_bits) - int(ref_bits)) <= 1


# ============================================================================
# Transaction: FpuTransaction
# ============================================================================
class FpuTransaction(uvm_sequence_item):
    """Transacción FPU: operandos (a, b) + resultado observado."""

    def __init__(self, name="fpu_tr"):
        super().__init__(name)
        self.a      = 0
        self.b      = 0
        self.result = 0

    def randomize(self, rng):
        self.a = random_safe_float32(rng)
        self.b = random_safe_float32(rng)

    def __str__(self):
        return (
            f"FpuTr(a=0x{self.a:08X}={bits_to_float32(self.a):.6e}, "
            f"b=0x{self.b:08X}={bits_to_float32(self.b):.6e}, "
            f"result=0x{self.result:08X}={bits_to_float32(self.result):.6e})"
        )


# ============================================================================
# Sequence: FpuSequence
# ============================================================================
class FpuSequence(uvm_sequence):
    """Genera N_TRANSACTIONS transacciones aleatorias con seed fijo."""

    def __init__(self, name="fpu_seq"):
        super().__init__(name)
        self.rng = random.Random(SEED)

    async def body(self):
        for _ in range(N_TRANSACTIONS):
            tr = FpuTransaction()
            tr.randomize(self.rng)
            await self.start_item(tr)
            await self.finish_item(tr)


# ============================================================================
# Driver: FpuDriver
# ============================================================================
class FpuDriver(uvm_driver):
    """Aplica FpuTransactions al DUT (a, b, start)."""

    def build_phase(self):
        self.dut = cocotb.top

    async def run_phase(self):
        self.dut.start.value = 0
        self.dut.a.value     = 0
        self.dut.b.value     = 0

        while True:
            tr = await self.seq_item_port.get_next_item()
            await self._drive(tr)
            self.seq_item_port.item_done()

    async def _drive(self, tr):
        await RisingEdge(self.dut.clk)
        self.dut.a.value     = tr.a
        self.dut.b.value     = tr.b
        self.dut.start.value = 1
        await RisingEdge(self.dut.clk)
        self.dut.start.value = 0
        # Ciclo extra de separación entre transacciones.
        await RisingEdge(self.dut.clk)


# ============================================================================
# Monitor: FpuMonitor
# ============================================================================
class FpuMonitor(uvm_monitor):
    """Observa el DUT y publica FpuTransaction vía analysis_port."""

    def build_phase(self):
        self.dut = cocotb.top
        self.analysis_port = self.create_analysis_port("ap")

    def create_analysis_port(self, name):
        from pyuvm import uvm_analysis_port
        return uvm_analysis_port(name, self)

    async def run_phase(self):
        from collections import deque
        pending = deque()

        while True:
            await RisingEdge(self.dut.clk)
            await Timer(1, units="ns")

            if int(self.dut.start.value) == 1:
                pending.append((int(self.dut.a.value), int(self.dut.b.value)))

            if int(self.dut.done.value) == 1 and len(pending) > 0:
                a, b = pending.popleft()
                tr = FpuTransaction()
                tr.a      = a
                tr.b      = b
                tr.result = int(self.dut.result.value)
                self.analysis_port.write(tr)


# ============================================================================
# Sequencer: FpuSequencer
# ============================================================================
class FpuSequencer(uvm_sequencer):
    pass


# ============================================================================
# Agent: FpuAgent
# ============================================================================
class FpuAgent(uvm_agent):
    def build_phase(self):
        self.driver    = FpuDriver("driver", self)
        self.monitor   = FpuMonitor("monitor", self)
        self.sequencer = FpuSequencer("sequencer", self)

    def connect_phase(self):
        self.driver.seq_item_port.connect(self.sequencer.seq_item_export)


# ============================================================================
# Scoreboard: FpuScoreboard
# ============================================================================
class FpuScoreboard(uvm_component):
    """Compara DUT vs golden_fadd con tolerancia ±1 ULP."""

    def build_phase(self):
        self.fifo = uvm_tlm_analysis_fifo("fifo", self)
        self.n_received = 0
        self.n_passed   = 0
        self.n_failed   = 0
        self.failures   = []   # lista de tuplas (tx, expected) para reporte

    async def run_phase(self):
        while True:
            tr = await self.fifo.get_export.get()
            self.n_received += 1
            self._check(tr)

    def _check(self, tr):
        expected = golden_fadd(tr.a, tr.b)
        if within_1_ulp(tr.result, expected):
            self.n_passed += 1
            self.logger.debug("[SBD PASS] %s | esperado=0x%08X", tr, expected)
        else:
            self.n_failed += 1
            self.failures.append((tr, expected))
            self.logger.error(
                "[SBD FAIL] %s | esperado=0x%08X=%.6e (diff_ulp=%d)",
                tr, expected, bits_to_float32(expected),
                abs(int(tr.result) - int(expected)),
            )

    def report_phase(self):
        self.logger.info(
            "Scoreboard report: received=%d, passed=%d, failed=%d (±1 ULP tol.)",
            self.n_received, self.n_passed, self.n_failed,
        )
        if self.n_failed > 0:
            # Resumen de los primeros 5 fallos (suficiente para diagnóstico).
            self.logger.error("=== Primeros %d fallos ===", min(5, len(self.failures)))
            for tr, exp in self.failures[:5]:
                self.logger.error("  %s | esperado=0x%08X", tr, exp)

        assert self.n_failed == 0, (
            f"Scoreboard detectó {self.n_failed} discrepancias > 1 ULP."
        )
        assert self.n_received == N_TRANSACTIONS, (
            f"Esperaban {N_TRANSACTIONS} tx, recibidas {self.n_received}."
        )


# ============================================================================
# Env: FpuEnv
# ============================================================================
class FpuEnv(uvm_env):
    def build_phase(self):
        self.agent      = FpuAgent("agent", self)
        self.scoreboard = FpuScoreboard("scoreboard", self)

    def connect_phase(self):
        self.agent.monitor.analysis_port.connect(
            self.scoreboard.fifo.analysis_export
        )


# ============================================================================
# Test: FpuTest
# ============================================================================
class FpuTest(uvm_test):
    def build_phase(self):
        self.env = FpuEnv("env", self)

    async def run_phase(self):
        self.raise_objection()
        seq = FpuSequence("fpu_seq")
        await seq.start(self.env.agent.sequencer)
        await Timer(50, units="ns")
        self.drop_objection()


# ============================================================================
# Wrapper @cocotb.test()
# ============================================================================
@cocotb.test()
async def fpu_uvm_test(dut):
    """Punto de entrada del testbench UVM FPU."""
    cocotb.start_soon(Clock(dut.clk, CLK_PERIOD_NS, units="ns").start())

    dut.rst.value   = 1
    dut.start.value = 0
    dut.a.value     = 0
    dut.b.value     = 0
    for _ in range(3):
        await RisingEdge(dut.clk)
    dut.rst.value = 0
    await RisingEdge(dut.clk)

    await uvm_root().run_test("FpuTest")
