# Verificación Funcional de Circuitos Digitales con Python

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
├── .devcontainer/      Definición del entorno reproducible
│   ├── Dockerfile
│   └── devcontainer.json
├── rtl/                Diseños Verilog compartidos por todos los labs
│   └── counter.v
├── tests/              Smoke test del Día 1
│   └── test_smoke.py
├── labs/
│   └── lab1_counter/   Lab 1: contador con cocotb (skeleton del alumno)
│       ├── Makefile
│       ├── README.md
│       ├── test_counter.py
│       └── waves/
├── solutions/
│   └── lab1_counter/   Lab 1: solución maestra y referencia
│       ├── Makefile
│       ├── counter_reference.md
│       ├── expected_output.log
│       ├── test_counter.py
│       └── waves/
├── slides/             Material de presentación
├── notebooks/          Notebooks de apoyo
├── docs/               Documentación técnica
│   └── setup.md
├── Makefile            Orquestación del smoke test del Día 1
├── requirements.txt    Dependencias Python con versiones fijas
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

| Lab                                   | Foco                                     |
|---------------------------------------|------------------------------------------|
| [`lab1_counter`](labs/lab1_counter/)  | Verificación de un contador síncrono con cocotb. Introducción a corrutinas, triggers y waveforms. |

Cada laboratorio incluye:

- Versión skeleton (con `TODO`s) en `labs/<lab>/`.
- Solución maestra y referencias en `solutions/<lab>/`.

Para empezar el Lab 1, abre [`labs/lab1_counter/README.md`](labs/lab1_counter/README.md).

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
