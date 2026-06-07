# Verificación Funcional de Circuitos Digitales con Python

[![CI](https://github.com/Misterio12947/CursoIntroVerifFunctional/actions/workflows/ci.yml/badge.svg)](https://github.com/Misterio12947/CursoIntroVerifFunctional/actions/workflows/ci.yml)

**Introducción a UVM usando pyUVM, cocotb y GitHub Codespaces**

Infraestructura del curso. Permite ejecutar simulaciones de RTL Verilog
y testbenches en Python con cocotb y pyUVM, todo dentro de un entorno
reproducible que se levanta automáticamente en GitHub Codespaces.

Este repositorio cubre los primeros días del curso. Cada día añade una
capa sobre la anterior.

## Estado

Días disponibles:

- **Día 1**: infraestructura Dev Container + smoke test del contador.
- **Día 2**: laboratorio 1 (verificación del contador con cocotb), con
  solución maestra, skeleton para el alumno y waveforms.
- **Día 3**: laboratorio 2 (verificación de un FIFO con scoreboard y
  modelo de referencia Python). CI con GitHub Actions ejecuta los
  flujos en cada push.
- **Día 4**: laboratorio 3 (verificación de una ALU con **pyUVM**),
  arquitectura UVM completa: test, env, agent, driver, monitor,
  scoreboard, sequencer, sequence, transaction. Comunicación entre
  componentes vía `uvm_tlm_analysis_fifo`.
- **Día 5**: laboratorio 4 (verificación de una **FPU IEEE 754** con
  pyUVM + **cobertura funcional**). Modelo de referencia con
  `numpy.float32`, tolerancia ±1 ULP, CoverPoints + CoverCross con
  `cocotb-coverage`, reporte HTML, y ejercicio de bug hunting contra
  un RTL con bug deliberado (`rtl/fpu_buggy.v`).

## Inicio rápido

1. Haz **fork** de este repositorio en tu cuenta de GitHub.
2. En tu fork, pulsa **Code → Codespaces → Create codespace on main**.
3. Espera a que termine la construcción del contenedor y la instalación
   automática de dependencias (`postCreateCommand`). La primera vez
   puede tardar varios minutos.
4. En la terminal integrada de VS Code ejecuta:

```bash
   make
```

5. Verifica que la salida termine con `TESTS=1 PASS=1 FAIL=0`.

Si algo falla, consulta [`docs/setup.md`](docs/setup.md).

## Estructura del repositorio

```text
.
├── .github/
│   └── workflows/
│       └── ci.yml          GitHub Actions: smoke test + lab1 + lab2
├── .devcontainer/          Definición del entorno reproducible
│   ├── Dockerfile
│   └── devcontainer.json
├── rtl/                    Diseños Verilog compartidos por todos los labs
│   ├── counter.v
│   └── fifo.v
│   └── alu.v
│   ├── fpu.v
│   └── fpu_buggy.v         Variante con bug deliberado (ejercicio Lab 4)
├── tests/                  Smoke test del Día 1
│   └── test_smoke.py
├── labs/
│   ├── lab1_counter/       Lab 1: contador con cocotb (skeleton)
│   └── lab2_fifo/          Lab 2: FIFO con scoreboard (skeleton)
│   └── lab3_alu_uvm/       Lab 3: ALU con pyUVM (skeleton)
│   └── lab4_fpu_uvm/       Lab 4: FPU con pyUVM + cobertura (skeleton)
├── solutions/
│   ├── lab1_counter/       Lab 1: solución maestra y referencia
│   └── lab2_fifo/          Lab 2: solución maestra, modelo y scoreboard
│   └── lab3_alu_uvm/       Lab 3: solución maestra UVM completa
│   └── lab4_fpu_uvm/       Lab 4: solución FPU + coverage + bug hunt
├── slides/                 Material de presentación
├── notebooks/              Notebooks de apoyo
├── docs/                   Documentación técnica
│   └── setup.md
├── Makefile                Smoke test del Día 1 (parametrizable)
├── requirements.txt        Dependencias Python con versiones fijas
└── README.md
```

## Stack

| Componente        | Versión                         |
|-------------------|---------------------------------|
| Python            | 3.11 (imagen base oficial)      |
| cocotb            | 1.9.2                           |
| pyuvm             | 3.0.0                           |
| cocotb-coverage   | 1.2.0                           |
| pytest            | 8.3.3                           |
| Icarus Verilog    | provisto por Debian Bookworm    |
| Verilator         | provisto por Debian Bookworm    |
| GTKWave           | provisto por Debian Bookworm    |

Las versiones de las herramientas instaladas vía `apt` quedan
determinadas por el snapshot de Debian Bookworm vigente cuando se
construye la imagen.

## Comandos disponibles

| Comando        | Acción                                                   |
|----------------|----------------------------------------------------------|
| `make`         | Smoke test del Día 1 (ejecutado desde la raíz).          |
| `make test`    | Alias de `make`.                                         |
| `make clean`   | Elimina artefactos de simulación de la raíz.             |

Cada laboratorio tiene su propio `Makefile` con los mismos targets,
ejecutables desde la carpeta del lab. Ver `labs/<lab>/README.md` para
detalles.

## Laboratorios disponibles

| Lab                                       | Foco                                                                |
|-------------------------------------------|---------------------------------------------------------------------|
| [`lab1_counter`](labs/lab1_counter/)      | Verificación de un contador síncrono con cocotb. Corrutinas y triggers. |
| [`lab2_fifo`](labs/lab2_fifo/)            | Verificación de una FIFO síncrona con modelo de referencia Python y scoreboard. |
| [`lab3_alu_uvm`](labs/lab3_alu_uvm/)      | Verificación de una ALU con **pyUVM**: arquitectura UVM completa, TLM analysis_fifo. |
| [`lab4_fpu_uvm`](labs/lab4_fpu_uvm/)      | Verificación de una **FPU IEEE 754** con pyUVM + **cobertura funcional**. Tolerancia ±1 ULP, CoverPoints, bug hunting. |

Cada laboratorio incluye:

- Versión skeleton (con `TODO`s) en `labs/<lab>/`.
- Solución maestra y referencias en `solutions/<lab>/`.

Para empezar: [`labs/lab1_counter/README.md`](labs/lab1_counter/README.md),
[`labs/lab2_fifo/README.md`](labs/lab2_fifo/README.md),
[`labs/lab3_alu_uvm/README.md`](labs/lab3_alu_uvm/README.md) o
[`labs/lab4_fpu_uvm/README.md`](labs/lab4_fpu_uvm/README.md).

## Integración continua

GitHub Actions ejecuta automáticamente en cada push y pull request a `main`:

- `smoke-test`: smoke test del Día 1.
- `lab1-counter`: solución maestra del Lab 1.
- `lab2-fifo`: 4 tests de la solución maestra del Lab 2.
- `lab3-alu-uvm`: solución maestra UVM del Lab 3 (50 transacciones, scoreboard).
- `lab4-fpu-uvm`: solución FPU del Lab 4 (220 transacciones + cobertura 100%).

Los cinco jobs corren en paralelo en runners separados. El estado en
tiempo real se ve en el badge superior y en la pestaña
[Actions](https://github.com/Misterio12947/CursoIntroVerifFunctional/actions).

## Ejecución local (sin Codespaces)

El mismo Dev Container puede usarse en local con Docker y VS Code:

1. Instala Docker y la extensión *Dev Containers* en VS Code.
2. Clona tu fork del repositorio.
3. Abre la carpeta en VS Code y selecciona
   **Dev Containers: Reopen in Container**.

## Limitaciones conocidas

- **pyUVM** implementa un subconjunto del estándar UVM-1.2. No es un
  reemplazo completo de la implementación SystemVerilog/UVM. Algunas
  construcciones avanzadas pueden no estar disponibles.
- **Verilator** está orientado a simulación de RTL sintetizable. Diseños
  con estilos no sintetizables o constructos específicos de Verilog para
  simulación pueden requerir reescritura o flags adicionales.
- **GitHub Codespaces (plan gratuito)** tiene un límite mensual de
  horas-núcleo y de almacenamiento. Conviene **detener** los Codespaces
  cuando no se usan para evitar consumir cuota.

## Licencia

Pendiente de definir.
