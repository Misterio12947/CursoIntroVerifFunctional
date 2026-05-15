# ============================================================================
# Makefile raíz del curso.
# ----------------------------------------------------------------------------
# Parametrizable: permite ejecutar distintos testbenches sin duplicar reglas.
#
# Uso por defecto (smoke test del Día 1):
#     make
#
# Uso parametrizado:
#     make MODULE=<test_module>
#     make MODULE=<test_module> TESTCASE=<single_test>
#     make MODULE=<test_module> MODULE_DIR=<path> VERILOG_SOURCES=...
#
# Lecciones aplicadas del Día 1 (caso "iverilog: no source files."):
#   - export VAR explícito.
#   - VAR=$(VAR) pasada inline al sub-make como red de seguridad.
# ============================================================================

# Directorio donde vive ESTE Makefile.
TOPDIR := $(abspath $(dir $(lastword $(MAKEFILE_LIST))))

# --- Configuración del simulador ---
SIM            ?= icarus
TOPLEVEL_LANG  ?= verilog

# --- Defaults: smoke test del Día 1 ---
VERILOG_SOURCES ?= $(TOPDIR)/rtl/counter.v
TOPLEVEL        ?= counter
MODULE          ?= test_smoke
MODULE_DIR      ?= $(TOPDIR)/tests

# TESTCASE es opcional. Si no se define, cocotb corre todos los tests
# del MODULE. Si se define, solo corre el test indicado.
TESTCASE ?=

# Exportar variables al entorno para el sub-make.
export SIM
export TOPLEVEL_LANG
export VERILOG_SOURCES
export TOPLEVEL
export MODULE

# Hacer visible MODULE_DIR a Python.
export PYTHONPATH := $(MODULE_DIR):$(PYTHONPATH)

# Si TESTCASE está definido, exportarlo también.
ifneq ($(strip $(TESTCASE)),)
export TESTCASE
endif

# ----------------------------------------------------------------------------
# Targets.
# ----------------------------------------------------------------------------
.PHONY: all
all: test

.PHONY: test
test:
	$(MAKE) -f $(shell cocotb-config --makefiles)/Makefile.sim \
	    SIM=$(SIM) \
	    TOPLEVEL_LANG=$(TOPLEVEL_LANG) \
	    VERILOG_SOURCES="$(VERILOG_SOURCES)" \
	    TOPLEVEL=$(TOPLEVEL) \
	    MODULE=$(MODULE) \
	    $(if $(strip $(TESTCASE)),TESTCASE=$(TESTCASE),)

.PHONY: clean
clean:
	rm -rf sim_build results.xml *.vcd *.fst *.vvp \
	       __pycache__ $(MODULE_DIR)/__pycache__

# ----------------------------------------------------------------------------
# Atajos útiles. No son obligatorios pero documentan ejemplos comunes.
# ----------------------------------------------------------------------------
.PHONY: smoke
smoke:
	$(MAKE) MODULE=test_smoke \
	        MODULE_DIR=$(TOPDIR)/tests \
	        VERILOG_SOURCES=$(TOPDIR)/rtl/counter.v \
	        TOPLEVEL=counter
