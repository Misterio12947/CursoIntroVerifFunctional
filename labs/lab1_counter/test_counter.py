"""
==============================================================================
Lab 1 — Skeleton del alumno: Verificación de un contador síncrono de 8 bits.
==============================================================================

OBJETIVO DEL LABORATORIO
------------------------
Implementar un testbench cocotb que verifique el comportamiento de un
contador síncrono de 8 bits. Practicarás:
    1. Cómo escribir corrutinas async/await.
    2. Cómo controlar señales del DUT desde Python.
    3. Cómo usar triggers (RisingEdge, Timer) para sincronizarte con el RTL.
    4. Cómo escribir asserts informativos.
    5. Cómo lanzar corrutinas concurrentes con cocotb.start_soon().

CÓMO USAR ESTE ARCHIVO
----------------------
- Busca los marcadores `TODO N:` y rellena el código que falta.
- Lee los `HINT:` para orientarte.
- Si te bloqueas, consulta `../../solutions/lab1_counter/test_counter.py`
  PERO solo después de haberlo intentado.

CÓMO EJECUTAR
-------------
Desde esta carpeta:

    make            # corre el test
    make waves      # corre el test y genera waves/counter.vcd
    make clean      # elimina artefactos

DOCUMENTACIÓN ÚTIL
------------------
- cocotb triggers: https://docs.cocotb.org/en/stable/triggers.html
- cocotb async/await: https://docs.cocotb.org/en/stable/coroutines.html
- Tu contador (RTL): ../../rtl/counter.v

MODELO MENTAL PARA HARDWARE ENGINEERS
-------------------------------------
- Corrutina ≈ proceso `always`/`initial` en Verilog.
- `await RisingEdge(dut.clk)` ≈ `@(posedge clk)`.
- `await Timer(10, units="ns")` ≈ `#10`.
- `cocotb.start_soon(corrutina(...))` ≈ `fork`/`join_none`.
==============================================================================
"""

import cocotb
from cocotb.triggers import RisingEdge, FallingEdge, Timer


# ----------------------------------------------------------------------------
# Constantes globales del testbench.
# Estas ya están listas; no necesitas modificarlas.
# ----------------------------------------------------------------------------
CLK_PERIOD_NS = 10            # Reloj de 100 MHz.
RESET_CYCLES = 2              # Duración del pulso de reset en ciclos.
COUNT_CYCLES = 10             # Cuántos ciclos contar.


# ============================================================================
# Corrutina 1: generate_clock
# ----------------------------------------------------------------------------
# TODO 1: Implementa una corrutina que genere un reloj cuadrado con duty
# cycle 50% en dut.clk.
#
# HINT:
#   - Pon dut.clk.value = 0 al inicio.
#   - Usa un `while True:` para que el reloj corra indefinidamente.
#   - Dentro del bucle, alterna 0 y 1 con `await Timer(half, units="ns")`.
#   - `half` es period_ns // 2.
# ============================================================================
async def generate_clock(dut, period_ns: int = CLK_PERIOD_NS):
    """Genera un reloj con duty cycle 50% en dut.clk indefinidamente."""
    # TODO 1: implementa la corrutina aquí.
    raise NotImplementedError("TODO 1: implementa generate_clock")


# ============================================================================
# Corrutina 2: reset_dut
# ----------------------------------------------------------------------------
# TODO 2: Aplica reset síncrono activo en alto durante `cycles` ciclos
# y libéralo. El DUT debe quedar con count=0, en=0 al terminar.
#
# HINT:
#   - Asigna dut.rst.value = 1 y dut.en.value = 0.
#   - Espera `cycles` flancos de subida con `await RisingEdge(dut.clk)`.
#   - Suelta el reset (dut.rst.value = 0) y espera un flanco más.
#   - Usa dut._log.info("...") para mostrar mensajes amigables.
# ============================================================================
async def reset_dut(dut, cycles: int = RESET_CYCLES):
    """Aplica reset síncrono durante `cycles` ciclos y lo libera."""
    # TODO 2: implementa la corrutina aquí.
    raise NotImplementedError("TODO 2: implementa reset_dut")


# ============================================================================
# Corrutina 3: monitor_counter
# ----------------------------------------------------------------------------
# TODO 3: Corre concurrentemente con el test. En cada flanco de subida
# muestrea dut.count y registra su valor con dut._log.debug(...).
#
# HINT:
#   - while True:
#         await RisingEdge(dut.clk)
#         await FallingEdge(dut.clk)   # <- muestrea tras la propagación
#         dut._log.debug("monitor: count=%d", int(dut.count.value))
#   - Usar debug (no info) evita inundar la consola.
# ============================================================================
async def monitor_counter(dut):
    """Imprime el valor del contador en cada flanco de subida."""
    # TODO 3: implementa la corrutina aquí.
    raise NotImplementedError("TODO 3: implementa monitor_counter")


# ============================================================================
# Test principal: test_counter_basic
# ----------------------------------------------------------------------------
# TODO 4: Rellena las cuatro fases siguientes para verificar el contador.
# La estructura ya está dada; solo falta la lógica de cada fase.
# ============================================================================
@cocotb.test()
async def test_counter_basic(dut):
    """Verifica conteo, reset y estabilidad del contador de 8 bits."""

    dut._log.info("=" * 70)
    dut._log.info("Lab 1 — Skeleton: arrancando test_counter_basic")
    dut._log.info("=" * 70)

    # ------------------------------------------------------------------
    # Fase 0: arranque del reloj y del monitor (corrutinas concurrentes).
    # Esta parte ya está hecha. Observa cómo cocotb.start_soon() lanza
    # ambas corrutinas sin bloquear el test principal.
    # ------------------------------------------------------------------
    clk_task = cocotb.start_soon(generate_clock(dut))
    monitor_task = cocotb.start_soon(monitor_counter(dut))

    # Dejamos arrancar al reloj.
    await Timer(1, units="ns")

    # ------------------------------------------------------------------
    # Fase 1: reset inicial.
    # TODO 4.1: llama a reset_dut(...) y comprueba con assert que
    # dut.count vale 0 tras el reset.
    #
    # HINT:
    #   await reset_dut(dut)
    #   valor = int(dut.count.value)
    #   assert valor == 0, f"Tras reset se esperaba 0, se obtuvo {valor}"
    # ------------------------------------------------------------------
    # TODO 4.1: implementa la fase de reset y su assert.
    raise NotImplementedError("TODO 4.1: implementa la fase de reset")

    # ------------------------------------------------------------------
    # Fase 2: conteo incremental con en=1.
    # TODO 4.2: pon dut.en.value = 1 y, durante COUNT_CYCLES ciclos,
    # comprueba que count incrementa en uno cada ciclo.
    #
    # HINT:
    #   dut.en.value = 1
    #   for ciclo in range(COUNT_CYCLES):
    #       await RisingEdge(dut.clk)
    #       await Timer(1, units="ns")          # margen tras el flanco
    #       valor = int(dut.count.value)
    #       esperado = ciclo + 1
    #       assert valor == esperado, ...
    # ------------------------------------------------------------------
    # TODO 4.2: implementa la fase de conteo.

    # ------------------------------------------------------------------
    # Fase 3: estabilidad con en=0.
    # TODO 4.3: pon dut.en.value = 0 y comprueba que count NO cambia
    # durante 5 ciclos.
    #
    # HINT:
    #   dut.en.value = 0
    #   congelado = int(dut.count.value)
    #   for _ in range(5):
    #       await RisingEdge(dut.clk)
    #       await Timer(1, units="ns")
    #       assert int(dut.count.value) == congelado, ...
    # ------------------------------------------------------------------
    # TODO 4.3: implementa la fase de estabilidad.

    # ------------------------------------------------------------------
    # Fase 4: reset en caliente.
    # TODO 4.4: aplica de nuevo reset_dut(...) y verifica count == 0.
    # ------------------------------------------------------------------
    # TODO 4.4: implementa la fase de reset en caliente.

    # ------------------------------------------------------------------
    # Cierre: paramos las corrutinas paralelas.
    # ------------------------------------------------------------------
    monitor_task.kill()
    clk_task.kill()

    dut._log.info("=" * 70)
    dut._log.info("PASS — test_counter_basic completado sin errores.")
    dut._log.info("=" * 70)
