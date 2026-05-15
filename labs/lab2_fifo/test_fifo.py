"""
==============================================================================
Lab 2 — Skeleton del alumno: Verificación de un FIFO síncrono con cocotb.
==============================================================================

OBJETIVO DEL LABORATORIO
------------------------
Implementar un testbench cocotb que verifique una FIFO síncrona usando el
patrón "DUT vs modelo de referencia + scoreboard". Practicarás:
    1. Construir un driver (helpers de push/pop).
    2. Mantener un modelo de referencia Python (collections.deque).
    3. Implementar un scoreboard (asserts contextuales).
    4. Escribir múltiples tests independientes con @cocotb.test().
    5. Usar pruebas dirigidas y una prueba aleatoria reproducible.

CÓMO USAR ESTE ARCHIVO
----------------------
- Busca los marcadores `TODO N:` y rellena el código que falta.
- Lee los `HINT:` para orientarte.
- Si te bloqueas, consulta:
    - solutions/lab2_fifo/fifo_reference.md  (qué hace el DUT).
    - solutions/lab2_fifo/expected_output.log (qué salida esperar).
    - solutions/lab2_fifo/test_fifo.py        (último recurso).

CÓMO EJECUTAR
-------------
Desde esta carpeta:

    make                              # los 4 tests
    make TESTCASE=test_fifo_basic     # un test específico
    make waves                        # con generación de VCD
    make clean                        # elimina artefactos

PATRÓN MENTAL: modelo de referencia
-----------------------------------
El test estimula el DUT con un driver, y EN PARALELO aplica las mismas
operaciones a un modelo Python (un deque). El scoreboard compara DUT
vs modelo en cada operación crítica. Si divergen, el test falla con
contexto.

Este patrón se generaliza directamente a UVM: driver, monitor,
reference model y scoreboard son los cuatro pilares de cualquier
testbench industrial.
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
# Deben coincidir con los parámetros del RTL (fifo.v).
# ----------------------------------------------------------------------------
DEPTH = 8
WIDTH = 8
CLK_PERIOD_NS = 10
RESET_CYCLES = 2


# ============================================================================
# TODO 1: setup_dut
# ----------------------------------------------------------------------------
# Arranca el reloj y aplica reset. Deja el DUT en estado conocido.
#
# HINT:
#   - cocotb.start_soon(Clock(dut.clk, CLK_PERIOD_NS, units="ns").start())
#   - dut.rst.value = 1, dut.push_valid.value = 0, dut.pop_valid.value = 0
#   - Espera RESET_CYCLES flancos, libera reset, espera un flanco más.
#   - Tras el reset, asserts: dut.empty == 1, dut.full == 0.
# ============================================================================
async def setup_dut(dut):
    """Arranca reloj y aplica reset síncrono."""
    # TODO 1: implementa la rutina de setup.
    raise NotImplementedError("TODO 1: implementa setup_dut")


# ============================================================================
# TODO 2: push
# ----------------------------------------------------------------------------
# Driver helper. Pulsa push_valid durante un ciclo con el dato indicado.
#
# HINT:
#   dut.push_valid.value = 1
#   dut.push_data.value  = data
#   await RisingEdge(dut.clk)
#   dut.push_valid.value = 0
#   await Timer(1, units="ns")
# ============================================================================
async def push(dut, data):
    """Pulsa push_valid durante un ciclo con el dato indicado."""
    # TODO 2: implementa el driver de push.
    raise NotImplementedError("TODO 2: implementa push")


# ============================================================================
# TODO 3: pop
# ----------------------------------------------------------------------------
# Driver helper. Pulsa pop_valid un ciclo y devuelve pop_data.
#
# HINT:
#   - pop_data es combinacional: ya es válido antes del flanco.
#   - Lee int(dut.pop_data.value) ANTES de await RisingEdge.
#   - Tras el flanco, baja pop_valid y devuelve el valor leído.
# ============================================================================
async def pop(dut):
    """Pulsa pop_valid un ciclo y devuelve pop_data."""
    # TODO 3: implementa el driver de pop.
    raise NotImplementedError("TODO 3: implementa pop")


# ============================================================================
# TODO 4: idle
# ----------------------------------------------------------------------------
# Espera `cycles` flancos sin push ni pop.
#
# HINT: trivial. Apaga push_valid y pop_valid, espera N flancos.
# ============================================================================
async def idle(dut, cycles=1):
    """Espera `cycles` flancos sin push ni pop."""
    # TODO 4: implementa idle.
    raise NotImplementedError("TODO 4: implementa idle")


# ============================================================================
# TODO 5: check_pop
# ----------------------------------------------------------------------------
# Scoreboard. Compara el valor leído del DUT contra el head del modelo.
# Si el modelo está vacío (pop sobre vacío en el DUT), no popea el modelo.
#
# HINT:
#   if len(model) == 0:
#       dut._log.debug(...)
#       return
#   esperado = model.popleft()
#   assert leido == esperado, f"[{tag}] DUT={leido}, modelo={esperado}"
# ============================================================================
def check_pop(dut, model: deque, leido: int, tag: str = ""):
    """Verifica que `leido` coincide con el head del modelo."""
    # TODO 5: implementa el scoreboard de pop.
    raise NotImplementedError("TODO 5: implementa check_pop")


# ============================================================================
# TODO 6: check_flags
# ----------------------------------------------------------------------------
# Scoreboard. Comprueba que dut.full y dut.empty coinciden con la ocupación
# del modelo.
#
# HINT:
#   empty_esperado = (len(model) == 0)
#   full_esperado  = (len(model) == DEPTH)
#   assert bool(int(dut.empty.value)) == empty_esperado, ...
#   assert bool(int(dut.full.value))  == full_esperado,  ...
# ============================================================================
def check_flags(dut, model: deque, tag: str = ""):
    """Verifica que full y empty del DUT coinciden con la ocupación."""
    # TODO 6: implementa el scoreboard de flags.
    raise NotImplementedError("TODO 6: implementa check_flags")


# ============================================================================
# TODO 7: test_fifo_basic
# ----------------------------------------------------------------------------
# 5 pushes consecutivos, luego 5 pops. Verifica orden FIFO y flags en cada
# operación.
#
# HINT (estructura):
#   await setup_dut(dut)
#   model = deque()
#   valores = [0x10, 0x20, 0x30, 0x40, 0x50]
#   for v in valores:
#       await push(dut, v)
#       model.append(v)
#       check_flags(dut, model, "basic-push")
#   for i in range(len(valores)):
#       leido = await pop(dut)
#       check_pop(dut, model, leido, f"basic-pop[{i}]")
#       check_flags(dut, model, "basic-pop")
# ============================================================================
@cocotb.test()
async def test_fifo_basic(dut):
    """5 pushes seguidos de 5 pops. Verifica orden y flags."""
    dut._log.info("=== test_fifo_basic ===")
    # TODO 7: implementa el cuerpo del test.
    raise NotImplementedError("TODO 7: implementa test_fifo_basic")


# ============================================================================
# TODO 8a: test_fifo_full
# ----------------------------------------------------------------------------
# Llenar el FIFO. Intentar un push extra (el DUT debe ignorarlo). Drenar
# todo y comprobar empty=1.
#
# HINT:
#   - Tras DEPTH pushes, full debe ser 1.
#   - Tras un push extra con full=1, el modelo NO debe cambiar (no uses
#     deque(maxlen=DEPTH) porque tira el front; el DUT solo ignora).
#   - Mejor: deque normal + condición "if len(model) < DEPTH: append".
#   - Tras drenar DEPTH pops, empty debe ser 1.
# ============================================================================
@cocotb.test()
async def test_fifo_full(dut):
    """Llenar FIFO, intentar push con full=1, drenar, comprobar empty=1."""
    dut._log.info("=== test_fifo_full ===")
    # TODO 8a: implementa el cuerpo del test.
    raise NotImplementedError("TODO 8a: implementa test_fifo_full")


# ============================================================================
# TODO 8b: test_fifo_empty
# ----------------------------------------------------------------------------
# Intentar pops sobre FIFO vacío. El DUT debe ignorar; flags no cambian.
# Luego un push + pop normal para comprobar que el FIFO sigue funcional.
# ============================================================================
@cocotb.test()
async def test_fifo_empty(dut):
    """Pop sobre FIFO vacío: ignorado, sin cambios de estado."""
    dut._log.info("=== test_fifo_empty ===")
    # TODO 8b: implementa el cuerpo del test.
    raise NotImplementedError("TODO 8b: implementa test_fifo_empty")


# ============================================================================
# TODO 8c: test_fifo_random
# ----------------------------------------------------------------------------
# N operaciones aleatorias (push/pop/idle). DUT vs modelo en cada operación.
# Usa seed fijo 0xC0FFEE para reproducibilidad.
#
# HINT:
#   rng = random.Random(0xC0FFEE)
#   model = deque()
#   for op_idx in range(100):
#       op = rng.choice(["push", "pop", "idle"])
#       if op == "push":
#           data = rng.randint(0, (1 << WIDTH) - 1)
#           await push(dut, data)
#           if len(model) < DEPTH:
#               model.append(data)
#       elif op == "pop":
#           leido = await pop(dut)
#           check_pop(dut, model, leido, f"random-pop[{op_idx}]")
#       else:
#           await idle(dut)
#       check_flags(dut, model, f"random[{op_idx}:{op}]")
# ============================================================================
@cocotb.test()
async def test_fifo_random(dut):
    """N operaciones aleatorias. DUT vs modelo en cada operación."""
    dut._log.info("=== test_fifo_random ===")
    # TODO 8c: implementa el cuerpo del test.
    raise NotImplementedError("TODO 8c: implementa test_fifo_random")
