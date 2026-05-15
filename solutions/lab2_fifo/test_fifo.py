"""
==============================================================================
Lab 2 — Solución Maestra: Verificación de un FIFO síncrono con cocotb.
==============================================================================

Esta solución introduce el patrón industrial fundamental de DV:

    DUT (RTL)  ←→  Driver  ←→  Test  ←→  Reference Model  ←→  Scoreboard

El test estimula el DUT vía un driver. El modelo de referencia predice
qué debería pasar. El scoreboard compara DUT vs modelo en cada operación.
Si divergen, el test falla con un mensaje contextual.

Conceptos nuevos respecto al Lab 1:
    1. Modelo de referencia (`collections.deque`).
    2. Scoreboard (función `check_pop`).
    3. Múltiples tests independientes (@cocotb.test() x 4).
    4. Reset compartido vía función `setup_dut()`.
    5. Pruebas dirigidas + prueba aleatoria con seed reproducible.

Patrón mental:
    El modelo de referencia es la "verdad alternativa". Si el DUT pasa
    todos los scoreboard, significa que se comporta como el modelo. Si
    el modelo está bien construido y refleja la especificación, entonces
    el DUT está correcto.

    Aquí el modelo es trivial (un deque). En diseños reales puede ser
    un modelo cycle-accurate, un golden generator en C, o un módulo
    SystemC. La estructura es la misma.
==============================================================================
"""

import os
import random
from collections import deque

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, Timer


# ----------------------------------------------------------------------------
# Constantes del testbench.
# Deben coincidir con los parámetros del RTL.
# ----------------------------------------------------------------------------
DEPTH = 8
WIDTH = 8
CLK_PERIOD_NS = 10
RESET_CYCLES = 2


# ============================================================================
# Setup compartido por todos los tests.
# ----------------------------------------------------------------------------
# Arranca el reloj y aplica reset. Deja el DUT con todas las señales en
# estado conocido: empty=1, full=0, count=0.
# ============================================================================
async def setup_dut(dut):
    """Arranca reloj y aplica reset síncrono. Idempotente."""
    cocotb.start_soon(Clock(dut.clk, CLK_PERIOD_NS, units="ns").start())

    dut.rst.value        = 1
    dut.push_valid.value = 0
    dut.pop_valid.value  = 0
    dut.push_data.value  = 0

    for _ in range(RESET_CYCLES):
        await RisingEdge(dut.clk)
    dut.rst.value = 0
    await RisingEdge(dut.clk)
    await Timer(1, units="ns")

    assert int(dut.empty.value) == 1, "Tras reset: empty debería ser 1"
    assert int(dut.full.value)  == 0, "Tras reset: full debería ser 0"


# ============================================================================
# Driver: helpers para escribir y leer del DUT.
# ----------------------------------------------------------------------------
# Cada función ocupa exactamente un ciclo de reloj. Esto facilita razonar
# sobre el timing y emparejarse con el modelo de referencia 1-a-1.
# ============================================================================
async def push(dut, data):
    """Pulsa push_valid durante un ciclo con el dato indicado."""
    dut.push_valid.value = 1
    dut.push_data.value  = data
    await RisingEdge(dut.clk)
    dut.push_valid.value = 0
    await Timer(1, units="ns")


async def pop(dut):
    """Pulsa pop_valid durante un ciclo y devuelve pop_data tras el flanco."""
    dut.pop_valid.value = 1
    # Lectura combinacional: pop_data ya es válido ahora.
    leido = int(dut.pop_data.value)
    await RisingEdge(dut.clk)
    dut.pop_valid.value = 0
    await Timer(1, units="ns")
    return leido


async def idle(dut, cycles=1):
    """Espera `cycles` flancos sin push ni pop."""
    dut.push_valid.value = 0
    dut.pop_valid.value  = 0
    for _ in range(cycles):
        await RisingEdge(dut.clk)
    await Timer(1, units="ns")


# ============================================================================
# Scoreboard: compara DUT vs modelo.
# ----------------------------------------------------------------------------
# Llamado tras cada pop. Comprueba que el dato leído del DUT coincide con
# el head del modelo de referencia.
# ============================================================================
def check_pop(dut, model: deque, leido: int, tag: str = ""):
    """Verifica que `leido` coincide con el head del modelo."""
    if len(model) == 0:
        # Pop sobre FIFO vacío: el DUT debió ignorar la operación.
        # No popeamos el modelo. Solo registramos.
        dut._log.debug("%s pop sobre vacío (ignorado): leido=%d", tag, leido)
        return

    esperado = model.popleft()
    assert leido == esperado, (
        f"[{tag}] scoreboard mismatch: DUT leyó {leido}, "
        f"modelo esperaba {esperado}. Modelo tras pop = {list(model)}"
    )


def check_flags(dut, model: deque, tag: str = ""):
    """Verifica que full y empty del DUT coinciden con la ocupación."""
    empty_esperado = (len(model) == 0)
    full_esperado  = (len(model) == DEPTH)
    empty_dut = bool(int(dut.empty.value))
    full_dut  = bool(int(dut.full.value))

    assert empty_dut == empty_esperado, (
        f"[{tag}] empty mismatch: DUT={empty_dut}, modelo={empty_esperado}, "
        f"len(model)={len(model)}"
    )
    assert full_dut == full_esperado, (
        f"[{tag}] full mismatch: DUT={full_dut}, modelo={full_esperado}, "
        f"len(model)={len(model)}"
    )


# ============================================================================
# Test 1: push y pop básico
# ----------------------------------------------------------------------------
# 5 pushes consecutivos, luego 5 pops. Verifica orden FIFO.
# ============================================================================
@cocotb.test()
async def test_fifo_basic(dut):
    """5 pushes seguidos de 5 pops. Verifica orden y flags."""
    dut._log.info("=== test_fifo_basic ===")
    await setup_dut(dut)

    # Modelo de referencia. `maxlen=DEPTH` para que rechace pushes cuando
    # esté lleno, igual que el DUT.
    model = deque(maxlen=DEPTH)

    valores = [0x10, 0x20, 0x30, 0x40, 0x50]

    # Fase push.
    for v in valores:
        await push(dut, v)
        model.append(v)
        check_flags(dut, model, "basic-push")

    dut._log.info("Tras 5 pushes: count modelo = %d", len(model))

    # Fase pop.
    for i in range(len(valores)):
        leido = await pop(dut)
        check_pop(dut, model, leido, f"basic-pop[{i}]")
        check_flags(dut, model, "basic-pop")

    dut._log.info("PASS — test_fifo_basic")


# ============================================================================
# Test 2: llenar el FIFO
# ----------------------------------------------------------------------------
# Empuja DEPTH valores, verifica full=1, intenta un push extra (debe
# ignorarse), drena todo y verifica empty=1.
# ============================================================================
@cocotb.test()
async def test_fifo_full(dut):
    """Llenar FIFO, intentar push con full=1, drenar, comprobar empty=1."""
    dut._log.info("=== test_fifo_full ===")
    await setup_dut(dut)

    model = deque(maxlen=DEPTH)

    # Llenado.
    for i in range(DEPTH):
        await push(dut, i + 1)
        model.append(i + 1)

    assert int(dut.full.value) == 1, "Tras DEPTH pushes, full debería ser 1"
    check_flags(dut, model, "full-after-fill")

    # Intento de push con full=1: el DUT debe ignorarlo.
    # No actualizamos el modelo (deque con maxlen también ignora).
    overflow_value = 0xAB
    await push(dut, overflow_value)
    model.append(overflow_value)   # deque.append en deque lleno hace pop por la izquierda
    # ATENCIÓN: deque(maxlen=DEPTH).append en cola llena tira el front.
    # El DUT NO hace eso; ignora silenciosamente. Corregimos el modelo:
    # como el DUT ignoró, el modelo no debió aceptar tampoco. Restauramos.
    # (Lección: el modelo debe imitar al DUT, no a la "lógica natural" de
    # deque. Usamos un deque sin maxlen + chequeo manual.)
    # Refactor inmediato:
    model = deque()
    for i in range(DEPTH):
        model.append(i + 1)
    # Modelo ahora refleja el estado real: lleno con [1..DEPTH], sin overflow.
    check_flags(dut, model, "full-after-overflow-attempt")

    # Drenado.
    for i in range(DEPTH):
        leido = await pop(dut)
        check_pop(dut, model, leido, f"full-pop[{i}]")

    assert int(dut.empty.value) == 1, "Tras drenar, empty debería ser 1"
    check_flags(dut, model, "full-after-drain")

    dut._log.info("PASS — test_fifo_full")


# ============================================================================
# Test 3: pop sobre FIFO vacío
# ----------------------------------------------------------------------------
# Intenta pop en empty=1. El DUT debe ignorar; flags no cambian.
# ============================================================================
@cocotb.test()
async def test_fifo_empty(dut):
    """Pop sobre FIFO vacío: ignorado, sin cambios de estado."""
    dut._log.info("=== test_fifo_empty ===")
    await setup_dut(dut)

    model = deque()

    # Verifica estado inicial.
    check_flags(dut, model, "empty-init")

    # Tres pops sobre vacío. No deben cambiar nada.
    for i in range(3):
        leido = await pop(dut)
        # En vacío, el DUT no popea, pero pop_data puede ser cualquier valor.
        # Solo verificamos que las flags no cambian.
        check_flags(dut, model, f"empty-pop[{i}]")

    # Tras los pops espurios, push un valor y leerlo correctamente.
    await push(dut, 0x99)
    model.append(0x99)
    check_flags(dut, model, "empty-after-push")

    leido = await pop(dut)
    check_pop(dut, model, leido, "empty-final-pop")
    check_flags(dut, model, "empty-after-pop")

    dut._log.info("PASS — test_fifo_empty")


# ============================================================================
# Test 4: secuencia aleatoria
# ----------------------------------------------------------------------------
# N operaciones aleatorias mezcladas (push, pop, idle). Modelo y DUT deben
# coincidir en TODAS las operaciones.
# ============================================================================
@cocotb.test()
async def test_fifo_random(dut):
    """N operaciones aleatorias. DUT vs modelo en cada operación."""
    dut._log.info("=== test_fifo_random ===")
    await setup_dut(dut)

    rng = random.Random(0xC0FFEE)   # Seed fijo: reproducibilidad.
    model = deque()
    N_OPS = 100

    for op_idx in range(N_OPS):
        op = rng.choice(["push", "pop", "idle"])

        if op == "push":
            data = rng.randint(0, (1 << WIDTH) - 1)
            await push(dut, data)
            # El modelo solo acepta si no está lleno (igual que el DUT).
            if len(model) < DEPTH:
                model.append(data)
        elif op == "pop":
            leido = await pop(dut)
            check_pop(dut, model, leido, f"random-pop[{op_idx}]")
        else:  # idle
            await idle(dut)

        check_flags(dut, model, f"random[{op_idx}:{op}]")

    dut._log.info(
        "PASS — test_fifo_random (%d ops, modelo final con %d elementos)",
        N_OPS, len(model),
    )
