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

from cocotb_coverage.coverage import (
    CoverPoint,
    CoverCross,
    coverage_db,
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
# Cobertura funcional.
# ============================================================================
def _classify_exp_diff(a_bits, b_bits):
    """Clasifica la diferencia de exponentes en uno de 4 rangos."""
    exp_a = (a_bits >> 23) & 0xFF
    exp_b = (b_bits >> 23) & 0xFF
    diff = abs(int(exp_a) - int(exp_b))
    if diff == 0:
        return "equal"
    elif diff <= 3:
        return "close"
    elif diff <= 10:
        return "moderate"
    else:
        return "far"


def _classify_result_sign(result_bits):
    """Clasifica el signo del resultado: positive / negative / zero."""
    # IEEE 754: si los 31 bits inferiores son 0, es cero (independiente del signo bit).
    if (result_bits & 0x7FFFFFFF) == 0:
        return "zero"
    return "negative" if (result_bits >> 31) else "positive"


# Decoradores aplicados a sample_coverage. Cada llamada a sample_coverage
# marca un bin en cada CoverPoint según el valor de tr.
@CoverPoint("top.sign_a",
            xf=lambda tr: (tr.a >> 31) & 1,
            bins=[0, 1],
            bins_labels=["positive", "negative"])
@CoverPoint("top.sign_b",
            xf=lambda tr: (tr.b >> 31) & 1,
            bins=[0, 1],
            bins_labels=["positive", "negative"])
@CoverPoint("top.exp_diff_range",
            xf=lambda tr: _classify_exp_diff(tr.a, tr.b),
            bins=["equal", "close", "moderate", "far"])
@CoverPoint("top.result_sign",
            xf=lambda tr: _classify_result_sign(tr.result),
            bins=["positive", "negative", "zero"])
@CoverCross("top.sign_cross",
            items=["top.sign_a", "top.sign_b"])
def sample_coverage(tr):
    """Sampler de cobertura. Llamado por el scoreboard tras cada transacción."""
    pass
    
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
        # Sampling de cobertura: se hace ANTES de chequear, así que cubrimos
        # incluso las transacciones que fallarían en el scoreboard.
        sample_coverage(tr)
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
        # n_received puede ser >= N_TRANSACTIONS si hay test dirigido extra.
        assert self.n_received >= N_TRANSACTIONS, (
            f"Mínimo esperado {N_TRANSACTIONS} tx, recibidas {self.n_received}."
        )

        # --- Reporte de cobertura ---
        self.logger.info("=" * 70)
        self.logger.info("=== Reporte de cobertura funcional ===")
        self.logger.info("=" * 70)
        coverage_db.report_coverage(logger=self.logger.info, bins=True)

        # Exporta YAML para post-procesado (script generate_coverage_html.py).
        coverage_db.export_to_yaml(filename="coverage.yml")
        self.logger.info("Coverage YAML escrito en coverage.yml")

        # --- Cobertura fallible: 100% en los CoverPoints clave ---
        critical_points = [
            "top.sign_a",
            "top.sign_b",
            "top.exp_diff_range",
            "top.sign_cross",
        ]
        gaps = []
        for cp in critical_points:
            cov = coverage_db[cp].cover_percentage
            if cov < 100.0:
                gaps.append(f"{cp}: {cov:.1f}%")
        assert not gaps, (
            f"Cobertura incompleta en CoverPoints críticos: {gaps}. "
            f"El test debe diseñarse para cubrir todos los bins."
        )
        self.logger.info("Cobertura crítica: 100% en %s", critical_points)


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
    
    
# ============================================================================
# Test dirigido — garantiza cobertura 100% en CoverPoints críticos.
# ----------------------------------------------------------------------------
# El test aleatorio no garantiza cubrir todos los bins (sobre todo el cero
# exacto y algunas combinaciones de signos en pocos exponentes). Este test
# añade 20 transacciones específicas tras el random para asegurar coverage.
# ============================================================================

class FpuDirectedSequence(uvm_sequence):
    """20 transacciones específicas para cubrir bins difíciles."""

    DIRECTED_PAIRS = [
        # (a_bits, b_bits, descripción)
        # Cuatro combinaciones de signos con exponentes iguales:
        (0x3F800000, 0x3F800000),  # +1.0 + +1.0  (sign_a=0, sign_b=0)
        (0x3F800000, 0xBF800000),  # +1.0 + -1.0  (sign_a=0, sign_b=1) -> cero
        (0xBF800000, 0x3F800000),  # -1.0 + +1.0  (sign_a=1, sign_b=0) -> cero
        (0xBF800000, 0xBF800000),  # -1.0 + -1.0  (sign_a=1, sign_b=1)

        # Forzar exp_diff close (diff=2):
        (0x40800000, 0x40000000),  # 4.0  + 2.0
        (0xC0800000, 0x40000000),  # -4.0 + 2.0

        # Forzar exp_diff moderate (diff=7):
        (0x42C80000, 0x40000000),  # 100.0 + 2.0  (exp 133 vs 128)
        (0xC2C80000, 0x40000000),  # -100.0 + 2.0

        # Forzar exp_diff far (diff>10):
        (0x4B189680, 0x3F800000),  # 1e7 + 1.0  (exp 150 vs 127, diff=23)
        (0xCB189680, 0x3F800000),  # -1e7 + 1.0
        (0x4B189680, 0xBF800000),
        (0xCB189680, 0xBF800000),

        # Más para reforzar combinaciones:
        (0x40490FDB, 0x3FB504F3),  # pi + sqrt(2)
        (0x40490FDB, 0xBFB504F3),  # pi - sqrt(2)
        (0xC0490FDB, 0xBFB504F3),  # -pi - sqrt(2)
        (0xC0490FDB, 0x3FB504F3),  # -pi + sqrt(2)
        (0x42A00000, 0xC2A00000),  # 80.0 + (-80.0) -> cero exacto
        (0x42C80000, 0xC2A00000),  # 100.0 + (-80.0) -> positive
        (0xC2C80000, 0x42A00000),  # -100.0 + 80.0 -> negative
        (0x3E800000, 0xC4000000),  # 0.25 + (-512.0)
    ]

    async def body(self):
        for a_bits, b_bits in self.DIRECTED_PAIRS:
            tr = FpuTransaction()
            tr.a = a_bits
            tr.b = b_bits
            await self.start_item(tr)
            await self.finish_item(tr)


class FpuTest(uvm_test):
    """Ejecuta el random + el dirigido para garantizar coverage 100%."""

    def build_phase(self):
        self.env = FpuEnv("env", self)

    async def run_phase(self):
        self.raise_objection()

        # Fase 1: random.
        random_seq = FpuSequence("random_seq")
        await random_seq.start(self.env.agent.sequencer)

        # Fase 2: dirigido para garantizar coverage.
        directed_seq = FpuDirectedSequence("directed_seq")
        await directed_seq.start(self.env.agent.sequencer)

        await Timer(50, units="ns")
        self.drop_objection()

