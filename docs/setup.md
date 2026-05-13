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
# Esperado: Icarus Verilog version 11.x o superior

verilator --version
# Esperado: Verilator 5.x (versión exacta según Bookworm)

gtkwave --version
# Esperado: GTKWave 3.x (opcional)

python -c "import cocotb; print(cocotb.__version__)"
# Esperado: 1.9.2

python -c "import pyuvm;  print(pyuvm.__version__)"
# Esperado: 3.0.0
```

Si alguno de los comandos falla, revisa la sección
*Problemas frecuentes*.

## Ejecución de la prueba de humo

```bash
make
```

Salida esperada (resumida):
...
INFO     ... test_smoke.py ... PASS: contador incrementa correctamente a 5
INFO     ... test_smoke.py ... cocotb y pyuvm cargados sin errores.
...

** TEST                                            STATUS  ...

** test_smoke.test_counter_increment               PASS    ...

** TESTS=1 PASS=1 FAIL=0 SKIP=0                            ...


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
