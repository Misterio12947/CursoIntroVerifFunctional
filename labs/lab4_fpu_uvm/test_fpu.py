"""
==============================================================================
Lab 4 — Skeleton del alumno: Verificación de una FPU IEEE 754 con pyUVM.
==============================================================================

OBJETIVO DEL LAB
----------------
Verificar funcionalmente una FPU (Floating Point Unit) IEEE 754
single-precision que implementa suma (fadd). Construyes un testbench UVM
completo, mides cobertura funcional (opcional), y descubres un bug
deliberado en un RTL alternativo (ejercicio extra).

REQUISITOS PREVIOS
------------------
- Lab 3 completado (entiendes la arquitectura pyUVM: test/env/agent/
  driver/monitor/scoreboard/sequence).
- Conoces el handshake start/done desde el Lab 3 (ALU).

NUEVOS CONCEPTOS DEL LAB 4
--------------------------
1. Modelo de referencia con numpy.float32 (no aritmética entera).
2. Comparación con TOLERANCIA (±1 ULP), no igualdad exacta.
3. Cobertura funcional con cocotb_coverage (CoverPoint, CoverCross).
4. Verificación adversarial: encontrar bugs en `rtl/fpu_buggy.v`.

DUT (`rtl/fpu.v`)
-----------------
Puertos:
    input  clk, rst
    input  [31:0] a, b
    input  start
    output [31:0] result
    output done             (pulso 1 ciclo tras start)
Comportamiento: suma flotante IEEE 754, truncate rounding,
                latencia 1 ciclo, sin manejo de NaN/Inf/denormales.

ESTRUCTURA DEL LAB (10 TODOs)
-----------------------------
TODO 1: FpuTransaction.randomize (proporcionado, no edites).
TODO 2: FpuSequence.body
TODO 3: FpuDriver.run_phase y _drive
TODO 4: FpuMonitor.run_phase
TODO 5: FpuAgent.build_phase y connect_phase
TODO 6: FpuScoreboard.run_phase y _check
TODO 7: FpuEnv.build_phase y connect_phase
TODO 8: FpuTest.build_phase y run_phase
TODO 9: wrapper @cocotb.test()
TODO 10: cobertura (OPCIONAL — sigue las instrucciones del README)

EJECUTAR
--------
    make                   # corre el test contra rtl/fpu.v
    make TESTBENCH=buggy   # corre contra rtl/fpu_buggy.v (ejercicio extra)
    make waves             # genera VCD
    make coverage          # si completaste TODO 10, genera coverage_report.html
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

# Para TODO 10 (cobertura, opcional). Si NO completas el TODO 10, deja
# estos imports tal cual: solo importan los símbolos, no los usan.
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
# Helpers IEEE 754 (PROPORCIONADOS — no son objetivo de aprendizaje).
# ============================================================================
def random_safe_float32(rng):
    """Genera bits IEEE 754 (uint32) de un float32 "seguro".

    Evita NaN/Inf (exp=255), cero/denormales (exp=0), y exponentes
    extremos. Rango efectivo: ~10⁻²⁰ a ~10²².
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
    """Modelo de referencia: suma flotante IEEE 754 vía numpy.float32."""
    a = bits_to_float32(a_bits)
    b = bits_to_float32(b_bits)
    r = np.float32(a + b)
    return float32_to_bits(r)


def within_1_ulp(dut_bits, ref_bits):
    """Tolerancia ±1 ULP: los bits difieren a lo sumo en 1.

    Justificación: el RTL trunca, numpy redondea. Diferencias de 1 LSB
    en la mantisa son aceptables.
    """
    return abs(int(dut_bits) - int(ref_bits)) <= 1


# ============================================================================
# Cobertura — TODO 10 (OPCIONAL).
# ----------------------------------------------------------------------------
# Para completar este TODO, descomenta los decoradores @CoverPoint y
# @CoverCross debajo y completa los xf, bins según la guía del README.
# Si NO lo completas, deja la función vacía: el test sigue funcionando
# (sin la fallibilidad por cobertura).
# ============================================================================
def _classify_exp_diff(a_bits, b_bits):
    """Clasifica |exp_a - exp_b| en 4 rangos."""
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
    if (result_bits & 0x7FFFFFFF) == 0:
        return "zero"
    return "negative" if (result_bits >> 31) else "positive"


# TODO 10: descomenta los decoradores @CoverPoint y @CoverCross para
# habilitar la cobertura funcional. Sin ellos, sample_coverage es no-op.
# Sigue las instrucciones detalladas del README del lab.
#
# @CoverPoint("top.sign_a",
#             xf=lambda tr: (tr.a >> 31) & 1,
#             bins=[0, 1],
#             bins_labels=["positive", "negative"])
# @CoverPoint("top.sign_b",
#             xf=lambda tr: (tr.b >> 31) & 1,
#             bins=[0, 1],
#             bins_labels=["positive", "negative"])
# @CoverPoint("top.exp_diff_range",
#             xf=lambda tr: _classify_exp_diff(tr.a, tr.b),
#             bins=["equal", "close", "moderate", "far"])
# @CoverPoint("top.result_sign",
#             xf=lambda tr: _classify_result_sign(tr.result),
#             bins=["positive", "negative", "zero"])
# @CoverCross("top.sign_cross",
#             items=["top.sign_a", "top.sign_b"])
def sample_coverage(tr):
    """Sampler de cobertura. Llamado por el scoreboard tras cada transacción."""
    pass


# ============================================================================
# Transaction: FpuTransaction
# ----------------------------------------------------------------------------
# TODO 1 (PROPORCIONADO — no es objetivo de aprendizaje).
# Operandos a, b y resultado observado. Método randomize implementado.
# ============================================================================
class FpuTransaction(uvm_sequence_item):

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
# Sequence aleatoria: FpuSequence
# ----------------------------------------------------------------------------
# TODO 2: body que genere N_TRANSACTIONS transacciones aleatorias.
#
# Patrón (idéntico al del Lab 3):
#   for _ in range(N_TRANSACTIONS):
#       tr = FpuTransaction()
#       tr.randomize(self.rng)
#       await self.start_item(tr)
#       await self.finish_item(tr)
# ============================================================================
class FpuSequence(uvm_sequence):

    def __init__(self, name="fpu_seq"):
        super().__init__(name)
        self.rng = random.Random(SEED)

    async def body(self):
        # TODO 2: genera N_TRANSACTIONS transacciones aleatorias.
        raise NotImplementedError("TODO 2: implementa FpuSequence.body")


# ============================================================================
# Sequence dirigida (PROPORCIONADA): FpuDirectedSequence
# ----------------------------------------------------------------------------
# 20 transacciones específicas que cubren bins difíciles (necesarias para
# alcanzar 100% coverage en TODO 10). NO la modifiques.
# ============================================================================
class FpuDirectedSequence(uvm_sequence):

    DIRECTED_PAIRS = [
        # Cuatro combinaciones de signos con exponentes iguales:
        (0x3F800000, 0x3F800000),  # +1.0 + +1.0
        (0x3F800000, 0xBF800000),  # +1.0 + -1.0  → cero
        (0xBF800000, 0x3F800000),  # -1.0 + +1.0  → cero
        (0xBF800000, 0xBF800000),  # -1.0 + -1.0
        # exp_diff close:
        (0x40800000, 0x40000000),  # 4.0  + 2.0
        (0xC0800000, 0x40000000),  # -4.0 + 2.0
        # exp_diff moderate:
        (0x42C80000, 0x40000000),
        (0xC2C80000, 0x40000000),
        # exp_diff far:
        (0x4B189680, 0x3F800000),
        (0xCB189680, 0x3F800000),
        (0x4B189680, 0xBF800000),
        (0xCB189680, 0xBF800000),
        # Refuerzo:
        (0x40490FDB, 0x3FB504F3),
        (0x40490FDB, 0xBFB504F3),
        (0xC0490FDB, 0xBFB504F3),
        (0xC0490FDB, 0x3FB504F3),
        (0x42A00000, 0xC2A00000),  # 80.0 + (-80.0) → cero
        (0x42C80000, 0xC2A00000),
        (0xC2C80000, 0x42A00000),
        (0x3E800000, 0xC4000000),
    ]

    async def body(self):
        for a_bits, b_bits in self.DIRECTED_PAIRS:
            tr = FpuTransaction()
            tr.a = a_bits
            tr.b = b_bits
            await self.start_item(tr)
            await self.finish_item(tr)


# ============================================================================
# Driver: FpuDriver
# ----------------------------------------------------------------------------
# TODO 3:
#   - build_phase: self.dut = cocotb.top
#   - run_phase:   bucle que toma transacciones y las aplica al DUT.
#   - _drive(tr):  aplicar a, b, start=1 un ciclo, start=0 luego.
#
# El handshake start/done es idéntico al Lab 3 (ALU). El DUT registra
# result/done en el flanco siguiente a start=1.
# ============================================================================
class FpuDriver(uvm_driver):

    def build_phase(self):
        # TODO 3a: obtén el handle del DUT.
        raise NotImplementedError("TODO 3a: implementa FpuDriver.build_phase")

    async def run_phase(self):
        # TODO 3b: inicializa señales (start=0, a=0, b=0) y entra al
        # bucle infinito de get_next_item → _drive → item_done.
        raise NotImplementedError("TODO 3b: implementa FpuDriver.run_phase")

    async def _drive(self, tr):
        # TODO 3c: aplica tr.a, tr.b, start=1, espera un flanco,
        # baja start, espera otro flanco de margen.
        raise NotImplementedError("TODO 3c: implementa FpuDriver._drive")


# ============================================================================
# Monitor: FpuMonitor
# ----------------------------------------------------------------------------
# TODO 4:
#   - build_phase: obtén self.dut, crea self.analysis_port.
#   - run_phase:   muestrea start (captura a,b en pending) y done
#                  (recupera el par más viejo, lee result, publica).
#
# Patrón idéntico al Lab 3. Recuerda usar deque() para pending y
# muestrear con Timer(1, "ns") tras el RisingEdge para que las
# señales registradas estén estables.
# ============================================================================
class FpuMonitor(uvm_monitor):

    def build_phase(self):
        # TODO 4a: obtén handle del DUT y crea analysis_port.
        # HINT: from pyuvm import uvm_analysis_port
        #       self.analysis_port = uvm_analysis_port("ap", self)
        raise NotImplementedError("TODO 4a: implementa FpuMonitor.build_phase")

    async def run_phase(self):
        # TODO 4b: bucle de muestreo del handshake start/done.
        # HINT: usa deque() para emparejar entradas con salidas.
        raise NotImplementedError("TODO 4b: implementa FpuMonitor.run_phase")


# ============================================================================
# Sequencer: FpuSequencer
# ----------------------------------------------------------------------------
# Sin código adicional. Solo hereda de uvm_sequencer.
# ============================================================================
class FpuSequencer(uvm_sequencer):
    pass


# ============================================================================
# Agent: FpuAgent
# ----------------------------------------------------------------------------
# TODO 5:
#   - build_phase: instancia driver, monitor, sequencer.
#   - connect_phase: conecta driver.seq_item_port a sequencer.seq_item_export.
# ============================================================================
class FpuAgent(uvm_agent):

    def build_phase(self):
        # TODO 5a: instancia driver, monitor, sequencer.
        raise NotImplementedError("TODO 5a: implementa FpuAgent.build_phase")

    def connect_phase(self):
        # TODO 5b: conecta driver al sequencer.
        raise NotImplementedError("TODO 5b: implementa FpuAgent.connect_phase")


# ============================================================================
# Scoreboard: FpuScoreboard
# ----------------------------------------------------------------------------
# TODO 6:
#   - build_phase: crea uvm_tlm_analysis_fifo "fifo", inicializa contadores.
#   - run_phase:   bucle infinito que await self.fifo.get_export.get() y
#                  llama _check(tr).
#   - _check(tr):  llama sample_coverage(tr); calcula expected con
#                  golden_fadd; compara con within_1_ulp; actualiza
#                  n_received/passed/failed.
#   - report_phase (proporcionado): reporta + assert n_failed == 0.
# ============================================================================
class FpuScoreboard(uvm_component):

    def build_phase(self):
        # TODO 6a: crea fifo y inicializa contadores.
        raise NotImplementedError("TODO 6a: implementa FpuScoreboard.build_phase")

    async def run_phase(self):
        # TODO 6b: bucle de consumo del fifo.
        raise NotImplementedError("TODO 6b: implementa FpuScoreboard.run_phase")

    def _check(self, tr):
        # TODO 6c: sample coverage, compute expected, compare ±1 ULP.
        raise NotImplementedError("TODO 6c: implementa FpuScoreboard._check")

    def report_phase(self):
        # Proporcionado: reporta + assert.
        self.logger.info(
            "Scoreboard report: received=%d, passed=%d, failed=%d (±1 ULP tol.)",
            self.n_received, self.n_passed, self.n_failed,
        )
        assert self.n_failed == 0, (
            f"Scoreboard detectó {self.n_failed} discrepancias > 1 ULP."
        )
        assert self.n_received >= N_TRANSACTIONS, (
            f"Mínimo esperado {N_TRANSACTIONS} tx, recibidas {self.n_received}."
        )

        # Reporte de cobertura (solo útil si completaste TODO 10).
        self.logger.info("=" * 70)
        self.logger.info("=== Reporte de cobertura funcional ===")
        self.logger.info("=" * 70)
        try:
            coverage_db.report_coverage(logger=self.logger.info, bins=True)
            coverage_db.export_to_yaml(filename="coverage.yml")
            self.logger.info("Coverage YAML escrito en coverage.yml")
        except Exception as e:
            self.logger.info(f"(TODO 10 no completado: {e})")


# ============================================================================
# Env: FpuEnv
# ----------------------------------------------------------------------------
# TODO 7:
#   - build_phase: instancia agent y scoreboard.
#   - connect_phase: conecta agent.monitor.analysis_port a
#                    scoreboard.fifo.analysis_export.
# ============================================================================
class FpuEnv(uvm_env):

    def build_phase(self):
        # TODO 7a: instancia agent y scoreboard.
        raise NotImplementedError("TODO 7a: implementa FpuEnv.build_phase")

    def connect_phase(self):
        # TODO 7b: conecta el monitor al scoreboard vía analysis_port/fifo.
        raise NotImplementedError("TODO 7b: implementa FpuEnv.connect_phase")


# ============================================================================
# Test: FpuTest
# ----------------------------------------------------------------------------
# TODO 8:
#   - build_phase: instancia env.
#   - run_phase: raise_objection → ejecuta FpuSequence → ejecuta
#                FpuDirectedSequence → Timer(50,"ns") → drop_objection.
#
# El run en dos fases (random + dirigido) garantiza coverage 100% si
# completaste el TODO 10.
# ============================================================================
class FpuTest(uvm_test):

    def build_phase(self):
        # TODO 8a: instancia env.
        raise NotImplementedError("TODO 8a: implementa FpuTest.build_phase")

    async def run_phase(self):
        # TODO 8b: raise_objection, ejecuta random + dirigido,
        # espera Timer 50 ns, drop_objection.
        raise NotImplementedError("TODO 8b: implementa FpuTest.run_phase")


# ============================================================================
# Wrapper @cocotb.test()
# ----------------------------------------------------------------------------
# TODO 9: entrada del testbench.
#   1. cocotb.start_soon(Clock(dut.clk, CLK_PERIOD_NS, units="ns").start())
#   2. dut.rst.value = 1; dut.start.value = 0; dut.a.value = 0; dut.b.value = 0
#   3. await 3 ciclos
#   4. dut.rst.value = 0; await 1 ciclo
#   5. await uvm_root().run_test("FpuTest")
# ============================================================================
@cocotb.test()
async def fpu_uvm_test(dut):
    """Punto de entrada del testbench UVM FPU."""
    # TODO 9: implementa el wrapper.
    raise NotImplementedError("TODO 9: implementa el wrapper @cocotb.test()")
