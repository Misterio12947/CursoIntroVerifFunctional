# ============================================================================
# Makefile — Lab 2 (Skeleton del alumno): FIFO síncrona con scoreboard.
# ----------------------------------------------------------------------------
# Soporta:
#     make                              # los 4 tests
#     make TESTCASE=test_fifo_basic     # un test específico
#     make waves                        # con generación de VCD
#     make clean
# ============================================================================

TOPDIR := $(abspath $(dir $(lastword $(MAKEFILE_LIST))))
RTLDIR := $(TOPDIR)/../../rtl

# --- Configuración del simulador ---
SIM            ?= icarus
TOPLEVEL_LANG  ?= verilog

# --- Fuentes y toplevel ---
VERILOG_SOURCES := $(RTLDIR)/fifo.v
TOPLEVEL        := fifo

# --- Módulo Python con los tests ---
MODULE          := test_fifo

# TESTCASE opcional.
TESTCASE ?=

# Exportar al sub-make.
export SIM
export TOPLEVEL_LANG
export VERILOG_SOURCES
export TOPLEVEL
export MODULE

# PYTHONPATH para que cocotb encuentre test_fifo.py.
export PYTHONPATH := $(TOPDIR):$(PYTHONPATH)

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

# Generación de waveforms VCD.
.PHONY: waves
waves:
	@mkdir -p $(TOPDIR)/waves
	@echo "// Wrapper auto-generado para dump VCD" > $(TOPDIR)/waves/dump.v
	@echo "module dump;"                          >> $(TOPDIR)/waves/dump.v
	@echo "  initial begin"                       >> $(TOPDIR)/waves/dump.v
	@echo "    \$$dumpfile(\"$(TOPDIR)/waves/fifo.vcd\");" \
	                                              >> $(TOPDIR)/waves/dump.v
	@echo "    \$$dumpvars(0, fifo);"             >> $(TOPDIR)/waves/dump.v
	@echo "  end"                                 >> $(TOPDIR)/waves/dump.v
	@echo "endmodule"                             >> $(TOPDIR)/waves/dump.v
	$(MAKE) -f $(shell cocotb-config --makefiles)/Makefile.sim \
	    SIM=$(SIM) \
	    TOPLEVEL_LANG=$(TOPLEVEL_LANG) \
	    VERILOG_SOURCES="$(VERILOG_SOURCES) $(TOPDIR)/waves/dump.v" \
	    TOPLEVEL=$(TOPLEVEL) \
	    MODULE=$(MODULE) \
	    $(if $(strip $(TESTCASE)),TESTCASE=$(TESTCASE),) \
	    COMPILE_ARGS="-s dump"
	@if [ -s $(TOPDIR)/waves/fifo.vcd ]; then \
	    echo ""; \
	    echo "Waveform generado: $(TOPDIR)/waves/fifo.vcd"; \
	    echo "Tamaño: $$(du -h $(TOPDIR)/waves/fifo.vcd | cut -f1)"; \
	    echo "Ábrelo con GTKWave local o la extensión Surfer en VS Code."; \
	else \
	    echo ""; \
	    echo "ERROR: waves/fifo.vcd no se generó o está vacío."; \
	    exit 1; \
	fi

.PHONY: clean
clean:
	rm -rf sim_build results.xml *.vcd *.fst *.vvp \
	       __pycache__ \
	       $(TOPDIR)/waves/fifo.vcd \
	       $(TOPDIR)/waves/dump.v
