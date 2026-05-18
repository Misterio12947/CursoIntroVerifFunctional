# ============================================================================
# Makefile — Lab 3 (Solución maestra): ALU con pyUVM.
# ----------------------------------------------------------------------------
# Soporta:
#     make                              # ejecuta el test UVM (50 transacciones)
#     make waves                        # con generación de VCD
#     make clean
# ============================================================================

TOPDIR := $(abspath $(dir $(lastword $(MAKEFILE_LIST))))
RTLDIR := $(TOPDIR)/../../rtl

SIM            ?= icarus
TOPLEVEL_LANG  ?= verilog

VERILOG_SOURCES := $(RTLDIR)/alu.v
TOPLEVEL        := alu

MODULE          := test_alu

TESTCASE ?=

export SIM
export TOPLEVEL_LANG
export VERILOG_SOURCES
export TOPLEVEL
export MODULE

export PYTHONPATH := $(TOPDIR):$(PYTHONPATH)

ifneq ($(strip $(TESTCASE)),)
export TESTCASE
endif

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

.PHONY: waves
waves:
	@mkdir -p $(TOPDIR)/waves
	@echo "// Wrapper auto-generado para dump VCD" > $(TOPDIR)/waves/dump.v
	@echo "module dump;"                          >> $(TOPDIR)/waves/dump.v
	@echo "  initial begin"                       >> $(TOPDIR)/waves/dump.v
	@echo "    \$$dumpfile(\"$(TOPDIR)/waves/alu.vcd\");" \
	                                              >> $(TOPDIR)/waves/dump.v
	@echo "    \$$dumpvars(0, alu);"              >> $(TOPDIR)/waves/dump.v
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
	@if [ -s $(TOPDIR)/waves/alu.vcd ]; then \
	    echo ""; \
	    echo "Waveform generado: $(TOPDIR)/waves/alu.vcd"; \
	    echo "Tamaño: $$(du -h $(TOPDIR)/waves/alu.vcd | cut -f1)"; \
	    echo "Ábrelo con GTKWave local o la extensión Surfer en VS Code."; \
	else \
	    echo ""; \
	    echo "ERROR: waves/alu.vcd no se generó o está vacío."; \
	    exit 1; \
	fi

.PHONY: clean
clean:
	rm -rf sim_build results.xml *.vcd *.fst *.vvp \
	       __pycache__ \
	       $(TOPDIR)/waves/alu.vcd \
	       $(TOPDIR)/waves/dump.v
