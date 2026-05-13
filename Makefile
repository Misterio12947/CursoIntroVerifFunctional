# Makefile para la prueba de humo del Día 1.
# Delega la lógica de simulación al Makefile.sim que provee cocotb.

# --- Configuración del simulador ---
SIM            ?= icarus
TOPLEVEL_LANG  ?= verilog

# --- Fuentes y toplevel ---
VERILOG_SOURCES = $(PWD)/rtl/counter.v
TOPLEVEL        = counter

# --- Módulo Python con los tests (sin extensión .py) ---
MODULE          = test_smoke

# Hacer visible la carpeta tests/ a Python.
export PYTHONPATH := $(PWD)/tests:$(PYTHONPATH)

# Objetivo por defecto.
.PHONY: all
all: test

# Ejecuta la simulación delegando al Makefile.sim oficial de cocotb.
.PHONY: test
test:
	$(MAKE) -f $(shell cocotb-config --makefiles)/Makefile.sim

# Limpieza de artefactos generados por la simulación.
.PHONY: clean
clean:
	rm -rf sim_build results.xml *.vcd *.fst *.vvp \
	       __pycache__ tests/__pycache__
