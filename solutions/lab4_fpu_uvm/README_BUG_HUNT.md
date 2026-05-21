# Guía de Bug Hunting — Lab 4 FPU

> **Solo lee este archivo si te has bloqueado**. El ejercicio de bug
> hunting está diseñado para que descubras el bug **por tu cuenta**
> analizando el comportamiento de tu testbench. Las pistas se
> revelan progresivamente.

## Contexto

En el Lab 4 verificas la FPU contra `rtl/fpu.v` (correcto). Como
ejercicio extra:

```bash
make clean
make TESTBENCH=buggy
```

Esto ejecuta tu testbench contra `rtl/fpu_buggy.v`, una variante con un
bug deliberado. Tu testbench, sin modificar, debe detectar el bug.

**Tu objetivo**: encontrar el bug, describirlo en tus palabras.

---

## Fase 1 — Observa

Ejecuta `make TESTBENCH=buggy` y mira el log completo.

### Preguntas para guiar tu observación:

1. ¿Cuántas transacciones fallaron de 220?
2. ¿Las transacciones fallidas son aleatorias, o tienen un patrón?
3. ¿El `diff_ulp` es similar entre fallos, o varía enormemente?
4. ¿Algún CoverPoint quedó por debajo del 100%?

**Antes de continuar a la Fase 2**, escribe tus respuestas. Si crees ya
saber qué está pasando, no leas más: ve directamente al archivo
`rtl/fpu_buggy.v` y busca la línea sospechosa.

---

## Fase 2 — Patrón

> Pista mínima.

Las transacciones fallidas comparten algo en común sobre los **signos
de a y b**. Mira las primeras 5-10 transacciones que el scoreboard
reportó como fallidas y agrupa por:

- ¿`a` es positivo o negativo? (bit 31)
- ¿`b` es positivo o negativo? (bit 31)
- ¿Tienen el mismo signo, o signos opuestos?

Si encuentras el patrón, lee el RTL buggy y trata de localizar **qué
rama del código se ejecuta cuando los signos son ese caso**.

---

## Fase 3 — Acotación

> Pista intermedia.

Los fallos ocurren cuando `sign_a != sign_b` (signos opuestos). En
suma flotante, esto significa que la operación efectiva es una **resta
de magnitudes**: `|a| - |b|` o `|b| - |a|`, según cuál sea mayor.

En el RTL hay un bloque `if op_sign_big == op_sign_small` (mismo
signo) con un `else` (signos distintos). El bug está en el `else`.

Ese `else` tiene a su vez una rama `if mant_big >= mant_small_aligned`.
Mira las dos asignaciones de `sum_mant` en esa rama y compara con el
RTL correcto (`rtl/fpu.v`).

---

## Fase 4 — Localización exacta

> Pista avanzada.

```bash
diff rtl/fpu.v rtl/fpu_buggy.v
```

Esto muestra exactamente las líneas que cambian. Ignora las diferencias
del header (comentarios) y enfócate en la diferencia en código.

Verás una línea como:

`<` sum_mant = {1'b0, op_mant_big} - {1'b0, op_mant_small_aligned};

`>` sum_mant = {1'b0, op_mant_big} + {1'b0, op_mant_small_aligned};


El `<` es `fpu.v` (correcto), el `>` es `fpu_buggy.v` (bug). La
diferencia es un operador.

---

## Fase 5 — Respuesta completa

### El bug

En `rtl/fpu_buggy.v` línea 71:

```verilog
sum_mant = {1'b0, op_mant_big} + {1'b0, op_mant_small_aligned};  // BUG B
```

Debería ser:

```verilog
sum_mant = {1'b0, op_mant_big} - {1'b0, op_mant_small_aligned};
```

### Por qué causa lo que observas

El bug afecta **una rama específica**: cuando los signos son opuestos
**y** la magnitud de `op_mant_big` es mayor o igual a la de
`op_mant_small_aligned`. En esa rama el RTL **suma** las mantisas en
lugar de **restarlas**.

**Cuando los signos son iguales**: el RTL toma el `if` superior, donde
suma las mantisas correctamente. Esa rama está bien.

**Cuando los signos son opuestos y `|a| < |b|`**: el RTL toma el `else`
interno (segundo caso), donde el operador `-` no fue tocado. Esa rama
también está bien.

**Cuando los signos son opuestos y `|a| >= |b|`**: el RTL toma el `if`
interno (primer caso), donde está el bug. Esa rama **siempre falla**.

### Frecuencia esperada

Con 220 transacciones (200 random + 20 dirigidas):

- ~50% tienen signos iguales: pasan (la rama está correcta).
- ~25% tienen signos opuestos con `|a| < |b|`: pasan (otra rama).
- ~25% tienen signos opuestos con `|a| >= |b|`: **fallan**.

En nuestra ejecución observada: ~30 fallos de 220, ≈ 13.6%. Ligeramente
menor al 25% teórico por la distribución específica del SEED.

---

## Entregable opcional

Si quieres practicar la escritura técnica de un bug report (habilidad
esencial en DV industrial), crea `labs/lab4_fpu_uvm/BUG_REPORT.md` con:

```markdown
# Bug Report — FPU buggy variant

## Síntoma
- Test contra rtl/fpu_buggy.v falla con ~30 discrepancias de 220 transacciones.
- Fallos restringidos a operandos con signos opuestos.

## Reproducción
$ make clean
$ make TESTBENCH=buggy
[copiar las 3 primeras líneas de fallo]

## Análisis
[tu interpretación: cuándo falla, cuándo pasa]

## Causa raíz
Archivo: rtl/fpu_buggy.v, línea 71.
Código actual: sum_mant = {1'b0, op_mant_big} + {1'b0, op_mant_small_aligned};
Esperado:      sum_mant = {1'b0, op_mant_big} - {1'b0, op_mant_small_aligned};

## Impacto
[qué operaciones específicas fallan, severidad]

## Recomendación
Reemplazar '+' por '-' en línea 71.
```

No es obligatorio, pero es el ejercicio que hace la diferencia entre
"encontré el bug" y "puedo comunicar un bug a otros ingenieros".

---

## Más allá

¿Quieres practicar más bug hunting?

### Crea tu propio bug

1. Copia `rtl/fpu.v` a `rtl/fpu_my_bug.v`.
2. Introduce un bug sutil (cambia un operador, una constante, un
   bit de un índice de slice).
3. Adapta el Makefile para soportar `TESTBENCH=my_bug`.
4. Ejecuta tu testbench y verifica que el bug se detecta.

### Variantes interesantes

- Bug en la alineación (cambia `>>` por `<<` en el shift).
- Bug en el bit implícito (omitir el `1'b1` al desempacar).
- Bug en la normalización (cambiar el límite del `for` o el `if`).

Cada uno produce un patrón de fallos distinto. Predice el patrón antes
de ejecutar y compara con la realidad. Es el ciclo completo de DV.

---

## Referencias

- DUT correcto: [`../../rtl/fpu.v`](../../rtl/fpu.v)
- DUT buggy: [`../../rtl/fpu_buggy.v`](../../rtl/fpu_buggy.v)
- Solución maestra: [`test_fpu.py`](test_fpu.py)
- Referencia técnica: [`fpu_uvm_reference.md`](fpu_uvm_reference.md)
