# Lab 2 — Verificación de un FIFO síncrona con cocotb

**Duración estimada**: 90-120 minutos.
**Prerrequisitos**: haber completado el Lab 1 (contador con cocotb).

## Objetivos de aprendizaje

Al terminar este laboratorio sabrás:

- Implementar un **driver** que abstrae operaciones sobre el DUT
  (push, pop, idle).
- Construir un **modelo de referencia** en Python que predice qué
  debería hacer el DUT.
- Escribir un **scoreboard** que compara DUT vs modelo en cada
  operación y reporta divergencias con contexto.
- Organizar múltiples **tests independientes** dentro de un mismo
  módulo cocotb.
- Diseñar pruebas **dirigidas** (escenarios específicos) y **aleatorias
  reproducibles** (con seed fijo).

Este patrón —driver, modelo, scoreboard— es el embrión de cualquier
testbench industrial moderno (incluyendo UVM). El Lab 1 enseñó a
hablar con el DUT; este lab enseña a **razonar sobre si el DUT está
correcto**.

## El diseño bajo prueba (DUT)

El DUT es una FIFO síncrona parametrizable definida en
[`../../rtl/fifo.v`](../../rtl/fifo.v). Por defecto `DEPTH=8` y
`WIDTH=8`.

Para la especificación detallada del comportamiento, tabla de verdad
y diagrama de tiempos, consulta:
[`../../solutions/lab2_fifo/fifo_reference.md`](../../solutions/lab2_fifo/fifo_reference.md).

Resumen rápido de la interfaz:

| Señal         | Dir | Descripción                            |
|---------------|-----|----------------------------------------|
| `clk`, `rst`  | in  | Reloj y reset síncrono activo en alto. |
| `push_valid`  | in  | Solicitud de escritura.                |
| `push_data`   | in  | Dato a escribir.                       |
| `pop_valid`   | in  | Solicitud de lectura.                  |
| `pop_data`    | out | Dato leído (combinacional).            |
| `full`        | out | FIFO lleno.                            |
| `empty`       | out | FIFO vacío.                            |

Reglas críticas:

- Push con `full=1` se ignora silenciosamente.
- Pop con `empty=1` se ignora silenciosamente.
- Push y pop simultáneos: ambos se ejecutan, la ocupación no cambia.

## Conceptos nuevos en este lab

### Modelo de referencia

El modelo es una FIFO "espejo" en Python. Aquí usamos
`collections.deque`: una lista doblemente enlazada que soporta
`append()` (push al final) y `popleft()` (pop del frente) en O(1).
Es la elección natural.

> **Analogía**: el modelo es un **narrador paralelo**. Mientras el
> DUT vive su historia (en el simulador HDL), el modelo vive la
> misma historia en Python. Si el narrador y el DUT cuentan
> versiones distintas, alguno de los dos está equivocado — y como
> el modelo es trivial, asumimos que el DUT es el sospechoso.

### Scoreboard

El scoreboard es el componente que **compara** DUT vs modelo. En este
lab son dos funciones puras:

- `check_pop(dut, model, leido, tag)`: tras un pop, comprueba que el
  valor leído del DUT coincide con el head del modelo.
- `check_flags(dut, model, tag)`: comprueba que `full` y `empty`
  coinciden con la ocupación del modelo.

Si divergen, el assert falla con un mensaje que incluye el tag, el
valor del DUT, el valor del modelo y el estado del modelo tras la
operación. Esto reduce el tiempo de debug por un factor enorme.

### Múltiples tests independientes

A diferencia del Lab 1 (un solo `@cocotb.test()` con fases), aquí
tenemos **4 tests independientes**. Cada uno arranca con un reset
propio. Beneficios:

- Aislamiento: si `test_fifo_random` falla, los otros tres siguen
  ejecutándose y vemos el panorama completo.
- Reporte: la tabla final muestra PASS/FAIL por test.
- Selectividad: puedes ejecutar solo uno con
  `make TESTCASE=test_fifo_basic`.

## Estructura del archivo `test_fifo.py`

```text
test_fifo.py
├── Constantes (DEPTH, WIDTH, CLK_PERIOD_NS, RESET_CYCLES)
├── setup_dut(dut)                ← TODO 1
├── push(dut, data)               ← TODO 2  (driver)
├── pop(dut)                      ← TODO 3  (driver)
├── idle(dut, cycles)             ← TODO 4  (driver)
├── check_pop(dut, model, leido)  ← TODO 5  (scoreboard)
├── check_flags(dut, model)       ← TODO 6  (scoreboard)
├── @cocotb.test() test_fifo_basic   ← TODO 7
├── @cocotb.test() test_fifo_full    ← TODO 8a
├── @cocotb.test() test_fifo_empty   ← TODO 8b
└── @cocotb.test() test_fifo_random  ← TODO 8c
```

## Ruta de resolución recomendada

Resuelve los TODOs en orden. La dificultad sube gradualmente.

1. **TODO 1 — `setup_dut`**: rutina conocida del Lab 1.
   Arranca el reloj con `Clock(...)`, aplica reset, comprueba
   `empty=1`, `full=0`.

2. **TODO 2 — `push`**: pulsa `push_valid` un ciclo con el `data`.
   Tras el flanco, baja `push_valid` y espera un margen de 1 ns.

3. **TODO 3 — `pop`**: lee `pop_data` (es combinacional, ya es
   válido), pulsa `pop_valid` un ciclo, baja `pop_valid` y devuelve
   el valor leído.

4. **TODO 4 — `idle`**: trivial. Apaga `push_valid` y `pop_valid`,
   espera N flancos.

5. **TODO 5 — `check_pop`**: si el modelo está vacío, retorna sin
   asserts (el DUT debe haber ignorado el pop). Si no, hace
   `model.popleft()` y compara con `leido`.

6. **TODO 6 — `check_flags`**: lee `dut.full` y `dut.empty`,
   compara con `len(model) == DEPTH` y `len(model) == 0`.

7. **TODO 7 — `test_fifo_basic`**: 5 pushes con valores conocidos,
   luego 5 pops, verificando orden FIFO en cada pop.

8. **TODO 8a — `test_fifo_full`**: llena el FIFO (DEPTH pushes),
   intenta un push extra (debe ignorarse), drena todo. **Atención**
   al modelo: si usas `deque(maxlen=DEPTH)`, en cola llena `append`
   **tira el front**, lo que NO refleja el DUT. Usa `deque()` normal
   con una condición: `if len(model) < DEPTH: model.append(data)`.

9. **TODO 8b — `test_fifo_empty`**: 3 pops sobre vacío (ignorados),
   luego un push y un pop normal para verificar que el FIFO sigue
   funcional.

10. **TODO 8c — `test_fifo_random`**: 100 operaciones aleatorias
    (push, pop, idle) con `random.Random(0xC0FFEE)`. Aplica cada
    operación al DUT y al modelo en lockstep. Verifica `check_pop`
    tras cada pop y `check_flags` tras cada operación.

Cuando los 10 TODOs estén hechos, deberías ver:

```text
TESTS=4 PASS=4 FAIL=0 SKIP=0
```

## Ejecución

Desde esta carpeta (`labs/lab2_fifo/`):

```bash
make                              # los 4 tests
make TESTCASE=test_fifo_basic     # solo un test
make waves                        # los 4 tests + VCD
make clean                        # limpia artefactos
```

### Si quieres ver el modelo paso a paso

Activa el debug log antes de ejecutar:

```bash
export COCOTB_LOG_LEVEL=DEBUG
make TESTCASE=test_fifo_random
unset COCOTB_LOG_LEVEL
```

Verás una línea por cada operación con el estado del modelo, útil
para localizar dónde diverge.

## Cómo abrir la waveform

Igual que en el Lab 1. `make waves` deja `waves/fifo.vcd`. Tienes
dos opciones:

- **Opción A**: descargar el VCD y abrirlo con GTKWave local.
- **Opción B**: extensión `surfer-project.surfer` en VS Code.

Detalles en
[`../../labs/lab1_counter/README.md#cómo-abrir-la-waveform`](../lab1_counter/README.md).

## Errores comunes y troubleshooting

### `NotImplementedError: TODO N: implementa ...`

No has rellenado ese TODO. Implementa y reintenta.

### `AssertionError: [basic-pop[0]] scoreboard mismatch: DUT leyó 0, modelo esperaba 16`

El primer pop devolvió 0 en lugar del primer valor empujado (`0x10`).
Causas típicas:

- En `pop`, lees `dut.pop_data.value` **después** de bajar `pop_valid`
  y esperar el flanco. Para entonces el FIFO ya ha avanzado `rd_ptr`.
  Lee `pop_data` **antes** del `await RisingEdge`.
- No esperas margen de propagación: añade `await Timer(1, "ns")` en
  los puntos críticos.

### `AssertionError: [full-after-fill] full mismatch: DUT=False, modelo=True`

El modelo cree que está lleno pero el DUT dice que no, o viceversa.
Causa: olvidaste guardar el dato en el modelo tras cada push, o lo
hiciste cuando el DUT ya estaba lleno (modelo desbordó pero DUT no).
Revisa el TODO 8a y la "Atención" sobre `deque(maxlen=DEPTH)`.

### `test_fifo_random` falla a partir de la operación N

Si tienes acceso al log con `COCOTB_LOG_LEVEL=DEBUG`, mira la última
operación antes del fallo. Lo más común: un push cuando el modelo
está lleno (no llamaste a `len(model) < DEPTH`) o un pop cuando el
modelo está vacío.

El seed es fijo (`0xC0FFEE`), así que el fallo es **reproducible**:
arregla, vuelve a ejecutar, y la misma secuencia se repite.

### Tests con TIMING varían sutilmente

Si comparas tu `expected_output.log` contra
`solutions/lab2_fifo/expected_output.log` y ves un timestamp distinto
en alguna línea (por ejemplo, 120 ns vs 121 ns), revisa si tus
`await Timer(...)` están en los mismos puntos que la solución. Un
margen extra de 1 ns por operación se acumula.

### `cocotb-config: command not found`

Mismo problema que en el Lab 1: estás corriendo `make` fuera del
Dev Container. Abre el repo en Codespaces o usa Dev Containers en
local.

## Reto extra (opcional)

Cuando los 4 tests pasen, intenta uno de estos:

1. **Push + pop simultáneos**: añade un `test_fifo_concurrent` que
   conduzca `push_valid=1` y `pop_valid=1` en el mismo ciclo. La
   ocupación debe mantenerse y el dato leído debe ser el más antiguo.

2. **Cobertura funcional**: usa `cocotb_coverage` (ya en
   `requirements.txt`) para añadir un `CoverPoint` que marque cuando
   `full=1`, cuando `empty=1`, y cuando ambos punteros han hecho
   wrap. Reporta los bins al final.

3. **DEPTH/WIDTH variables**: parametriza el `Makefile` para aceptar
   `make DEPTH=16 WIDTH=16`. El testbench Python debe leer esos
   parámetros del DUT (cocotb expone `dut.DEPTH.value` para
   parámetros Verilog).

## Si te bloqueas

Sigue este orden, de menor a mayor "ayuda":

1. **Especificación del DUT**:
   [`../../solutions/lab2_fifo/fifo_reference.md`](../../solutions/lab2_fifo/fifo_reference.md).

2. **Salida esperada**:
   [`../../solutions/lab2_fifo/expected_output.log`](../../solutions/lab2_fifo/expected_output.log).

3. **Documentación oficial de cocotb**:
   - Triggers: <https://docs.cocotb.org/en/stable/triggers.html>
   - Múltiples tests: <https://docs.cocotb.org/en/stable/quickstart.html>
   - `collections.deque`: <https://docs.python.org/3/library/collections.html#collections.deque>

4. **Último recurso — solución maestra**:
   [`../../solutions/lab2_fifo/test_fifo.py`](../../solutions/lab2_fifo/test_fifo.py).

## Checklist de cierre

- [ ] `make` termina con `TESTS=4 PASS=4 FAIL=0 SKIP=0`.
- [ ] `make TESTCASE=test_fifo_basic` termina con `TESTS=1 PASS=1`.
- [ ] `make waves` genera `waves/fifo.vcd` con tamaño > 0.
- [ ] Abriste la waveform y verificaste visualmente que el FIFO
      acepta los pushes y devuelve los valores en orden.
- [ ] `make clean` elimina los artefactos correctamente.
- [ ] (Opcional) Resolviste al menos un reto extra.
