# Lab 2 — Modelo de referencia del FIFO

Documento de soporte para la solución maestra. Define el comportamiento
esperado del DUT y la estrategia del testbench. Es la "fuente de verdad"
contra la que el scoreboard compara.

## DUT

FIFO síncrona parametrizable definida en
[`../../rtl/fifo.v`](../../rtl/fifo.v).

```text
                +--------------------+
   clk         ►│                    │
   rst         ►│                    │
   push_valid  ►│       fifo         │
   push_data[] ►│     (DEPTH=8)      │
   pop_valid   ►│     (WIDTH=8)      ├─► pop_data[7:0]
                │                    ├─► full
                │                    ├─► empty
                +--------------------+
```

## Parámetros

| Parámetro | Valor por defecto | Significado                          |
|-----------|-------------------|--------------------------------------|
| `DEPTH`   | 8                 | Número máximo de palabras almacenadas|
| `WIDTH`   | 8                 | Ancho de cada palabra en bits        |

## Interfaz

| Señal         | Dir | Ancho   | Descripción                            |
|---------------|-----|---------|----------------------------------------|
| `clk`         | in  | 1       | Reloj.                                 |
| `rst`         | in  | 1       | Reset síncrono, activo en alto.        |
| `push_valid`  | in  | 1       | Solicitud de escritura.                |
| `push_data`   | in  | WIDTH   | Dato a escribir.                       |
| `pop_valid`   | in  | 1       | Solicitud de lectura.                  |
| `pop_data`    | out | WIDTH   | Dato leído (combinacional).            |
| `full`        | out | 1       | El FIFO está lleno.                    |
| `empty`       | out | 1       | El FIFO está vacío.                    |

## Comportamiento

En cada flanco de subida de `clk`:

```text
if (rst):
    count <= 0
    wr_ptr <= 0
    rd_ptr <= 0
    memoria <= todo cero

else:
    do_push = push_valid AND NOT full
    do_pop  = pop_valid  AND NOT empty

    if (do_push):
        mem[wr_ptr] <= push_data
        wr_ptr <= (wr_ptr + 1) mod DEPTH

    if (do_pop):
        rd_ptr <= (rd_ptr + 1) mod DEPTH

    según (do_push, do_pop):
        (1, 0): count <= count + 1
        (0, 1): count <= count - 1
        (1, 1): count <= count        # simultáneo: no cambia
        (0, 0): count <= count
```

Salidas combinacionales:

```text
pop_data = mem[rd_ptr]
full     = (count == DEPTH)
empty    = (count == 0)
```

## Reglas clave

1. **Push sobre lleno**: se ignora silenciosamente. `push_data` no se
   almacena. El alumno no recibe señal de error; debe inferirlo por
   `full=1`.
2. **Pop sobre vacío**: se ignora silenciosamente. `pop_data` puede
   tener cualquier valor (típicamente el último válido). Las flags
   no cambian.
3. **Push y pop simultáneos** con `count > 0` y `count < DEPTH`:
   ambos se ejecutan, la ocupación se mantiene.
4. **Push sobre lleno + pop simultáneo**: do_pop libera espacio, pero
   en este RTL específico `do_push = push_valid AND NOT full` se evalúa
   **con la `full` actual**, no la futura. Por tanto el push NO entra
   en ese ciclo. Esto es intencional y refleja un FIFO típico.

## Estrategia del testbench

El testbench mantiene un **modelo de referencia** en Python (un `deque`)
que refleja el estado teórico del FIFO. Cada operación del driver se
aplica también al modelo, manteniendo así un "shadow" del DUT.

El **scoreboard** (funciones `check_pop` y `check_flags`) compara el
DUT contra el modelo en cada operación crítica. Si divergen, el assert
falla con un mensaje que incluye:

- El tag del check (qué fase del test).
- El valor leído del DUT.
- El valor esperado por el modelo.
- El estado del modelo tras la operación.

Esto permite localizar el bug en segundos.

## Pruebas dirigidas vs aleatoria

| Test               | Tipo       | Cobertura objetivo                     |
|--------------------|------------|----------------------------------------|
| `test_fifo_basic`  | Dirigida   | Orden FIFO, push y pop secuenciales.   |
| `test_fifo_full`   | Dirigida   | Saturación, rechazo de push con full=1.|
| `test_fifo_empty`  | Dirigida   | Drenado, rechazo de pop con empty=1.   |
| `test_fifo_random` | Aleatoria  | Mezcla impredecible. Stress real.      |

La prueba aleatoria usa `random.Random(seed=0xC0FFEE)` para
reproducibilidad: si falla, el seed permite reproducir exactamente la
secuencia que causó el fallo.

## Limitaciones cubiertas vs no cubiertas

**Cubiertas**:

- Conteo correcto del modelo en push/pop simples.
- Flags `full`/`empty` consistentes con la ocupación.
- Wrap de los punteros `wr_ptr` y `rd_ptr` (durante `test_fifo_random`
  con `N_OPS=100` casi seguro ocurre).

**No cubiertas explícitamente** (ejercicios futuros):

- Push y pop simultáneos en el mismo ciclo (`do_push && do_pop`).
  Requiere conducir ambas señales en paralelo dentro de un solo ciclo.
- Asserts de timing (sin handshake `ready/valid`, no aplica).
- Cobertura funcional formal (ver `cocotb-coverage` en módulos
  posteriores).
