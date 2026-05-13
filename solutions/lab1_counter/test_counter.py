"""
==============================================================================
Lab 1 — Solución Maestra: Verificación de un contador síncrono de 8 bits.
==============================================================================

Este archivo es la SOLUCIÓN COMPLETA del Laboratorio 1.
Está pensada como referencia tras intentar el ejercicio del alumno.

Conceptos cocotb cubiertos:
    1. Corrutinas async/await.
    2. Triggers de simulación: RisingEdge, FallingEdge, Timer.
    3. Concurrencia con cocotb.start_soon().
    4. Control de señales del DUT desde Python.
    5. Asserts con mensajes contextuales.
    6. Logging integrado con el ciclo de simulación.

Modelo mental para alumnos de hardware:
    - Una "corrutina" en Python es como un proceso `initial` o `always`
      en Verilog: una unidad de ejecución concurrente.
    - Un "trigger" (RisingEdge, Timer, ...) es como un `@(posedge clk)`
      o un `#10`: una sentencia de espera.
    - El "scheduler" de cocotb es como el simulador HDL: decide qué
      corrutina avanza en cada paso de tiempo simulado.
    - `await` es la forma en Python de decir "suspéndeme hasta que
      ocurra este evento". El simulador HDL se encarga de despertarte.

Tiempo real vs tiempo simulado:
    - Tiempo real = segundos en el reloj de pared.
    - Tiempo simulado = ns/ps en el modelo digital.
    Una simulación de 1 ms puede tardar 100 ms reales o 10 segundos
    reales: depende de la complejidad del DUT, no del wall-clock.
    Por eso `await Timer(10, units="ns")` NO bloquea al CPU 10 ns,
    bloquea a la corrutina hasta que el simulador avance su reloj 10 ns.
==============================================================================
"""

import os
import cocotb
from cocotb.triggers import RisingEdge, FallingEdge, Timer


# ----------------------------------------------------------------------------
# Constantes globales del testbench.
# ----------------------------------------------------------------------------
CLK_PERIOD_NS = 10            # Reloj de 100 MHz (periodo de 10 ns).
RESET_CYCLES = 2              # Duración del pulso de reset en ciclos.
COUNT_CYCLES = 10             # Cuántos ciclos contar para la fase básica.


# ============================================================================
# Corrutina 1: generate_clock
# ----------------------------------------------------------------------------
# Genera un reloj cuadrado en la señal dut.clk.
#
# Equivalente Verilog:
#     always #(CLK_PERIOD_NS/2) clk = ~clk;
#
# En código de producción suele usarse:
#     cocotb.start_soon(cocotb.clock.Clock(dut.clk, 10, units="ns").start())
# que es más eficiente y robusto. La escribimos a mano aquí con fines
# pedagógicos: queremos ver cómo se construye una corrutina periódica
# desde primeros principios.
# ============================================================================
async def generate_clock(dut, period_ns: int = CLK_PERIOD_NS):
    """Genera un reloj con duty cycle 50% en dut.clk indefinidamente."""
    half_period = period_ns // 2
    dut.clk.value = 0
    while True:
        await Timer(half_period, units="ns")   # Espera medio periodo.
        dut.clk.value = 1                      # Flanco de subida.
        await Timer(half_period, units="ns")
        dut.clk.value = 0                      # Flanco de bajada.


# ============================================================================
# Corrutina 2: reset_dut
# ----------------------------------------------------------------------------
# Aplica reset síncrono activo en alto durante N ciclos.
# Deja el DUT en estado conocido: count=0, en=0.
# ============================================================================
async def reset_dut(dut, cycles: int = RESET_CYCLES):
    """Aplica reset síncrono durante `cycles` ciclos y lo libera."""
    dut._log.info("Aplicando reset durante %d ciclos...", cycles)

    dut.rst.value = 1
    dut.en.value = 0

    # Esperamos N flancos de reloj con rst=1.
    for _ in range(cycles):
        await RisingEdge(dut.clk)

    # Liberamos el reset en el flanco siguiente.
    dut.rst.value = 0
    await RisingEdge(dut.clk)

    dut._log.info("Reset liberado. count=%d", int(dut.count.value))


# ============================================================================
# Corrutina 3: monitor_counter
# ----------------------------------------------------------------------------
# Corre en paralelo al test principal.
# Muestrea count en cada flanco de subida y lo registra en log.
#
# Patrón pedagógico: dos corrutinas (test principal + monitor) ejecutándose
# concurrentemente sobre el mismo DUT. El alumno ve que cocotb permite
# "observadores" pasivos como en un testbench UVM real.
# ============================================================================
async def monitor_counter(dut):
    """Imprime el valor del contador en cada flanco de subida."""
    while True:
        await RisingEdge(dut.clk)
        # FallingEdge tras el RisingEdge para muestrear tras la propagación
        # del flip-flop. Alternativa equivalente: await Timer(1, units="ns").
        await FallingEdge(dut.clk)
        dut._log.debug(
            "monitor: t=%s | en=%d rst=%d count=%d",
            cocotb.utils.get_sim_time(units="ns"),
            int(dut.en.value),
            int(dut.rst.value),
            int(dut.count.value),
        )


# ============================================================================
# Test principal: test_counter_basic
# ----------------------------------------------------------------------------
# Cubre los tres comportamientos del prompt:
#   1. Conteo incremental correcto con en=1.
#   2. Reset síncrono correcto (count vuelve a 0).
#   3. Estabilidad cuando en=0 (count se mantiene).
# ============================================================================
@cocotb.test()
async def test_counter_basic(dut):
    """Verifica conteo, reset y estabilidad del contador de 8 bits."""

    dut._log.info("=" * 70)
    dut._log.info("Lab 1 — Solución: arrancando test_counter_basic")
    dut._log.info("=" * 70)

    # ------------------------------------------------------------------
    # Fase 0: arranque del reloj y del monitor (corrutinas concurrentes).
    # ------------------------------------------------------------------
    # start_soon lanza la corrutina sin esperar a que termine. Es
    # equivalente conceptual a un `fork` en SystemVerilog.
    clk_task = cocotb.start_soon(generate_clock(dut))
    monitor_task = cocotb.start_soon(monitor_counter(dut))

    # Damos un instante al reloj para arrancar (Timer 1 ns).
    # Sin esto, el primer RisingEdge podría no haber ocurrido aún.
    await Timer(1, units="ns")

    # ------------------------------------------------------------------
    # Fase 1: reset.
    # ------------------------------------------------------------------
    await reset_dut(dut)

    valor_post_reset = int(dut.count.value)
    assert valor_post_reset == 0, (
        f"[Fase 1] Tras reset se esperaba count=0, se obtuvo "
        f"{valor_post_reset}."
    )
    dut._log.info("[Fase 1] OK — reset deja count=0.")

    # ------------------------------------------------------------------
    # Fase 2: conteo incremental con en=1.
    # ------------------------------------------------------------------
    dut._log.info("[Fase 2] Habilitando en=1 y contando %d ciclos.",
                  COUNT_CYCLES)
    dut.en.value = 1

    for ciclo in range(COUNT_CYCLES):
        await RisingEdge(dut.clk)
        # Pequeño margen para muestrear tras la actualización del FF.
        await Timer(1, units="ns")
        valor = int(dut.count.value)
        esperado = ciclo + 1
        assert valor == esperado, (
            f"[Fase 2] Ciclo {ciclo}: se esperaba count={esperado}, "
            f"se obtuvo {valor}."
        )

    dut._log.info("[Fase 2] OK — contador alcanzó %d tras %d ciclos.",
                  COUNT_CYCLES, COUNT_CYCLES)

    # ------------------------------------------------------------------
    # Fase 3: estabilidad con en=0.
    # ------------------------------------------------------------------
    dut._log.info("[Fase 3] Deshabilitando en=0. count debe mantenerse.")
    dut.en.value = 0

    valor_congelado = int(dut.count.value)
    for ciclo in range(5):
        await RisingEdge(dut.clk)
        await Timer(1, units="ns")
        valor = int(dut.count.value)
        assert valor == valor_congelado, (
            f"[Fase 3] Ciclo {ciclo}: count cambió pese a en=0. "
            f"Esperado {valor_congelado}, obtenido {valor}."
        )

    dut._log.info("[Fase 3] OK — count se mantuvo en %d con en=0.",
                  valor_congelado)

    # ------------------------------------------------------------------
    # Fase 4: segundo reset (verifica que rst funciona en cualquier momento).
    # ------------------------------------------------------------------
    dut._log.info("[Fase 4] Aplicando reset en caliente.")
    await reset_dut(dut)

    valor_post_reset2 = int(dut.count.value)
    assert valor_post_reset2 == 0, (
        f"[Fase 4] Reset en caliente falló: count={valor_post_reset2}."
    )
    dut._log.info("[Fase 4] OK — reset en caliente correcto.")

    # ------------------------------------------------------------------
    # Cierre: paramos las corrutinas paralelas.
    # ------------------------------------------------------------------
    monitor_task.kill()
    clk_task.kill()

    dut._log.info("=" * 70)
    dut._log.info("PASS — test_counter_basic completado sin errores.")
    dut._log.info("=" * 70)
