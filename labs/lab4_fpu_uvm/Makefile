# ============================================================================
# Makefile — Lab 4 (Skeleton): FPU IEEE 754 con pyUVM y coverage.
# ----------------------------------------------------------------------------
# Soporta:
#     make                              # ejecuta contra rtl/fpu.v (correcto)
#     make TESTBENCH=buggy              # ejecuta contra rtl/fpu_buggy.v
#     make coverage                     # genera coverage_report.html
#     make waves                        # con generación de VCD
#     make clean
# ============================================================================

TOPDIR := $(abspath $(dir $(lastword $(MAKEFILE_LIST))))
RTLDIR := $(TOPDIR)/../../rtl

SIM            ?= icarus
TOPLEVEL_LANG  ?= verilog

TESTBENCH ?= correct

ifeq ($(TESTBENCH),buggy)
VERILOG_SOURCES := $(RTLDIR)/fpu_buggy.v
$(info Using BUGGY RTL: $(VERILOG_SOURCES))
else
VERILOG_SOURCES := $(RTLDIR)/fpu.v
endif

TOPLEVEL  := fpu
MODULE    := test_fpu

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
	@echo "    \$$dumpfile(\"$(TOPDIR)/waves/fpu.vcd\");" \
	                                              >> $(TOPDIR)/waves/dump.v
	@echo "    \$$dumpvars(0, fpu);"              >> $(TOPDIR)/waves/dump.v
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
	@if [ -s $(TOPDIR)/waves/fpu.vcd ]; then \
	    echo ""; \
	    echo "Waveform generado: $(TOPDIR)/waves/fpu.vcd"; \
	    echo "Tamaño: $$(du -h $(TOPDIR)/waves/fpu.vcd | cut -f1)"; \
	else \
	    echo "ERROR: waves/fpu.vcd no se generó."; \
	    exit 1; \
	fi

.PHONY: coverage
coverage:
	@echo "NOTE: Para que 'make coverage' genere reporte, debes completar el TODO 10"
	@echo "      (cobertura) en test_fpu.py. Sin él, este target solo ejecuta test."
	$(MAKE) -f $(MAKEFILE_LIST) test
	@if [ -f coverage.yml ]; then \
	    python3 $(TOPDIR)/../../solutions/lab4_fpu_uvm/generate_coverage_html.py; \
	    echo ""; \
	    echo "=== Coverage report ==="; \
	    echo "  YAML: $(TOPDIR)/coverage.yml"; \
	    echo "  HTML: $(TOPDIR)/coverage_report.html"; \
	else \
	    echo "INFO: coverage.yml no generado (TODO 10 no implementado)."; \
	fi

.PHONY: clean
clean:
	rm -rf sim_build results.xml *.vcd *.fst *.vvp \
	       __pycache__ \
	       $(TOPDIR)/waves/fpu.vcd \
	       $(TOPDIR)/waves/dump.v \
	       $(TOPDIR)/coverage_report.html \
	       $(TOPDIR)/coverage.yml
