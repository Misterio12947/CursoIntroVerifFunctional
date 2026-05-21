# Lab 4 — Referencia técnica: FPU + pyUVM + Cobertura Funcional

Este documento describe en detalle la arquitectura del testbench UVM para
la FPU, el comportamiento del DUT, y las decisiones de diseño que el
estudiante puede consultar cuando se bloquea.

> **Antes de leer**: este documento es referencia, no tutorial. Si es tu
> primer contacto con el lab, lee primero
> [`../../labs/lab4_fpu_uvm/README.md`](../../labs/lab4_fpu_uvm/README.md).

## Parte 1 — El DUT: FPU IEEE 754 single-precision

### Interfaz

| Señal      | Dir  | Ancho | Descripción                                  |
|------------|------|-------|----------------------------------------------|
| `clk`      | in   | 1     | Reloj síncrono.                              |
| `rst`      | in   | 1     | Reset síncrono activo alto.                  |
| `a`, `b`   | in   | 32    | Operandos IEEE 754 single-precision.         |
| `start`    | in   | 1     | Solicita ejecución de `result = a + b`.      |
| `result`   | out  | 32    | Resultado registrado (1 ciclo de latencia).  |
| `done`     | out  | 1     | Pulso de 1 ciclo, asertado con `result`.     |

### Formato IEEE 754 single-precision

```
Bit:    31 30        23 22                       0
        ┌──┬───────────┬─────────────────────────┐
        │S │  exponent │      mantissa           │
        └──┴───────────┴─────────────────────────┘
         1 bit  8 bits           23 bits
```

- **S (signo)**: 0 = positivo, 1 = negativo.
- **exponent**: 8 bits con bias 127. El exponente real es `exp - 127`.
- **mantissa**: 23 bits. Hay un **bit implícito** (1) a la izquierda del
  punto, así que la mantisa real es `1.fraction`.

Valor representado:

```
(-1)^S × 1.mantissa × 2^(exp - 127)
```

Ejemplos:

| Valor      | Bits IEEE 754 | Signo | Exp (bias) | Exp real | Mantisa  |
|------------|---------------|-------|------------|----------|----------|
| `+1.0`     | `0x3F800000`  | 0     | 127        | 0        | 1.0      |
| `-1.0`     | `0xBF800000`  | 1     | 127        | 0        | 1.0      |
| `+2.0`     | `0x40000000`  | 0     | 128        | 1        | 1.0      |
| `+0.5`     | `0x3F000000`  | 0     | 126        | -1       | 1.0      |
| `+π`       | `0x40490FDB`  | 0     | 128        | 1        | 1.5708   |

### Algoritmo de suma flotante (fadd)

Calcular `result = a + b` en IEEE 754 requiere cinco pasos:

1. **Desempacar**:
```
   sign_a, exp_a, mant_a = a[31], a[30:23], {1, a[22:0]}    // 24 bits
   sign_b, exp_b, mant_b = b[31], b[30:23], {1, b[22:0]}
```

2. **Alinear**: el operando con menor exponente desplaza su mantisa a la
   derecha hasta igualar el exponente del mayor.
```
   if exp_a >= exp_b:
     mant_b_aligned = mant_b >> (exp_a - exp_b)
     final_exp = exp_a
   else:
     mant_a_aligned = mant_a >> (exp_b - exp_a)
     final_exp = exp_b
```

3. **Sumar o restar** según los signos:
```
   if sign_a == sign_b:                      # mismo signo
     sum_mant = mant_big + mant_small_aligned
     result_sign = sign_big
   else:                                     # signos opuestos
     if mant_big >= mant_small_aligned:
       sum_mant = mant_big - mant_small_aligned
       result_sign = sign_big
     else:
       sum_mant = mant_small_aligned - mant_big
       result_sign = sign_small
```

4. **Normalizar**: garantizar que el bit más significativo de la mantisa
   sea 1 (forma normalizada).
```
   if sum_mant tiene carry (bit 24 = 1):
     sum_mant = sum_mant >> 1
     final_exp = final_exp + 1
   else mientras sum_mant[23] == 0:
     sum_mant = sum_mant << 1
     final_exp = final_exp - 1
```

5. **Empacar**:
```
   result = {result_sign, final_exp[7:0], sum_mant[22:0]}
```

### Política de redondeo: truncate

El DUT **descarta** los bits perdidos durante el shift de alineación.
Esto causa errores de hasta ±1 ULP frente al estándar IEEE 754
round-to-nearest-even (que numpy implementa).

**Ejemplo concreto**:

- Operandos: `a = 1.0` (`0x3F800000`), `b = 1.5e-7` (cerca del LSB de
  la mantisa de 1.0).
- DUT (truncate): `0x3F800000` (devuelve 1.0, descarta el bit que se
  habría sumado).
- Numpy (round-to-nearest-even): `0x3F800001` (redondea hacia arriba).
- Diferencia: 1 ULP.

Por eso el scoreboard tolera ±1 ULP. Ver Parte 4 para más detalle.

### Limitaciones documentadas

| Caso              | Comportamiento del DUT                  |
|-------------------|------------------------------------------|
| NaN (exp=255)     | Indefinido. No usar.                    |
| Infinity (exp=255)| Aproximado, no garantizado.             |
| Denormales (exp=0)| Tratados como cero (flush to zero).     |
| Overflow del exp  | Wraparound silencioso.                  |

El generador `random_safe_float32` evita exp=0 y exp=255 precisamente
por estas limitaciones. Usa exponentes entre 60 y 200 (~10⁻²⁰ a ~10²²).

### Cycle-by-cycle: ejemplo `1.0 + 0.5 = 1.5`

| Ciclo | `clk` | `start` | `a`          | `b`          | `result`     | `done` | Comentario                     |
|-------|-------|---------|--------------|--------------|--------------|--------|--------------------------------|
| 0     | ↑     | 0       | 0x00000000   | 0x00000000   | 0x00000000   | 0      | Idle.                          |
| 1     | ↑     | 1       | 0x3F800000   | 0x3F000000   | 0x00000000   | 0      | Driver aplica operandos.       |
| 2     | ↑     | 0       | (don't care) | (don't care) | 0x3FC00000   | 1      | DUT publica 1.5, asserts done. |
| 3     | ↑     | 0       | -            | -            | 0x3FC00000   | 0      | Done baja. result se mantiene. |

El monitor muestrea en cada flanco: captura `(a, b)` en ciclo 1
(`start=1`), recupera el par en ciclo 2 (`done=1`), lee `result`, y
publica la transacción.

## Parte 2 — Arquitectura del testbench

### Las 9 clases UVM (igual al Lab 3)

```
                       ┌──────────────────────┐
                       │       FpuTest        │
                       │  ┌────────────────┐  │
                       │  │     FpuEnv     │  │
                       │  │ ┌────────────┐ │  │
                       │  │ │  FpuAgent  │ │  │
                       │  │ │ ┌────────┐ │ │  │
                       │  │ │ │ Driver │─┼─┼──┼──► DUT (a, b, start)
                       │  │ │ │ Monitor│◄┼─┼──┼──◄ DUT (result, done)
                       │  │ │ │Sequencer│ │  │
                       │  │ │ └────────┘ │ │  │
                       │  │ └────────────┘ │  │
                       │  │ ┌────────────┐ │  │
                       │  │ │ Scoreboard │ │  │
                       │  │ │(golden_fadd│ │  │
                       │  │ │ + coverage)│ │  │
                       │  │ └────────────┘ │  │
                       │  └────────────────┘  │
                       └──────────────────────┘
```

### Responsabilidades

| Clase                 | Responsabilidad                                           |
|-----------------------|-----------------------------------------------------------|
| `FpuTransaction`      | Datos de una transacción: a, b, result.                   |
| `FpuSequence`         | Genera N transacciones random con seed fijo.              |
| `FpuDirectedSequence` | Genera 20 transacciones dirigidas a bins difíciles.       |
| `FpuDriver`           | Aplica handshake start/done. Lee tx, escribe en DUT.      |
| `FpuMonitor`          | Observa el DUT, empareja entrada con salida, publica tx.  |
| `FpuSequencer`        | Arbitra sequences que quieren hablar con el driver.       |
| `FpuAgent`            | Contiene driver, monitor, sequencer. Conexión TLM interna. |
| `FpuScoreboard`       | Compara con golden_fadd. Sample coverage. Reporta.        |
| `FpuEnv`              | Contiene agent + scoreboard. Conexión TLM agent→sbd.      |
| `FpuTest`             | Top. Instancia env. Ejecuta random + dirigido.            |

### Data flow de una transacción

```
┌─────────────────────┐
│ FpuSequence.body    │     1. randomize(rng) → genera (a, b)
│ (o Directed)        │
└──────────┬──────────┘
           │ start_item/finish_item
           ▼
┌─────────────────────┐
│ FpuSequencer        │     2. Buffer la transacción
└──────────┬──────────┘
           │ seq_item_port.get_next_item()
           ▼
┌─────────────────────┐     3. Aplica a, b, start=1 en el DUT
│ FpuDriver._drive    │        Espera 1 ciclo
│                     │        Baja start
└─────────────────────┘

(El DUT calcula y publica result + done en el siguiente flanco)

┌─────────────────────┐     4. Captura (a, b) cuando ve start=1
│ FpuMonitor          │        Lo guarda en self.pending (deque)
│ .run_phase          │        Cuando ve done=1, lee result
│                     │        Crea FpuTransaction con (a, b, result)
│                     │        analysis_port.write(tr)
└──────────┬──────────┘
           │ analysis_port
           ▼
┌─────────────────────┐     5. Recibe la transacción del monitor
│ FpuScoreboard       │        sample_coverage(tr) ← bins se marcan
│ ._check             │        expected = golden_fadd(tr.a, tr.b)
│                     │        Compara con within_1_ulp tolerance
│                     │        Incrementa counters
└─────────────────────┘
```

## Parte 3 — Mismo escenario, dos estilos

Para comparar el costo y el beneficio de UVM, vamos a verificar la misma
condición en dos estilos:

**Escenario**: aplicar `1.0 + 0.5`, esperar resultado `1.5`.

### Estilo cocotb plano (estilo Lab 1)

```python
@cocotb.test()
async def test_fpu_add(dut):
    cocotb.start_soon(Clock(dut.clk, 10, units="ns").start())

    # Reset
    dut.rst.value = 1
    for _ in range(3):
        await RisingEdge(dut.clk)
    dut.rst.value = 0
    await RisingEdge(dut.clk)

    # Aplica 1.0 + 0.5
    await RisingEdge(dut.clk)
    dut.a.value     = 0x3F800000  # +1.0
    dut.b.value     = 0x3F000000  # +0.5
    dut.start.value = 1
    await RisingEdge(dut.clk)
    dut.start.value = 0

    # Espera done
    while int(dut.done.value) != 1:
        await RisingEdge(dut.clk)

    # Verifica
    result = int(dut.result.value)
    expected = 0x3FC00000  # +1.5
    assert abs(result - expected) <= 1, (
        f"Esperaba {expected:08X}, obtuve {result:08X}"
    )
```

~25 líneas. Una transacción.

### Estilo pyUVM (este lab)

Para verificar la misma condición necesitas las 9 clases UVM y el
wrapper (~280 líneas distribuidas). La transacción individual es:

```python
# En FpuDirectedSequence.body, una entrada:
(0x3F800000, 0x3F000000)   # 1.0 + 0.5

# Que va por:
#   Sequence → Sequencer → Driver → DUT → Monitor → Scoreboard
# El Scoreboard hace:
#   expected = golden_fadd(0x3F800000, 0x3F000000)   # devuelve 0x3FC00000
#   within_1_ulp(dut_result, expected)               # True
#   sample_coverage(tr)                              # marca bins
```

### Comparación

|                         | cocotb plano         | pyUVM                       |
|-------------------------|----------------------|------------------------------|
| Setup inicial           | ~20 líneas           | ~280 líneas (9 clases)       |
| Añadir 1 transacción    | ~10 líneas           | 1 entrada en sequence        |
| Añadir 100 transacciones| Bucle + ~30 líneas   | `for _ in range(100): ...`   |
| Modelo de referencia    | Inline               | Función separada             |
| Cobertura               | Manual               | Decoradores `@CoverPoint`    |
| Cambiar el DUT          | Reescribir test      | Sustituir agent driver/monitor|
| Mantenibilidad          | Baja                 | Alta                          |
| Curva de aprendizaje    | Baja                 | Media                         |

**Cuándo cocotb plano es mejor**: scripts puntuales, validación de
un DUT simple, sin reuso.

**Cuándo pyUVM es mejor**: testbench de un módulo que va a evolucionar,
verificación a largo plazo, múltiples sequences, equipo grande,
cobertura funcional.

El Lab 4 es donde pyUVM realmente brilla: el coverage funcional sería
mucho más doloroso de implementar en cocotb plano.

## Parte 4 — Lecciones específicas del Lab 4

### Lección 1: ¿Por qué tolerancia ±1 ULP?

**ULP (Unit in Last Place)**: el valor del bit menos significativo de la
mantisa. Si la mantisa son los bits `[22:0]`, 1 ULP es el incremento que
provoca cambiar el bit 0 de la mantisa.

Numéricamente: para un valor float32 con exponente `e`, 1 ULP es
`2^(e - 127 - 23)`.

**Por qué se diferencia el DUT del modelo**:

- **DUT**: trunca los bits descartados durante la alineación. Si la
  mantisa de B se shifta 5 bits, esos 5 bits se pierden sin redondear.
- **Numpy (round-to-nearest-even)**: examina los bits descartados. Si
  el bit más alto descartado es 1, redondea hacia arriba (excepto el
  caso "exacto 0.5", donde redondea hacia par).

**Consecuencia**: alrededor del 50% de las transacciones random tendrán
un mismatch de 1 ULP. NO es un bug. Es una decisión de diseño del DUT.

**Tolerancia ±1 ULP en el scoreboard**:

```python
def within_1_ulp(dut_bits, ref_bits):
    return abs(int(dut_bits) - int(ref_bits)) <= 1
```

Compara bits como enteros. Si difieren en 0 o 1, OK. Si difieren en 2+,
hay un bug real.

**Práctica industrial**: este patrón es estándar en DV de FPU. Nadie
compara bit-exacto cuando RTL y modelo difieren en política de
redondeo. Las tolerancias típicas son 0.5 ULP (round-to-nearest-even
real) o 1 ULP (truncate o round-down).

### Lección 2: ¿Por qué random + dirigido?

El test random aleatorio cubre la **mayoría** del espacio:

- `sign_a` (positive/negative): cada uno aparece ~50% de las veces.
- `sign_b`: igual.
- `sign_cross`: 4 combinaciones, cada una ~25%.
- `exp_diff_range = far`: la mayoría de pares aleatorios tienen
  exponentes muy distintos (entre 60 y 200). El bin "far" se llena
  inmediatamente.
- `exp_diff_range = equal`: requiere que `exp_a == exp_b`
  exactamente. Probabilidad: 1/140 ≈ 0.7%.

El bin **`result_sign = zero`** es **imposible** con random aleatorio
en operandos no triviales: requiere cancelación exacta (`a + (-a)`),
que random no produce con probabilidad práctica.

**Solución: sequence dirigida**. El `FpuDirectedSequence` incluye:

```python
(0x42A00000, 0xC2A00000),  # 80.0 + (-80.0) → cero exacto
(0x3F800000, 0xBF800000),  # 1.0 + (-1.0)   → cero exacto
(0xBF800000, 0x3F800000),  # -1.0 + 1.0     → cero exacto
```

Estas 3 entradas garantizan que `result_sign=zero` reciba al menos 3
hits, llevando el CoverPoint al 100%.

**Lección general**: random es necesario para volumen, dirigido es
necesario para corner cases. Los dos juntos = cobertura completa.

### Lección 3: ¿Por qué la cobertura es fallible?

**Caso A (test sin cobertura)**: el testbench corre 200 transacciones,
verifica que cada una pase contra el modelo, y declara PASS.

Problema: ¿estás seguro de haber probado los casos relevantes? Quizás
todas las 200 random tuvieron `sign_a = 0`. Quizás ninguna tuvo signos
opuestos. Si tu testbench solo prueba un slice del espacio, un bug en
otro slice queda invisible.

**Caso B (test con cobertura fallible al 100%)**: el testbench corre,
verifica funcionalidad, **y además** verifica que cada bin de cada
CoverPoint crítico haya sido tocado al menos una vez. Si algún bin
quedó vacío, el test falla.

Esto fuerza al diseñador del test a **demostrar** que cubrió el espacio
relevante, no solo que pasó. Es la diferencia entre "no encontré bugs"
y "demuestro que probé X cosas".

**Industria**: la métrica clave en DV no es "tests pasan" sino "tests
pasan + coverage al 100%". El primero es necesario; el segundo es lo
que vendes a los stakeholders cuando dices "este DUT está verificado".

### Lección 4: Helpers IEEE 754

Cuatro helpers proporcionados (no son objetivo de aprendizaje pero
conviene entender qué hacen):

```python
def random_safe_float32(rng):
    # Genera bits IEEE 754 evitando NaN, Inf, denormales.
    # Exp en [60, 200] → magnitudes en [~10⁻²⁰, ~10²²].

def bits_to_float32(bits):
    # uint32 → numpy.float32. Vía np.frombuffer (interpretación de bits).

def float32_to_bits(f):
    # numpy.float32 → uint32. Vía np.frombuffer también.

def golden_fadd(a_bits, b_bits):
    # Modelo de referencia: bits → numpy → +  → bits.
    # numpy aplica round-to-nearest-even automáticamente.

def within_1_ulp(dut_bits, ref_bits):
    # Tolerancia: difiere a lo sumo en 1 bit en representación entera.
```

### Lección 5: El monitor empareja entradas con salidas

Mismo patrón que el Lab 3 (ALU), pero crítico de entender:

```python
async def run_phase(self):
    from collections import deque
    pending = deque()

    while True:
        await RisingEdge(self.dut.clk)
        await Timer(1, units="ns")   # Margen para que las señales se estabilicen

        if int(self.dut.start.value) == 1:
            # Captura los operandos en el momento que el driver los aplica
            pending.append((int(self.dut.a.value), int(self.dut.b.value)))

        if int(self.dut.done.value) == 1 and len(pending) > 0:
            # Recupera los operandos correspondientes (en orden FIFO)
            a, b = pending.popleft()
            tr = FpuTransaction()
            tr.a = a
            tr.b = b
            tr.result = int(self.dut.result.value)
            self.analysis_port.write(tr)
```

**Por qué `deque` (no variable simple)**: si el DUT estuviera pipelined
con más de 1 stage, podría haber 2+ transacciones in-flight al mismo
tiempo. La `deque` mantiene el orden FIFO. Para nuestra FPU de 1 stage,
nunca habrá más de 1 elemento pendiente, pero el patrón se generaliza.

**Por qué `Timer(1, "ns")` tras el `RisingEdge`**: las señales
registradas (`done`, `result`) se actualizan en el mismo edge, pero
hay un delta de simulación. Esperar 1 ns garantiza que la señal esté
estable cuando la leamos.

**Por qué muestrear `start` y `done` en el mismo flanco**: en este DUT,
nunca coinciden (start aplica en ciclo N, done responde en ciclo N+1).
El monitor procesa ambos eventos en flancos distintos sin conflicto.

## Referencias

- IEEE 754-2008 standard.
- cocotb-coverage docs: <https://cocotb-coverage.readthedocs.io/>
- pyUVM: <https://pyuvm.github.io/pyuvm/>
- numpy float32 internals: <https://numpy.org/doc/stable/reference/arrays.scalars.html>
- Lab 3 reference (ALU UVM): [`../lab3_alu_uvm/alu_uvm_reference.md`](../lab3_alu_uvm/alu_uvm_reference.md)
