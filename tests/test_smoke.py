"""Prueba de humo del entorno.

Valida que la cadena cocotb + iverilog + pyuvm funciona extremo a extremo
ejercitando un contador síncrono de 8 bits.
"""

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, Timer

# Importación con el único propósito de verificar que pyuvm está instalado.
# El uso real de pyUVM se introduce en módulos posteriores del curso.
import pyuvm  # noqa: F401


async def reset_dut(dut):
    """Aplica reset síncrono durante 2 ciclos y lo libera."""
    dut.rst.value = 1
    dut.en.value = 0
    await RisingEdge(dut.clk)
    await RisingEdge(dut.clk)
    dut.rst.value = 0
    await RisingEdge(dut.clk)


@cocotb.test()
async def test_counter_increment(dut):
    """El contador incrementa una unidad por cada ciclo con en=1."""

    # 1. Generación de reloj: 10 ns de periodo (100 MHz).
    cocotb.start_soon(Clock(dut.clk, 10, units="ns").start())

    # 2. Reset inicial.
    await reset_dut(dut)
    valor_tras_reset = int(dut.count.value)
    assert valor_tras_reset == 0, (
        f"Tras reset se esperaba count=0, se obtuvo {valor_tras_reset}"
    )

    # 3. Habilitar el contador.
    dut.en.value = 1

    # 4. Esperar N ciclos contando flancos.
    n_ciclos = 5
    for _ in range(n_ciclos):
        await RisingEdge(dut.clk)

    # Pequeña espera para muestrear el valor tras la propagación del flanco.
    await Timer(1, units="ns")

    # 5. Verificación.
    valor = int(dut.count.value)
    assert valor == n_ciclos, (
        f"Se esperaba count={n_ciclos}, se obtuvo {valor}"
    )

    # 6. Mensajes de éxito.
    dut._log.info("PASS: contador incrementa correctamente a %d", valor)
    dut._log.info("cocotb y pyuvm cargados sin errores.")
