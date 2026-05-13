FROM mcr.microsoft.com/devcontainers/python:3.11-bookworm

ENV DEBIAN_FRONTEND=noninteractive

# Herramientas de sistema y simuladores HDL de código abierto.
# Las versiones quedan determinadas por el snapshot de Debian Bookworm
# vigente en el momento de la build.
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        make \
        git \
        iverilog \
        verilator \
        gtkwave \
        ca-certificates \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Verificación temprana: si alguna herramienta no quedó instalada,
# la build falla aquí en lugar de en tiempo de uso.
RUN iverilog -V \
    && verilator --version \
    && python --version \
    && make --version | head -n 1

WORKDIR /workspaces
