# ============================================================================
# Makefile — Lab 1 (Skeleton del alumno): contador síncrono de 8 bits.
# ----------------------------------------------------------------------------
# Misma estructura que el Makefile de la solución.
# Default simulator: icarus. Override con: SIM=verilator make
# ============================================================================

# Directorio donde vive ESTE Makefile.
TOPDIR := $(abspath $(dir $(lastword $(MAKEFILE_LIST))))

# Ruta al RTL compartido.
RTLDIR := $(TOPDIR)/../../rtl

# --- Configuración del simulador ---
SIM            ?= icarus
TOPLEVEL_LANG  ?= verilog

# --- Fuentes y toplevel ---
VERILOG_SOURCES := $(RTLDIR)/counter.v
TOPLEVEL        := counter

# --- Módulo Python con los tests (sin extensión .py) ---
MODULE          := test_counter

# Exportar variables al entorno para el sub-make.
export SIM
export TOPLEVEL_LANG
export VERILOG_SOURCES
export TOPLEVEL
export MODULE

# PYTHONPATH para que cocotb encuentre test_counter.py.
export PYTHONPATH := $(TOPDIR):$(PYTHONPATH)

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
	    MODULE=$(MODULE)

# Genera waveforms VCD en waves/counter.vcd (Icarus).
.PHONY: waves
waves:
	@mkdir -p $(TOPDIR)/waves
	@echo "// Wrapper auto-generado para dump VCD" > $(TOPDIR)/waves/dump.v
	@echo "module dump;"                          >> $(TOPDIR)/waves/dump.v
	@echo "  initial begin"                       >> $(TOPDIR)/waves/dump.v
	@echo "    \$$dumpfile(\"$(TOPDIR)/waves/counter.vcd\");" \
	                                              >> $(TOPDIR)/waves/dump.v
	@echo "    \$$dumpvars(0, counter);"          >> $(TOPDIR)/waves/dump.v
	@echo "  end"                                 >> $(TOPDIR)/waves/dump.v
	@echo "endmodule"                             >> $(TOPDIR)/waves/dump.v
	$(MAKE) -f $(shell cocotb-config --makefiles)/Makefile.sim \
	    SIM=$(SIM) \
	    TOPLEVEL_LANG=$(TOPLEVEL_LANG) \
	    VERILOG_SOURCES="$(VERILOG_SOURCES) $(TOPDIR)/waves/dump.v" \
	    TOPLEVEL=$(TOPLEVEL) \
	    MODULE=$(MODULE) \
	    COMPILE_ARGS="-s dump"
	@if [ -s $(TOPDIR)/waves/counter.vcd ]; then \
	    echo ""; \
	    echo "Waveform generado: $(TOPDIR)/waves/counter.vcd"; \
	    echo "Tamaño: $$(du -h $(TOPDIR)/waves/counter.vcd | cut -f1)"; \
	    echo "Ábrelo con GTKWave local o la extensión Surfer en VS Code."; \
	else \
	    echo ""; \
	    echo "ERROR: waves/counter.vcd no se generó o está vacío."; \
	    exit 1; \
	fi

.PHONY: clean
clean:
	rm -rf sim_build results.xml *.vcd *.fst *.vvp \
	       __pycache__ \
	       $(TOPDIR)/waves/counter.vcd \
	       $(TOPDIR)/waves/dump.v
