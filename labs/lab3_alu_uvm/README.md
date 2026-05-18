# Lab 3 — Verificación de una ALU con pyUVM

**Duración estimada**: 180-240 minutos.
**Prerrequisitos**: haber completado el Lab 1 y Lab 2.

## Objetivos de aprendizaje

Al terminar este laboratorio sabrás:

- Construir un testbench con **arquitectura UVM completa**: test, env,
  agent, driver, monitor, scoreboard, sequencer, sequence, transaction.
- Comunicar componentes vía **TLM (Transaction-Level Modeling)** usando
  `uvm_tlm_analysis_fifo`.
- Usar **ConfigDB** para parametrizar tests sin modificar el código de
  los componentes.
- Acceder al DUT desde componentes UVM vía **`cocotb.top`**.
- Aplicar el patrón **sequence + sequence_item**: separar "qué hacer"
  de "cómo aplicarlo al DUT".

Este lab es el embrión de cualquier testbench industrial moderno.

## El DUT: ALU de 8 bits

ALU síncrona con `start`/`done` handshake, 7 operaciones implementadas
y flags `zero`/`carry`. Definida en
[`../../rtl/alu.v`](../../rtl/alu.v).

Para la especificación detallada, consulta
[`../../solutions/lab3_alu_uvm/alu_uvm_reference.md`](../../solutions/lab3_alu_uvm/alu_uvm_reference.md).

Resumen de operaciones:

| `op` | Nombre | Resultado                  |
|------|--------|----------------------------|
| 000  | ADD    | `a + b` (con carry)        |
| 001  | SUB    | `a - b` (con borrow)       |
| 010  | AND    | `a & b`                    |
| 011  | OR     | `a \| b`                   |
| 100  | XOR    | `a ^ b`                    |
| 101  | SHL    | `a << 1`                   |
| 110  | SHR    | `a >> 1`                   |
| 111  | NOP    | mantiene resultado anterior|

## ¿Por qué UVM? Comparativa con el Lab 1

El Lab 1 verificó un counter con cocotb plano: un solo test, helpers
inline, todo en un archivo lineal. Funcionó perfectamente para algo
simple. Pero a medida que los DUT crecen, ese estilo no escala.

UVM resuelve eso **distribuyendo responsabilidades** entre componentes
con roles únicos. La siguiente tabla muestra la equivalencia 1-a-1:

| Lo que haces en cocotb plano (Lab 1)         | Cómo se hace en pyUVM (Lab 3)                  | Por qué UVM lo separa así                                                      |
|----------------------------------------------|------------------------------------------------|--------------------------------------------------------------------------------|
| `cocotb.start_soon(monitor_corutina)`        | `class AluMonitor(uvm_monitor)` con `run_phase`| El monitor es un objeto con estado propio (buffer, contadores), reutilizable. |
| Helpers `push(dut, data)`, `pop(dut)` inline | `class AluDriver(uvm_driver)` con `_drive()`   | El driver es independiente del test; puedes cambiar la sequence sin tocarlo.  |
| Lista compartida `valores_esperados = []`    | `uvm_tlm_analysis_fifo` entre monitor y scbd   | Desacopla productor (monitor) y consumidor (scoreboard). Fire-and-forget.     |
| Datos hardcoded en el test                   | `class AluSequence` genera con `randomize()`   | La sequence se reutiliza en N tests; el test solo decide cuál ejecutar.       |
| `dut` accedido directamente en el test       | `cocotb.top` en cada componente                | Cada componente acceede a sus señales sin pasar `dut` como parámetro.         |
| Reloj y reset en el `@cocotb.test`           | Reloj y reset en el wrapper; el resto en UVM   | Lo de "abajo del hardware" queda en cocotb; lo de "arriba" queda en UVM.      |

> **Analogía**: imagina que verificar un DUT es como verificar la calidad de
> coches en una fábrica. En cocotb plano, una sola persona conduce el coche,
> lo observa, lo compara contra los planos, y reporta. Para un solo modelo
> simple, va bien. Para 50 modelos distintos, la misma persona no escala.
> En UVM, separas los roles: un **conductor** (driver) que solo conduce, un
> **observador** (monitor) que solo mira, un **inspector** (scoreboard) que
> solo compara, y un **director** (test) que coordina todo. Cada uno hace
> bien una cosa, y los puedes mezclar y reemplazar.

## Arquitectura que vas a construir

```text
                          AluTest (uvm_test)
                                  │
                                  │ instancia
                                  ▼
                          AluEnv (uvm_env)
                                  │
                  ┌───────────────┴───────────────┐
                  │                               │
                  ▼                               ▼
          AluAgent (uvm_agent)        AluScoreboard (uvm_component)
                  │                               ▲
      ┌───────────┼───────────┐                   │
      │           │           │                   │
      ▼           ▼           ▼                   │
   Driver   Sequencer   Monitor ── analysis_fifo ─┘
     │           ▲           │
     │           │           │
     │      AluSequence      │
     │   (genera 50 tx       │
     │    aleatorias)        │
     │                       │
     │                       ▼
     │                  (lee DUT, captura
     │                   start/done, publica tx)
     ▼
  (escribe a/b/op,
   pulsa start)
```

**Flujo de datos**:

1. **AluSequence** genera 50 transacciones aleatorias y las envía al
   AluSequencer (un buffer entre sequence y driver).
2. **AluDriver** toma cada transacción y la aplica al DUT: escribe
   `a`/`b`/`op`, pulsa `start=1` durante 1 ciclo.
3. **AluMonitor** observa el DUT. Cuando ve `start=1`, captura las
   entradas. Cuando ve `done=1` un ciclo después, construye una
   transacción con las salidas (`result`, `zero`, `carry`) y la
   publica al analysis_port.
4. **AluScoreboard** consume transacciones del FIFO con
   `await fifo.get_export.get()` y las compara contra `golden_alu()`.
   Reporta `received/passed/failed` al final.

## Estructura del archivo `test_alu.py`

```text
test_alu.py
├── Constantes (CLK_PERIOD_NS, N_TRANSACTIONS, SEED, OP_*)
├── golden_alu()                      ← TODO 1   (modelo de referencia)
├── class AluTransaction              ← TODO 2   (randomize)
├── class AluSequence                 ← TODO 3   (body)
├── class AluDriver                   ← TODO 4a, 4b
├── class AluMonitor                  ← TODO 5a, 5b
├── class AluSequencer                ← ya listo
├── class AluAgent                    ← ya listo
├── class AluScoreboard               ← TODO 6, 7
├── class AluEnv                      ← ya listo
├── class AluTest                     ← ya listo
└── @cocotb.test() wrapper            ← TODO 8
```

## Ruta de resolución recomendada

Resuelve los TODOs en este orden:

1. **TODO 8 — wrapper `@cocotb.test()`**:
   - Arranca el reloj con `cocotb.start_soon(Clock(...))`.
   - Aplica reset 3 ciclos.
   - `ConfigDB().set(None, "*", "N_TRANSACTIONS", N_TRANSACTIONS)`.
   - `ConfigDB().set(None, "*", "SEED", SEED)`.
   - `await uvm_root().run_test("AluTest")`.

   *Sin esto, el test no arranca.* Si lo ejecutas sin implementar, falla
   en la primera línea.

2. **TODO 1 — `golden_alu()`**: 8 ramas if/elif, una por opcode. El
   modelo debe coincidir exactamente con la tabla del DUT.

3. **TODO 2 — `AluTransaction.randomize()`**: tres asignaciones con
   `rng.randint(...)`.

4. **TODO 3 — `AluSequence.body()`**: loop `for _ in range(N)` con
   `start_item` y `finish_item`.

5. **TODO 4a — `AluDriver.build_phase()`**: `self.dut = cocotb.top`.

6. **TODO 4b — `AluDriver._drive()`**: aplica la transacción durante
   1 ciclo de `start=1`.

7. **TODO 5a — `AluMonitor.build_phase()`**: `self.dut = cocotb.top` +
   `self.analysis_port = self.create_analysis_port("ap")`.

8. **TODO 5b — `AluMonitor.run_phase()`**: loop con buffer `pending`.
   Atención: el monitor debe capturar entradas en el ciclo de `start=1`
   y recuperarlas un ciclo después cuando `done=1`. Esto se debe a que
   la ALU registra el resultado un ciclo después del `start`.

9. **TODO 6 — `AluScoreboard.run_phase()`**: loop con
   `await self.fifo.get_export.get()`.

10. **TODO 7 — `AluScoreboard._check()`**: llama a `golden_alu()` y
    compara. **Importante**: tras cada check, actualiza
    `self.prev_result` con `exp_result` para que el modelo siga al DUT
    en NOPs.

Cuando los 10 TODOs estén implementados, deberías ver:

```text
1580.00ns INFO  Scoreboard report: received=50, passed=50, failed=0
** TESTS=1 PASS=1 FAIL=0 SKIP=0
```

## Ejecución

Desde esta carpeta (`labs/lab3_alu_uvm/`):

```bash
make                   # ejecuta el test UVM
make waves             # con generación de VCD
make clean             # elimina artefactos
```

### Si quieres ver el detalle de cada transacción

Activa el debug log:

```bash
export COCOTB_LOG_LEVEL=DEBUG
make
unset COCOTB_LOG_LEVEL
```

Verás una línea por cada transacción procesada por el scoreboard,
incluyendo valores esperados vs vistos.

## Cómo abrir la waveform

Igual que en Labs 1 y 2. `make waves` deja `waves/alu.vcd`. Ábrelo con
GTKWave local o con la extensión Surfer en VS Code.

Útil para inspeccionar visualmente el handshake `start`/`done` y
confirmar que el cómputo aparece exactamente 1 ciclo después.

## Errores comunes y troubleshooting

### `NotImplementedError: TODO N: ...`

No has rellenado ese TODO. Implementa siguiendo el HINT del comentario
y reintenta.

### `UVMConfigItemNotFound: 'uvm_test_top...' is not in ConfigDB()`

Estás intentando recuperar un valor del ConfigDB que no se ha
registrado, o el path no coincide. Causas típicas:

- Olvidaste el `ConfigDB().set(...)` en el wrapper TODO 8.
- La clave (string) no coincide entre `set` y `get`. Son
  case-sensitive y deben ser idénticas.

### `UVMError: '*' is illegal: inst_name wildcards only allowed when storing`

Estás usando `"*"` en el segundo argumento de `ConfigDB().get(...)`.
Eso no está permitido en pyUVM 3.0.0. Las reglas son:
- `ConfigDB().set(None, "*", key, value)`: permitido.
- `ConfigDB().get(None, "", key)`: permitido.
- `ConfigDB().get(None, "*", key)`: ILEGAL.

Para parámetros como `N_TRANSACTIONS`/`SEED`, usa
`ConfigDB().get(None, "", key)`.

### `AttributeError: NoneType has no attribute 'value'`

El componente intentó usar `self.dut.algo.value` antes de que
`self.dut` esté asignado. Causas típicas:

- Olvidaste `self.dut = cocotb.top` en `build_phase` del Driver o
  Monitor.
- Llamaste a `self.dut` antes del `build_phase` (raro pero posible
  si lo pones en `__init__`).

### El scoreboard reporta `received=N` con N < 50

El monitor no está publicando todas las transacciones. Causas
típicas:

- El monitor no captura las entradas en el ciclo correcto. Recuerda:
  capturar en `start=1`, publicar en `done=1` (un ciclo después).
- Race condition: el muestreo no espera margen tras el flanco. Añade
  `await Timer(1, units="ns")` tras `await RisingEdge(dut.clk)`.

### El scoreboard reporta discrepancias en NOP

El modelo no está rastreando `prev_result`. En cada `_check`, tras
calcular `exp_result`, actualiza `self.prev_result = exp_result`.
Sin esto, el NOP del modelo compara contra cero (estado inicial)
mientras el DUT mantiene su valor real.

### El test se cuelga sin terminar

El scoreboard hace `await get()` indefinidamente esperando
transacciones que el monitor nunca publica. O `raise_objection` /
`drop_objection` no están equilibrados. Revisa que `AluTest.run_phase`
levante objeción al inicio y la baje al final.

## Reto extra (opcional)

Cuando el test pase, intenta:

1. **Sequence dirigida**: añade una `AluDirectedAddSequence` que genere
   solo operaciones ADD con valores conocidos (0+0, 255+1 para forzar
   carry, etc.). Lanza ambas sequences en `AluTest.run_phase`.

2. **Cobertura funcional**: usa `cocotb_coverage` para añadir un
   `CoverPoint` que marque cuándo cada opcode se ejecuta, cuándo
   `carry=1`, cuándo `zero=1`. Reporta los bins al final.

3. **Multi-test**: define dos `uvm_test` distintos (`AluQuickTest` con
   N=10, `AluStressTest` con N=1000) y elige cuál ejecutar vía
   `make TESTCASE=...`.

## Si te bloqueas

Sigue este orden, de menor a mayor "ayuda":

1. **Especificación detallada**:
   [`../../solutions/lab3_alu_uvm/alu_uvm_reference.md`](../../solutions/lab3_alu_uvm/alu_uvm_reference.md).

2. **Salida esperada**:
   [`../../solutions/lab3_alu_uvm/expected_output.log`](../../solutions/lab3_alu_uvm/expected_output.log).

3. **Documentación oficial**:
   - pyUVM: <https://pyuvm.github.io/pyuvm/>
   - cocotb (triggers, clocks): <https://docs.cocotb.org/en/stable/triggers.html>

4. **Último recurso — solución maestra**:
   [`../../solutions/lab3_alu_uvm/test_alu.py`](../../solutions/lab3_alu_uvm/test_alu.py).

## Checklist de cierre

- [ ] `make` termina con `TESTS=1 PASS=1 FAIL=0 SKIP=0`.
- [ ] El scoreboard reporta `received=50, passed=50, failed=0`.
- [ ] `make waves` genera `waves/alu.vcd` con tamaño > 0.
- [ ] Abriste la waveform y verificaste visualmente el handshake
      `start`/`done`.
- [ ] `make clean` elimina los artefactos correctamente.
- [ ] (Opcional) Resolviste al menos un reto extra.
