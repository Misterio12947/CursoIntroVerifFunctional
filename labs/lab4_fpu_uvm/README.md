# Lab 4 — FPU IEEE 754 con pyUVM y Cobertura Funcional

> **Objetivo**: verificar funcionalmente una FPU (Floating Point Unit)
> single-precision que implementa suma flotante. Construyes un testbench
> UVM completo, mides cobertura funcional, y descubres un bug deliberado
> en un RTL alternativo.

## 1. Contexto

### DUT — `rtl/fpu.v`

Una FPU IEEE 754 single-precision que ejecuta `result = a + b` donde
`a`, `b`, `result` son números flotantes de 32 bits codificados en
IEEE 754.

| Señal      | Dir  | Ancho | Descripción                          |
|------------|------|-------|--------------------------------------|
| `clk`      | in   | 1     | Reloj.                               |
| `rst`      | in   | 1     | Reset síncrono activo alto.          |
| `a`, `b`   | in   | 32    | Operandos IEEE 754 single.           |
| `start`    | in   | 1     | Solicita ejecución.                  |
| `result`   | out  | 32    | Resultado registrado.                |
| `done`     | out  | 1     | Pulso de 1 ciclo cuando hay result.  |

**Handshake**: el alumno aplica `a`, `b`, `start=1` durante un ciclo. En
el flanco siguiente, el DUT presenta `result` y `done=1` durante un
ciclo. Mismo patrón que la ALU del Lab 3.

### Limitaciones del RTL

El DUT está simplificado para fines pedagógicos. **No** maneja:
- NaN (entradas NaN producen resultado indefinido).
- Infinity (manejo aproximado, no garantizado).
- Denormales (tratados como cero — flush to zero).
- Overflow/underflow del exponente.

**Política de redondeo: truncate** (no round-to-nearest-even). Esto
genera discrepancias de hasta ±1 ULP respecto al modelo de referencia
basado en numpy. El scoreboard usa tolerancia ±1 ULP.

## 2. Lo que vas a construir

### Arquitectura UVM (idéntica al Lab 3)
              ┌──────────────────────┐
              │      FpuTest         │
              │ ┌──────────────────┐ │
              │ │      FpuEnv      │ │
              │ │ ┌──────────────┐ │ │
              │ │ │   FpuAgent   │ │ │
              │ │ │ ┌─────────┐  │ │ │
              │ │ │ │ Driver  │──┼─┼─┼──> DUT (a,b,start)
              │ │ │ │Monitor  │<─┼─┼─┼──< DUT (result,done)
              │ │ │ │Sequencer│  │ │ │
              │ │ │ └─────────┘  │ │ │
              │ │ └──────────────┘ │ │
              │ │ ┌──────────────┐ │ │
              │ │ │ Scoreboard   │ │ │
              │ │ │ (golden_fadd │ │ │
              │ │ │  + cobertura)│ │ │
              │ │ └──────────────┘ │ │
              │ └──────────────────┘ │
              └──────────────────────┘

### Modelo de referencia

```python
def golden_fadd(a_bits, b_bits):
    a = bits_to_float32(a_bits)
    b = bits_to_float32(b_bits)
    r = np.float32(a + b)
    return float32_to_bits(r)
```

Convierte los bits IEEE 754 a `numpy.float32`, suma, devuelve los bits
del resultado. Numpy aplica round-to-nearest-even, así que difiere del
DUT (que trunca) en hasta ±1 ULP. El scoreboard tolera esa diferencia.

### Cobertura funcional (TODO 10, opcional)

Cuatro **CoverPoints** + un **CoverCross**:

| CoverPoint           | Bins                                     |
|----------------------|------------------------------------------|
| `top.sign_a`         | positive, negative                       |
| `top.sign_b`         | positive, negative                       |
| `top.exp_diff_range` | equal, close, moderate, far              |
| `top.result_sign`    | positive, negative, zero                 |
| `top.sign_cross`     | 4 combinaciones (a × b)                  |

El scoreboard llama a `sample_coverage(tr)` por cada transacción. Si
completas el TODO 10, el test exige **100% de cobertura** en los 4
CoverPoints críticos: si algún bin queda sin cubrir, el test falla.

Esto es práctica industrial real. PASS sin coverage es insuficiente.

## 3. Cómo trabajar el lab

### Orden recomendado (top-down)

Implementa los TODOs **en este orden**:

| Orden | TODO | Componente               | Justificación                         |
|-------|------|--------------------------|---------------------------------------|
| 1     | 9    | Wrapper `@cocotb.test()` | Entrada del testbench                 |
| 2     | 8    | `FpuTest`                | Top de la jerarquía UVM               |
| 3     | 7    | `FpuEnv`                 | Contenedor del agent y scoreboard     |
| 4     | 5    | `FpuAgent`               | Contenedor de driver/monitor/sequencer |
| 5     | 6    | `FpuScoreboard`          | Compara DUT vs golden                 |
| 6     | 4    | `FpuMonitor`             | Observa el DUT                        |
| 7     | 3    | `FpuDriver`              | Aplica estímulos al DUT               |
| 8     | 2    | `FpuSequence`            | Genera transacciones aleatorias       |
| 9     | 10   | Cobertura (OPCIONAL)     | Activa los decoradores `@CoverPoint`  |

Después de cada TODO, ejecuta `make`. El siguiente `NotImplementedError`
te dice qué implementar a continuación.

### Comandos

```bash
make                   # ejecuta el test contra rtl/fpu.v (correcto)
make TESTBENCH=buggy   # ejecuta contra rtl/fpu_buggy.v (ejercicio extra)
make coverage          # si completaste TODO 10, genera coverage_report.html
make waves             # genera VCD para inspección con GTKWave/Surfer
make clean             # limpia archivos generados
```

### Cuándo está terminado

Sin coverage (TODOs 1-9):
Scoreboard report: received=220, passed=220, failed=0 (±1 ULP tol.)
** TESTS=1 PASS=1 FAIL=0 SKIP=0

Con coverage (TODOs 1-10):
Scoreboard report: received=220, passed=220, failed=0 (±1 ULP tol.)
=== Reporte de cobertura funcional ===
top.sign_a, top.sign_b, top.exp_diff_range, top.sign_cross: 100%
** TESTS=1 PASS=1 FAIL=0 SKIP=0

## 4. Ejercicio extra: Bug Hunting

Una vez que tu testbench pase contra `rtl/fpu.v`, ejecuta:

```bash
make clean
make TESTBENCH=buggy
```

Tu mismo testbench, contra `rtl/fpu_buggy.v` (variante con un bug
deliberado). Esperado:
Using BUGGY RTL: .../fpu_buggy.v
... muchas líneas [SBD FAIL] ...
Scoreboard report: received=220, passed=~190, failed=~30
** TESTS=1 PASS=0 FAIL=1

Aproximadamente 15% de las transacciones fallan. Tu trabajo:

1. **Identifica el patrón** de fallos. ¿Qué tienen en común las
   transacciones que fallan? Mira las entradas `a` y `b` de cada
   `[SBD FAIL]`.
2. **Localiza la línea ofensiva** en `rtl/fpu_buggy.v`. Compara con
   `rtl/fpu.v` si te bloqueas.
3. **Describe el bug** en tus propias palabras en un comentario al
   inicio de tu `test_fpu.py` o en un archivo nuevo `BUG_REPORT.md`.

Guía paso a paso: ver `solutions/lab4_fpu_uvm/README_BUG_HUNT.md`
(léelo solo después de intentarlo).

## 5. Si te bloqueas

- **Solución maestra**: [`../../solutions/lab4_fpu_uvm/test_fpu.py`](../../solutions/lab4_fpu_uvm/test_fpu.py)
- **Referencia técnica**: [`../../solutions/lab4_fpu_uvm/fpu_uvm_reference.md`](../../solutions/lab4_fpu_uvm/fpu_uvm_reference.md)
- **Log esperado**: [`../../solutions/lab4_fpu_uvm/expected_output.log`](../../solutions/lab4_fpu_uvm/expected_output.log)
- **Guía de bug hunting**: [`../../solutions/lab4_fpu_uvm/README_BUG_HUNT.md`](../../solutions/lab4_fpu_uvm/README_BUG_HUNT.md)

## 6. Troubleshooting común

### `ModuleNotFoundError: No module named 'numpy'`

El entorno no tiene numpy instalado. En Codespaces ejecuta:
```bash
pip install -r ../../requirements.txt
```

### `Scoreboard detectó N discrepancias > 1 ULP`

Tu DUT (o tu testbench) genera resultados que difieren del modelo de
referencia por más de 1 ULP. Casos comunes:

- **El monitor empareja mal**: si `pending` se vacía o duplica, los
  resultados se asignan a la transacción equivocada. Revisa que el
  monitor capture `a, b` cuando `start=1` y los recupere cuando `done=1`.
- **El driver no respeta el handshake**: si das `start=1` durante dos
  ciclos seguidos, el DUT procesa dos transacciones encadenadas y el
  monitor se confunde.

### `Cobertura incompleta en CoverPoints críticos`

Completaste el TODO 10 pero algún bin no se cubrió. Causas comunes:

- `result_sign=zero` requiere transacciones del `FpuDirectedSequence`
  (cancelación exacta). Verifica que `FpuTest.run_phase` ejecuta primero
  `FpuSequence` y luego `FpuDirectedSequence`.
- `exp_diff_range=equal` requiere operandos con el mismo exponente
  (mismo orden de magnitud). El dirigido lo proporciona.

### `TypeError: must be real number, not list` en el logger

Si añadiste un `self.logger.info("... 100% ...", some_list)`, el `%` de
"100%" colisiona con el `%` del format specifier. Usa f-string:
```python
self.logger.info(f"Cobertura: 100% en {some_list}")
```

### Más TODOs aún por implementar tras pasar 220 transacciones

Si tu `make` pasa pero algún CoverPoint queda por debajo del 100%,
significa que las transacciones aleatorias no cubrieron todos los bins.
Necesitas que el TODO 8 (`FpuTest.run_phase`) ejecute el
`FpuDirectedSequence` después del `FpuSequence`.

## 7. Conceptos clave

| Concepto                    | Detalle                                        |
|-----------------------------|------------------------------------------------|
| IEEE 754 single             | 1 signo + 8 exp + 23 mantisa + 1 implícito     |
| Truncate vs round           | El DUT trunca; numpy redondea → ±1 ULP de error |
| ULP (Unit in Last Place)    | El "1" del LSB de la mantisa                   |
| Coverage 100%               | Todos los bins de un CoverPoint cubiertos      |
| Random + dirigido           | Random llena la mayoría; dirigido cubre rincones |
| Bug deliberado (Bug B)      | Suma cuando debería restar (signos opuestos)   |

## 8. Más allá del lab

Si terminas con coverage al 100% y bug encontrado, prueba:

- **Reduce `N_TRANSACTIONS`** a 50 random + 20 dirigido y verifica que
  los CoverPoints siguen al 100%. Si bajan, tu test no es robusto.
- **Cambia el `SEED`** (de `0xC0FFEE` a otro valor). Verifica que sigue
  pasando funcionalmente (con tolerancia ±1 ULP) y con coverage 100%.
- **Añade más CoverPoints**: `exp_a_range`, `exp_b_range`, mantisa_range.
- **Ajusta la tolerancia a 0 ULP** (igualdad exacta) y observa qué % de
  transacciones falla por el problema de redondeo. Eso te muestra
  intuitivamente cuánto impacto tiene la diferencia truncate vs round.
