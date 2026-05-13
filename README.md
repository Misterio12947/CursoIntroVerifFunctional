# Verificación Funcional de Circuitos Digitales con Python

**Introducción a UVM usando pyUVM, cocotb y GitHub Codespaces**

Infraestructura del curso. Permite ejecutar simulaciones de RTL Verilog
y testbenches en Python con cocotb y pyUVM, todo dentro de un entorno
reproducible que se levanta automáticamente en GitHub Codespaces.

Este repositorio corresponde al **Día 1**: levantar el entorno y
ejecutar una prueba de humo sobre un contador de 8 bits.

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
.
├── .devcontainer/      Definición del entorno reproducible
│   ├── Dockerfile
│   └── devcontainer.json
├── rtl/                Diseños Verilog
│   └── counter.v
├── tests/              Tests cocotb / pyUVM
│   └── test_smoke.py
├── labs/               Laboratorios guiados (próximos días)
├── solutions/          Soluciones de los laboratorios
├── slides/             Material de presentación
├── notebooks/          Notebooks de apoyo
├── docs/               Documentación técnica
│   └── setup.md
├── Makefile            Orquestación de simulación
├── requirements.txt    Dependencias Python con versiones fijas
└── README.md

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
| `make`         | Alias de `make test`.                                    |
| `make test`    | Compila el RTL con Icarus y ejecuta el test cocotb.      |
| `make clean`   | Elimina artefactos de simulación.                        |

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
