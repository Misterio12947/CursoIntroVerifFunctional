# Lab 1 — Verificación de un contador síncrono con cocotb

**Duración estimada**: 60-90 minutos.
**Prerrequisitos**: haber completado el Día 1 (smoke test corriendo en
Codespaces).

## Objetivos de aprendizaje

Al terminar este laboratorio sabrás:

- Escribir un testbench cocotb desde cero.
- Generar un reloj y aplicar reset desde Python.
- Usar triggers (`RisingEdge`, `Timer`) para sincronizarte con la simulación.
- Lanzar corrutinas concurrentes con `cocotb.start_soon()`.
- Escribir asserts informativos que faciliten el debug.
- Generar y leer una waveform VCD del DUT.

Estas son habilidades base de cualquier ingeniero de DV moderno.

## El diseño bajo prueba (DUT)

El DUT es un contador síncrono de 8 bits. El RTL vive en
[`../../rtl/counter.v`](../../rtl/counter.v) y se comparte con el smoke
test del Día 1 y con la solución maestra.

```text
                +-----------------+
   clk  ───────►│                 │
   rst  ───────►│    counter      │═════►  count[7:0]
   en   ───────►│  (8-bit sync)   │
                +-----------------+
```

| Señal   | Dir  | Ancho | Descripción                              |
|---------|------|-------|------------------------------------------|
| `clk`   | in   | 1     | Reloj. Flanco activo: subida.            |
| `rst`   | in   | 1     | Reset síncrono, activo en alto.          |
| `en`    | in   | 1     | Habilitación de conteo, activa en alto.  |
| `count` | out  | 8     | Valor del contador (0..255, con wrap).   |

**Comportamiento** (en cada flanco de `clk`):

```text
if (rst)         count <= 0
else if (en)     count <= count + 1
else             count <= count
```

## Conceptos previos

### Qué es un DUT

DUT = *Design Under Test*. Es el módulo de hardware que estás verificando.
Aquí es `counter`. cocotb instancia tu DUT en el simulador HDL y te
entrega un objeto Python (`dut`) cuyas propiedades son las señales del
RTL: `dut.clk`, `dut.rst`, `dut.en`, `dut.count`.

Puedes leer (`int(dut.count.value)`) y escribir (`dut.en.value = 1`)
cada señal desde Python. Por debajo, cocotb traduce eso a llamadas VPI
contra el simulador.

### Qué es una corrutina

Una corrutina es una función Python que se puede **suspender** y
**reanudar**. Se define con `async def` y se suspende con `await`.

> **Analogía**: una corrutina es como un empleado multitarea. Mientras
> espera que el simulador avance, no bloquea la oficina: pasa el turno
> al siguiente empleado. Cuando llega el evento que esperaba, vuelve a
> su mesa y continúa.

Equivalente conceptual en Verilog:

| Python (cocotb)              | Verilog                       |
|------------------------------|-------------------------------|
| `async def proc(dut): ...`   | `initial begin ... end`       |
| `await RisingEdge(dut.clk)`  | `@(posedge clk);`             |
| `await Timer(10, "ns")`      | `#10;`                        |
| `cocotb.start_soon(proc(dut))` | `fork proc(...); join_none` |

### Qué es un trigger

Un trigger es una condición de espera. La corrutina queda suspendida
hasta que el simulador hace que el trigger se cumpla.

> **Analogía**: `await RisingEdge(dut.clk)` es como esperar el timbre.
> No estás haciendo trabajo activo; estás suspendido. Cuando suena
> (flanco de subida), te levantas y continúas.

Triggers más comunes:

- `RisingEdge(signal)` — flanco de subida.
- `FallingEdge(signal)` — flanco de bajada.
- `Edge(signal)` — cualquier flanco.
- `Timer(N, units="ns")` — espera de N unidades de tiempo simulado.
- `ReadOnly()` — espera al final del time-step actual (sin escrituras).

Documentación completa: <https://docs.cocotb.org/en/stable/triggers.html>

### Qué es el scheduler

El scheduler de cocotb es el componente que decide qué corrutina
avanza en cada paso de simulación. Trabaja **dentro** del time-step del
simulador HDL. Tú no lo controlas directamente; lo controlas
indirectamente a través de los `await`.

> **Analogía**: el scheduler es el director de orquesta. Cada
> corrutina es un músico. Tú escribes la partitura (los `await`); el
> director marca cuándo entra cada uno.

### Tiempo real vs tiempo simulado

Esto confunde mucho a alumnos que vienen de software puro.

- **Tiempo real**: lo que mide tu reloj de pared. Segundos reales.
- **Tiempo simulado**: lo que cuenta el simulador HDL. Nanosegundos,
  picosegundos.

Cuando escribes `await Timer(10, units="ns")`, **NO** bloqueas el CPU
10 ns. Bloqueas la corrutina hasta que el simulador HDL avance su
reloj interno 10 ns. Eso puede tardar 1 ms reales (DUT pequeño) o
varios segundos reales (DUT grande). Son magnitudes desacopladas.

## Estructura del archivo `test_counter.py`

```text
test_counter.py
├── Constantes (CLK_PERIOD_NS, RESET_CYCLES, COUNT_CYCLES)
├── generate_clock(dut, period_ns)        ← TODO 1
├── reset_dut(dut, cycles)                ← TODO 2
├── monitor_counter(dut)                  ← TODO 3
└── test_counter_basic(dut)               ← TODO 4
    ├── Fase 0: arranque (ya hecho)
    ├── Fase 1: reset                     ← TODO 4.1
    ├── Fase 2: conteo                    ← TODO 4.2
    ├── Fase 3: estabilidad               ← TODO 4.3
    └── Fase 4: reset en caliente         ← TODO 4.4
```

## Flujo del test maestro (timeline)

Así se ve la simulación cuando el test está completo:

```text
              ___     ___     ___     ___     ___     ___     ___     ___
clk      ____|   |___|   |___|   |___|   |___|   |___|   |___|   |___|   |__

         _________________________
rst      |                        |________________________________________

                                  __________________________
en       _________________________|                         |_______________

count    [0 ][0 ][0 ][0 ][1 ][2 ][3 ][4 ][5 ][5 ][5 ][5 ][0 ]
              ↑                    ↑                         ↑
              reset                conta con en=1            reset en caliente
```

## Cómo resolver el lab (ruta recomendada)

Resuelve los TODOs en orden. Cada uno debe pasar antes de seguir al
siguiente.

1. **TODO 1 — `generate_clock`**: define la corrutina del reloj.
   Lánzala desde el test con `cocotb.start_soon(generate_clock(dut))`.
   *Validación*: ya estaba lanzada en el código; al implementar la
   corrutina, los `await RisingEdge(dut.clk)` del resto del código
   dejarán de colgarse.

2. **TODO 2 — `reset_dut`**: aplica `rst=1` durante 2 ciclos y libera.
   *Validación*: el log debe mostrar `Reset liberado. count=0`.

3. **TODO 3 — `monitor_counter`**: muestrea `dut.count` cada flanco.
   *Validación*: si activas el log debug (ver "Cómo ver el monitor"
   abajo), verás una línea por ciclo.

4. **TODO 4.1 — fase de reset**: llama a `reset_dut(dut)` y verifica
   `count == 0`.

5. **TODO 4.2 — fase de conteo**: pon `en=1` y comprueba que `count`
   incrementa en uno cada ciclo durante `COUNT_CYCLES`.

6. **TODO 4.3 — fase de estabilidad**: pon `en=0` y comprueba que
   `count` no cambia durante 5 ciclos.

7. **TODO 4.4 — fase de reset en caliente**: aplica `reset_dut(dut)`
   otra vez. `count` debe volver a 0.

Cuando los 4 TODOs principales (+ subfases) estén hechos, deberías ver:

```text
TESTS=1 PASS=1 FAIL=0 SKIP=0
```

## Ejecución

Desde esta carpeta (`labs/lab1_counter/`):

```bash
make            # corre el test
make waves      # corre el test y genera waves/counter.vcd
make clean      # elimina artefactos
```

### Si quieres ver el monitor en consola

Por defecto el monitor usa `dut._log.debug(...)`, que cocotb suprime.
Para verlo, exporta antes de `make`:

```bash
export COCOTB_LOG_LEVEL=DEBUG
make
unset COCOTB_LOG_LEVEL
```

## Cómo abrir la waveform

`make waves` deja el archivo en `waves/counter.vcd`. No es directamente
abrible en Codespaces (no hay display X11 para GTKWave). Tienes dos
opciones:

### Opción A — Descargar el VCD y abrirlo con GTKWave local

1. En el panel de archivos de VS Code (Codespace), navega a
   `labs/lab1_counter/waves/`.
2. Clic derecho sobre `counter.vcd` → **Download**.
3. En tu máquina local, instala GTKWave si no lo tienes:

```bash
   sudo apt install gtkwave        # Ubuntu/Debian
   brew install gtkwave            # macOS
```

4. Abre el archivo:

```bash
   gtkwave counter.vcd &
```

### Opción B — Extensión Surfer en VS Code

1. En el Codespace, abre el panel de extensiones (Ctrl+Shift+X).
2. Busca `surfer-project.surfer` e instálala.
3. Abre `counter.vcd` haciendo doble clic. Se renderiza inline.

## Errores comunes y troubleshooting

### `NotImplementedError: TODO N: implementa ...`

No has rellenado ese TODO. Es la situación inicial esperada. Implementa
el TODO correspondiente y vuelve a ejecutar `make`.

### El test se queda colgado sin terminar

Lo más probable es que `generate_clock` no esté implementada o tenga
un error: si el reloj no avanza, ningún `await RisingEdge(dut.clk)`
del resto del código se despierta. Revisa el TODO 1.

### `AssertionError: [Fase 2] Ciclo 0: se esperaba count=1, se obtuvo 0`

El test detecta que tras un ciclo con `en=1` el contador no
incrementó. Causas típicas:

- Olvidaste poner `dut.en.value = 1` antes del bucle.
- No esperas un margen de propagación tras `RisingEdge` (usa
  `await Timer(1, units="ns")` antes de leer `dut.count.value`).
- El reset no se liberó correctamente: `rst` sigue alto.

Imprime el valor de `dut.rst.value`, `dut.en.value` y `dut.count.value`
con `dut._log.info(...)` justo antes del assert para localizar el
problema.

### `cocotb-config: command not found`

Estás corriendo `make` fuera del Dev Container / Codespaces. Cocotb
solo está instalado dentro del entorno reproducible. Abre el repo en
Codespaces o usa Dev Containers en local.

### El VCD generado está vacío

Confirma que ejecutaste `make waves` y no `make`. Y mira la salida:
debe terminar con `Waveform generado: ...counter.vcd` y un tamaño no
nulo. Si el target falla con `ERROR: waves/counter.vcd no se generó`,
revisa que tu RTL no tenga errores de sintaxis Verilog.

## Reto extra (opcional)

El test maestro **no** verifica el wrap-around de 255 → 0. Reto:
añade una **Fase 5** al test que:

1. Cuente exactamente 256 ciclos con `en=1` desde count=0.
2. Verifique que en el ciclo 256, `count == 0` (wrap).
3. Verifique que en el ciclo 257, `count == 1`.

Pista: usa una constante nueva `WRAP_CYCLES = 256` para no mezclar con
las constantes existentes.

## Si te bloqueas

1. Consulta la documentación oficial de cocotb:
   - Triggers: <https://docs.cocotb.org/en/stable/triggers.html>
   - Corrutinas: <https://docs.cocotb.org/en/stable/coroutines.html>
2. Mira el `counter_reference.md` en `solutions/lab1_counter/` para
   refrescar el comportamiento esperado del DUT.
3. Solo como **último recurso**, abre la solución maestra en
   `solutions/lab1_counter/test_counter.py`.

## Checklist de cierre

Antes de dar el lab por terminado:

- [ ] `make` termina con `TESTS=1 PASS=1 FAIL=0 SKIP=0`.
- [ ] `make waves` genera `waves/counter.vcd` con tamaño > 0.
- [ ] Abriste la waveform y verificaste visualmente que `count`
      incrementa en cada flanco con `en=1`.
- [ ] `make clean` elimina los artefactos correctamente.
- [ ] (Opcional) Resolviste el reto extra de wrap-around.
