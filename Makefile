# Makefile para la prueba de humo del Día 1.
# Delega la lógica de simulación al Makefile.sim que provee cocotb.

# Directorio donde vive ESTE Makefile, calculado de forma robusta.
TOPDIR := $(abspath $(dir $(lastword $(MAKEFILE_LIST))))

# --- Configuración del simulador ---
SIM            ?= icarus
TOPLEVEL_LANG  ?= verilog

# --- Fuentes y toplevel ---
VERILOG_SOURCES := $(TOPDIR)/rtl/counter.v
TOPLEVEL        := counter

# --- Módulo Python con los tests (sin extensión .py) ---
MODULE          := test_smoke

# Exportar variables al entorno para el sub-make.
export SIM
export TOPLEVEL_LANG
export VERILOG_SOURCES
export TOPLEVEL
export MODULE

# Hacer visible la carpeta tests/ a Python.
export PYTHONPATH := $(TOPDIR)/tests:$(PYTHONPATH)

# Objetivo por defecto.
.PHONY: all
all: test

# Ejecuta la simulación delegando al Makefile.sim oficial de cocotb.
# Las variables se pasan también inline como red de seguridad.
.PHONY: test
test:
	$(MAKE) -f $(shell cocotb-config --makefiles)/Makefile.sim \
	    SIM=$(SIM) \
	    TOPLEVEL_LANG=$(TOPLEVEL_LANG) \
	    VERILOG_SOURCES="$(VERILOG_SOURCES)" \
	    TOPLEVEL=$(TOPLEVEL) \
	    MODULE=$(MODULE)

# Limpieza de artefactos generados por la simulación.
.PHONY: clean
clean:
	rm -rf sim_build results.xml *.vcd *.fst *.vvp \
	       __pycache__ tests/__pycache__
