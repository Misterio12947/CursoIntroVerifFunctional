# Guía de configuración y verificación

Documentación de soporte para el Día 1 del curso. Cubre la apertura
del repositorio en Codespaces, la verificación manual del entorno y
los problemas más frecuentes.

## Requisitos previos

- Una cuenta de GitHub con acceso a Codespaces.
- (Alternativa local) Docker + Visual Studio Code + extensión
  *Dev Containers*.

## Apertura en Codespaces

1. Haz fork del repositorio.
2. Pulsa **Code → Codespaces → Create codespace on main**.
3. Codespaces construirá la imagen definida en
   `.devcontainer/Dockerfile` y ejecutará
   `pip install --user -r requirements.txt` como `postCreateCommand`.

La primera apertura puede tardar varios minutos. Las siguientes son
notablemente más rápidas porque la imagen se cachea.

## Verificación manual del entorno

Ejecuta los siguientes comandos en la terminal del Codespace y compara
con la salida esperada.

```bash
python --version
# Esperado: Python 3.11.x

pip --version
# Esperado: pip apuntando al Python 3.11 de la imagen base

make --version | head -n 1
# Esperado: GNU Make 4.x

git --version
# Esperado: git 2.x

iverilog -V
# Esperado: Icarus Verilog version 11.x (en Bookworm: 11.0 stable)

verilator --version
# Esperado: Verilator 5.x (versión exacta según Bookworm)

gtkwave --version
# Esperado: GTKWave 3.x (opcional)

python -c "import cocotb; print(cocotb.__version__)"
# Esperado: 1.9.2

python -c "from importlib.metadata import version; print(version('pyuvm'))"
# Esperado: 3.0.0
```

Si alguno de los comandos falla, revisa la sección
*Problemas frecuentes*.

## Ejecución de la prueba de humo

```bash
make
```

Salida esperada (resumida):

```text
...
0.00ns INFO  cocotb            Running on Icarus Verilog version 11.0 (stable)
0.00ns INFO  cocotb            Running tests with cocotb v1.9.2 from ...
0.00ns INFO  cocotb.regression Found test test_smoke.test_counter_increment
...
71.00ns INFO cocotb.counter    PASS: contador incrementa correctamente a 5
71.00ns INFO cocotb.counter    cocotb y pyuvm cargados sin errores.
71.00ns INFO cocotb.regression test_counter_increment passed
...
** TEST                               STATUS  SIM TIME (ns)  REAL TIME (s) **
** test_smoke.test_counter_increment  PASS         71.00            0.00   **
** TESTS=1 PASS=1 FAIL=0 SKIP=0                    71.00            0.13   **
```

> Nota: cocotb imprime al inicio el mensaje informativo
> `Did not detect Python virtual environment. Using system-wide Python
> interpreter`. No es un error. La instalación con `pip install --user`
> es la práctica recomendada en este Dev Container y funciona
> correctamente.

## Limpieza

```bash
make clean
```

Elimina `sim_build/`, `results.xml`, archivos `*.vcd` y `*.vvp`,
y caches de Python.

## Problemas frecuentes

### `cocotb-config: command not found`

El `postCreateCommand` no terminó o instaló en un Python distinto al
del PATH. Reintenta:

```bash
pip install --user -r requirements.txt
export PATH="$HOME/.local/bin:$PATH"
hash -r
cocotb-config --version
```

### `iverilog: not found` o `verilator: not found`

La imagen del contenedor no se construyó completamente. Desde la
paleta de comandos de VS Code:
**Codespaces: Rebuild Container**.

### `iverilog: no source files.`

Síntoma: `make` se interrumpe casi al inicio con:

```text
/usr/bin/iverilog: no source files.
make[2]: *** [.../simulators/Makefile.icarus:81: sim_build/sim.vvp] Error 1
```

Causa: las variables del `Makefile` del proyecto
(`VERILOG_SOURCES`, `TOPLEVEL`, `MODULE`) no llegaron al sub-`make`
que ejecuta `Makefile.sim` de cocotb. GNU Make no exporta variables
al entorno por defecto, así que cuando el `Makefile` delega vía
`$(MAKE) -f .../Makefile.sim`, esas variables hay que **exportarlas
explícitamente y, además, pasarlas inline** al sub-`make`.

Diagnóstico rápido:

```bash
make -n test 2>&1 | head -n 15
```

Si en la línea que invoca `vvp` ves variables vacías, p. ej.:

```text
MODULE= TESTCASE= TOPLEVEL= TOPLEVEL_LANG=verilog \
   /usr/bin/vvp -M ... sim_build/sim.vvp
```

…es exactamente este problema. Verifica que el `Makefile` del
repositorio contiene tanto las directivas `export VAR` como las
asignaciones inline (`VAR=$(VAR)`) en la línea del sub-`make`.

### El test queda colgado

Causa más común: el reloj no se inició o el reset no se desactivó.
Verifica en `tests/test_smoke.py` que existan:

- `cocotb.start_soon(Clock(dut.clk, 10, units="ns").start())` al inicio.
- La transición `dut.rst.value = 0` tras los pulsos de reset.

### `make: *** missing separator. Stop.`

El `Makefile` tiene espacios en lugar de tabs al inicio de los
comandos de regla. Reemplaza los espacios por un tab real:

```bash
grep -nP "^    " Makefile
# Cualquier coincidencia indica una línea mal indentada.
```

### Diferencias entre Codespaces y local

- Localmente, abre el repositorio en VS Code y selecciona
  **Dev Containers: Reopen in Container**. Se usa el mismo
  `Dockerfile`.
- Las versiones de `iverilog`, `verilator` y `gtkwave` dependen del
  snapshot vigente de Debian Bookworm en el momento de construir la
  imagen. Para fijarlas exactamente, anclar versiones con
  `apt-get install <paquete>=<versión>` en el `Dockerfile` y publicar
  la imagen en un registro propio.

## Limitaciones del entorno

- **pyUVM** implementa un subconjunto de UVM-1.2.
- **Verilator** puede requerir directivas o flags adicionales para
  diseños con constructos no sintetizables.
- **GitHub Codespaces** en cuentas gratuitas tiene cuotas mensuales.
  Detén tus Codespaces cuando no los uses.
  
## Integración continua

El repositorio tiene un workflow de GitHub Actions
(`.github/workflows/ci.yml`) que ejecuta automáticamente en cada
push y pull request:

| Job             | Acción                                          |
|-----------------|-------------------------------------------------|
| `smoke-test`    | `make` desde la raíz (Día 1).                   |
| `lab1-counter`  | `make -C solutions/lab1_counter` (Día 2).       |
| `lab2-fifo`     | `make -C solutions/lab2_fifo` (Día 3, 4 tests). |

Si el badge del README muestra "passing", los tres flujos se ejecutan
sin errores en un runner limpio. Si muestra "failing", alguno falló
y conviene revisar la pestaña Actions del repositorio antes de
asumir que algo está bien.

El workflow es independiente del Dev Container: instala `iverilog`,
`verilator`, `gtkwave` y los paquetes pip directamente sobre el
runner `ubuntu-latest`. El Dev Container sigue siendo la fuente de
verdad para desarrollo local y Codespaces.

## Cómo navegar entre laboratorios

Desde el Día 3 hay dos laboratorios. Cada uno tiene su propia carpeta
con `Makefile`, README y `test_*.py`:

- `labs/lab1_counter/` — Lab 1 (skeleton del alumno).
- `solutions/lab1_counter/` — Lab 1 (solución maestra + referencia).
- `labs/lab2_fifo/` — Lab 2 (skeleton del alumno).
- `solutions/lab2_fifo/` — Lab 2 (solución maestra + referencia).

El RTL en `rtl/` se comparte entre todos: una sola fuente de verdad
para cada DUT.

## Regenerar `expected_output.log`

Si la solución maestra cambia y necesitas actualizar el log de
referencia:

```bash
cd solutions/lab1_counter
make clean
make 2>&1 | tee /tmp/run.log
sed -E '/Seeding Python random module/d' /tmp/run.log > expected_output.log
git add expected_output.log
git commit -m "docs(solutions): refresh expected_output.log"
```
