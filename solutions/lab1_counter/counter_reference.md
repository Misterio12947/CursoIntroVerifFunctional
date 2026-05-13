# Lab 1 — Modelo de referencia del contador

Documento de soporte para la solución maestra. Describe el comportamiento
esperado del DUT, la tabla de verdad relevante y el diagrama de tiempos.
Es la "fuente de verdad" contra la que el testbench compara.

## DUT

```text
                +-----------------+
   clk  ───────►│                 │
   rst  ───────►│    counter      │═════►  count[7:0]
   en   ───────►│  (8-bit sync)   │
                +-----------------+
```

## Especificación funcional

| Señal       | Dirección | Ancho | Descripción                              |
|-------------|-----------|-------|------------------------------------------|
| `clk`       | Entrada   | 1     | Reloj. Flanco activo: subida.            |
| `rst`       | Entrada   | 1     | Reset síncrono, activo en alto.          |
| `en`        | Entrada   | 1     | Habilitación de conteo, activa en alto.  |
| `count`     | Salida    | 8     | Valor actual del contador (0 .. 255).    |

## Ecuación de comportamiento

En cada flanco de subida de `clk`:

```text
if (rst)         count <= 0
else if (en)     count <= count + 1
else             count <= count           // se mantiene
```

Tras alcanzar 255, el contador hace wrap a 0 (overflow natural de 8 bits).
No se gestiona overflow explícitamente: es el comportamiento por defecto
de la suma binaria sin saturación.

## Tabla de verdad (próximo valor)

| `rst` | `en` | `count_next`         |
|-------|------|----------------------|
| 1     | x    | `0`                  |
| 0     | 0    | `count` (sin cambio) |
| 0     | 1    | `count + 1`          |

`x` indica "no importa".

## Diagrama de tiempos esperado

Ejemplo: reset durante 2 ciclos, luego conteo de 5 ciclos con `en=1`,
luego 3 ciclos con `en=0` (estabilidad), luego un nuevo reset.

```text
              ___     ___     ___     ___     ___     ___     ___     ___
clk      ____|   |___|   |___|   |___|   |___|   |___|   |___|   |___|   |__

         _________________________
rst      |                        |________________________________________

                                  __________________________
en       _________________________|                         |_______________

count    [0 ][0 ][0 ][0 ][1 ][2 ][3 ][4 ][5 ][5 ][5 ][5 ][0 ]
              ↑                    ↑                         ↑
              reset activo         conta con en=1            reset de nuevo
```

Notas:
- `count` se actualiza en el flanco de subida siguiente al cambio de
  entradas (un ciclo de latencia por el flip-flop).
- Durante `rst=1`, `count=0` se fuerza en el primer flanco con `rst` alto.
- Cuando `en=0`, `count` se congela en el último valor antes de la
  transición.

## Fases del test maestro

| Fase | Acción                            | Aserción principal              |
|------|-----------------------------------|---------------------------------|
| 0    | Arranque reloj + monitor          | (sin assert; setup)             |
| 1    | Reset inicial                     | `count == 0`                    |
| 2    | Conteo 10 ciclos con `en=1`       | `count == ciclo + 1`            |
| 3    | 5 ciclos con `en=0`               | `count == valor_congelado`      |
| 4    | Reset en caliente                 | `count == 0`                    |

## Cobertura conceptual cubierta

- Conteo creciente desde 0.
- Reset síncrono desde estado distinto de cero.
- Estabilidad con `en=0`.

## Cobertura conceptual NO cubierta (ejercicios futuros)

- Wrap de 255 → 0 (overflow). Requiere 256+ ciclos.
- Toggle dinámico de `en` (en=1, 0, 1, 0, ...).
- Comportamiento de `rst` síncrono cuando llega en mitad de ciclo.

Esto se trabaja en laboratorios posteriores.
