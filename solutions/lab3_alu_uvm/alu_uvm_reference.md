# Lab 3 — Modelo de referencia: ALU + arquitectura pyUVM

Documento de soporte para la solución maestra del Lab 3. Define el
comportamiento del DUT, la estrategia del testbench y, lo más
importante, contrasta dos arquitecturas equivalentes: cocotb plano
(Lab 1) y pyUVM (Lab 3).

## Parte 1 — El DUT: ALU síncrona de 8 bits

### Diagrama de bloques

```text
                +---------------------+
   clk      ───►│                     │
   rst      ───►│                     │
   a[7:0]   ───►│        ALU          │═══►  result[7:0]
   b[7:0]   ───►│   (8-bit, sync)     │───►  zero
   op[2:0]  ───►│                     │───►  carry
   start    ───►│                     │───►  done
                +---------------------+
```

### Interfaz

| Señal      | Dir  | Ancho | Descripción                                 |
|------------|------|-------|---------------------------------------------|
| `clk`      | in   | 1     | Reloj.                                      |
| `rst`      | in   | 1     | Reset síncrono, activo en alto.             |
| `a`, `b`   | in   | 8     | Operandos.                                  |
| `op`       | in   | 3     | Código de operación (ver tabla).            |
| `start`    | in   | 1     | Solicita ejecución (1 ciclo).               |
| `result`   | out  | 8     | Resultado, registrado.                      |
| `zero`     | out  | 1     | Flag: 1 si `result == 0`.                   |
| `carry`    | out  | 1     | Flag: acarreo/borrow/bit desplazado fuera.  |
| `done`     | out  | 1     | Pulso de 1 ciclo cuando hay resultado nuevo.|

### Operaciones

| `op` | Nombre | `result`                          | `carry`                          |
|------|--------|-----------------------------------|----------------------------------|
| 000  | ADD    | `(a + b) & 0xFF`                  | `(a + b) >> 8`                   |
| 001  | SUB    | `(a - b) & 0xFF`                  | `1` si `b > a`, sino `0`         |
| 010  | AND    | `a & b`                           | `0`                              |
| 011  | OR     | `a \| b`                          | `0`                              |
| 100  | XOR    | `a ^ b`                           | `0`                              |
| 101  | SHL    | `(a << 1) & 0xFF`                 | `(a >> 7) & 1`                   |
| 110  | SHR    | `a >> 1`                          | `a & 1`                          |
| 111  | NOP    | `result` (sin cambio)             | `0`                              |

`zero` se calcula tras la operación: `zero = 1 si result == 0 sino 0`.

### Comportamiento ciclo a ciclo

Diagrama de tiempos para un ADD con `a=5`, `b=3`:

| Ciclo | `clk` | `rst` | `start` | `a` | `b` | `op` | `done` | `result` |
|-------|-------|-------|---------|-----|-----|------|--------|----------|
| 0     | ↑     | 1     | 0       | xx  | xx  | xxx  | 0      | 0        |
| 1     | ↑     | 0     | 0       | xx  | xx  | xxx  | 0      | 0        |
| 2     | ↑     | 0     | 1       | 5   | 3   | 000  | 0      | 0        |
| 3     | ↑     | 0     | 0       | xx  | xx  | xxx  | 1      | 8        |
| 4     | ↑     | 0     | 0       | xx  | xx  | xxx  | 0      | 8        |

- En el ciclo 2, el alumno aplica `start=1` con los operandos y opcode.
- En el ciclo 3 (un flanco después), la ALU registra el `result=8`,
  pone `done=1`, `zero=0`, `carry=0`.
- En el ciclo 4, `done` ya bajó pero `result` se mantiene.

### Reglas clave

1. **Operandos capturados en el flanco con `start=1`**: si `a`/`b`/`op`
   cambian después de ese flanco, el cálculo ya estaba hecho. Esto
   permite al alumno cambiar las entradas inmediatamente sin esperar.
2. **`done` es un pulso**, no una señal sostenida. Solo está alto un
   ciclo. Si el alumno mira más tarde, no lo ve.
3. **NOP mantiene el resultado anterior**: el flanco con `op=NOP` y
   `start=1` no cambia `result` ni los flags. Útil para verificar que
   "operaciones reservadas" no corrompen estado.
4. **Sin handshake `ready`**: la ALU siempre acepta una solicitud. No
   hay backpressure. Si el alumno aplica dos `start` consecutivos, el
   segundo sobrescribe el cálculo del primero antes de que `done` se
   propague del primero.
5. **Reset síncrono**: cuando `rst=1` en un flanco, todos los
   registros van a 0 (incluido `result`). El test inicial aplica reset
   3 ciclos para garantizar estado conocido.

## Parte 2 — Arquitectura del testbench

### Diagrama jerárquico

```text
                       AluTest (uvm_test)
                              │
                              ▼
                       AluEnv (uvm_env)
                       │              │
              ┌────────┘              └──────────┐
              ▼                                  ▼
        AluAgent (uvm_agent)            AluScoreboard (uvm_component)
          │                                      ▲
          ├── AluDriver (uvm_driver)             │
          ├── AluMonitor (uvm_monitor) ──ap──► fifo
          └── AluSequencer (uvm_sequencer)
                  ▲
                  │
              AluSequence (uvm_sequence)
                  │
                  └── genera N AluTransaction
```

- **AluTest**: punto de entrada, construye AluEnv y arranca AluSequence.
- **AluEnv**: contenedor superior; instancia agent + scoreboard,
  conecta el analysis_port del monitor al analysis_export del scoreboard.
- **AluAgent**: agrupa los tres componentes "de bajo nivel".
- **AluDriver**: aplica transacciones al DUT (pulsa `start=1`).
- **AluMonitor**: observa el DUT, construye transacciones "vistas",
  las publica al analysis_port.
- **AluSequencer**: cola entre la sequence y el driver.
- **AluScoreboard**: consume transacciones del FIFO, las compara
  contra `golden_alu()`, reporta al final.
- **AluSequence**: genera 50 transacciones aleatorias.
- **AluTransaction**: payload con `{a, b, op, result, zero, carry}`.

### Componentes y sus responsabilidades

| Componente       | Tipo UVM             | Responsabilidad                                           |
|------------------|----------------------|-----------------------------------------------------------|
| `AluTransaction` | `uvm_sequence_item`  | Datos: entradas + salidas observadas.                     |
| `AluSequence`    | `uvm_sequence`       | Generar N transacciones aleatorias.                       |
| `AluDriver`      | `uvm_driver`         | Aplicar transacciones al DUT (`start=1` por 1 ciclo).     |
| `AluMonitor`     | `uvm_monitor`        | Observar DUT, capturar `start`/`done`, publicar tx vista. |
| `AluSequencer`   | `uvm_sequencer`      | Buffer entre sequence y driver (sin lógica propia).       |
| `AluAgent`       | `uvm_agent`          | Instancia driver+monitor+sequencer; conecta puertos.      |
| `AluScoreboard`  | `uvm_component`      | Comparar tx vs `golden_alu()`, reportar.                  |
| `AluEnv`         | `uvm_env`            | Instancia agent+scoreboard; conecta analysis_port→fifo.   |
| `AluTest`        | `uvm_test`           | Construir env, arrancar sequence, gestionar objection.    |

### Flujo de datos completo

Para una sola transacción ADD con `a=5`, `b=3`:

AluSequence.body()      crea AluTransaction(a=5, b=3, op=ADD)
y la envía al AluSequencer.
AluDriver.run_phase()   recibe la tx vía seq_item_port.get_next_item().
AluDriver._drive()      escribe dut.a=5, dut.b=3, dut.op=ADD,
pulsa dut.start=1 durante 1 ciclo.
ALU (RTL)               en el siguiente flanco registra result=8,
done=1, carry=0, zero=0.
AluMonitor.run_phase()  detecta start=1 en el ciclo previo y
guarda (a=5, b=3, op=ADD) en pending.
Detecta done=1 en este ciclo, recupera
(5,3,ADD) de pending, construye una
AluTransaction con result=8, etc., y la
publica via analysis_port.write(tr).
AluScoreboard.run_phase()  hace await fifo.get_export.get(),
recibe la tx.
AluScoreboard._check()  llama a golden_alu(ADD, 5, 3, prev_result),
obtiene (8, 0, 0). Compara contra la tx.
Si coinciden: n_passed += 1.
Si no:        n_failed += 1.
Actualiza self.prev_result = 8.


## Parte 3 — El mismo escenario, dos arquitecturas

Esta es la sección clave. El mismo escenario ("aplicar ADD 5+3 al DUT,
verificar result=8") implementado de las dos formas que el curso ha
cubierto: cocotb plano (estilo Lab 1) y pyUVM (Lab 3).

### Escenario común

- DUT: la ALU.
- Estímulo: `a=5`, `b=3`, `op=ADD`.
- Verificación: el `result` registrado por la ALU debe ser `8`.

### Implementación A — cocotb plano (estilo Lab 1)

```python
@cocotb.test()
async def test_alu_add(dut):
    """Test cocotb plano: aplica ADD 5+3, verifica result=8."""

    # Setup: reloj + reset.
    cocotb.start_soon(Clock(dut.clk, 10, units="ns").start())
    dut.rst.value = 1
    for _ in range(3):
        await RisingEdge(dut.clk)
    dut.rst.value = 0
    await RisingEdge(dut.clk)

    # Aplicar la operación: a=5, b=3, op=ADD, start=1 un ciclo.
    dut.a.value     = 5
    dut.b.value     = 3
    dut.op.value    = 0    # OP_ADD
    dut.start.value = 1
    await RisingEdge(dut.clk)
    dut.start.value = 0

    # Esperar a que done suba.
    await RisingEdge(dut.clk)
    await Timer(1, units="ns")

    # Verificar.
    assert int(dut.done.value)   == 1, "done debería ser 1"
    assert int(dut.result.value) == 8, f"Esperado 8, obtuve {int(dut.result.value)}"
```

**~20 líneas. Una sola función. Todo lineal.**

### Implementación B — pyUVM (estilo Lab 3)

La misma lógica, pero distribuida en componentes. Mostramos las
piezas relevantes:

**Transaction (datos):**

```python
class AluTransaction(uvm_sequence_item):
    def __init__(self, name="alu_tr"):
        super().__init__(name)
        self.a = 0; self.b = 0; self.op = 0
        self.result = 0; self.zero = 0; self.carry = 0
```

**Sequence (qué transacciones generar):**

```python
class AluSequence(uvm_sequence):
    async def body(self):
        tr = AluTransaction()
        tr.a = 5; tr.b = 3; tr.op = 0  # ADD
        await self.start_item(tr)
        await self.finish_item(tr)
```

**Driver (cómo aplicar al DUT):**

```python
class AluDriver(uvm_driver):
    def build_phase(self):
        self.dut = cocotb.top

    async def run_phase(self):
        while True:
            tr = await self.seq_item_port.get_next_item()
            await RisingEdge(self.dut.clk)
            self.dut.a.value     = tr.a
            self.dut.b.value     = tr.b
            self.dut.op.value    = tr.op
            self.dut.start.value = 1
            await RisingEdge(self.dut.clk)
            self.dut.start.value = 0
            self.seq_item_port.item_done()
```

**Monitor (qué observar):**

```python
class AluMonitor(uvm_monitor):
    def build_phase(self):
        self.dut = cocotb.top
        self.analysis_port = uvm_analysis_port("ap", self)

    async def run_phase(self):
        # (lógica de captura start/done, publica tr al analysis_port)
        ...
```

**Scoreboard (cómo comparar):**

```python
class AluScoreboard(uvm_component):
    def build_phase(self):
        self.fifo = uvm_tlm_analysis_fifo("fifo", self)

    async def run_phase(self):
        while True:
            tr = await self.fifo.get_export.get()
            exp = golden_alu(tr.op, tr.a, tr.b, prev_result)
            assert tr.result == exp[0]
```

**Test (orquestador):**

```python
class AluTest(uvm_test):
    def build_phase(self):
        self.env = AluEnv("env", self)

    async def run_phase(self):
        self.raise_objection()
        seq = AluSequence("seq")
        await seq.start(self.env.agent.sequencer)
        self.drop_objection()
```

**Wrapper cocotb (puente entre cocotb y UVM):**

```python
@cocotb.test()
async def alu_uvm_test(dut):
    cocotb.start_soon(Clock(dut.clk, 10, units="ns").start())
    dut.rst.value = 1
    for _ in range(3):
        await RisingEdge(dut.clk)
    dut.rst.value = 0
    await uvm_root().run_test("AluTest")
```

**~80 líneas. 6 clases. Estructura jerárquica.**

### Comparación: ¿qué ganamos? ¿qué perdemos?

| Aspecto                     | cocotb plano (A)         | pyUVM (B)                                  |
|-----------------------------|--------------------------|--------------------------------------------|
| Líneas de código            | ~20                      | ~80                                        |
| Curva de aprendizaje        | Baja                     | Media-alta                                 |
| Para 1 escenario            | Excelente                | Sobre-ingeniería                           |
| Para 50 escenarios          | Empieza a duplicar       | Una nueva sequence basta                   |
| Para 1000 escenarios        | Inviable                 | Diseñado para esto                         |
| Reutilización del driver    | Nula                     | El mismo driver sirve para cualquier test  |
| Separación productor/consumidor | Implícita (riesgo) | Explícita (TLM FIFO)                       |
| Trazabilidad de errores     | Print/log inline         | Componentes con `self.logger`              |
| Cobertura funcional         | Difícil de organizar     | Natural: añadir CoverPoints al monitor     |
| Migración a SystemVerilog   | Reescribir todo          | Casi 1-a-1 (mismos nombres de clase)       |
| Multi-test en un mismo file | Una función por test     | Múltiples `uvm_test`, elegir vía TESTCASE  |

### Cuándo usar cuál

- **cocotb plano**: prototipos rápidos, smoke tests, verificación
  específica de un bug. El Lab 1 es el ejemplo perfecto: un counter,
  un test, listo.
- **pyUVM**: testbench para un DUT que vas a verificar exhaustivamente,
  con múltiples sequences, múltiples tests, scoreboards estructurados,
  o cuando piensas migrar a SystemVerilog UVM en el futuro.

No es una elección absoluta. En proyectos reales conviven: hay
testbenches UVM "grandes" para cada bloque importante, y testbenches
cocotb planos para tests específicos o utilidades de bring-up.

## Parte 4 — Lecciones específicas de pyUVM 3.0.0

### `cocotb.top` vs ConfigDB para el handle del DUT

En SystemVerilog UVM, el DUT se inyecta vía "virtual interface" dentro
de ConfigDB. En pyUVM con cocotb, ese patrón es **innecesariamente
indirecto**: cocotb ya expone el handle global como `cocotb.top`.

**Patrón canónico en pyUVM**:

```python
class AluDriver(uvm_driver):
    def build_phase(self):
        self.dut = cocotb.top   # ← acceso directo
```

ConfigDB sigue siendo útil para **parámetros de configuración**
(`N_TRANSACTIONS`, `SEED`, modos de test, factor overrides, etc.).
Pero para el DUT, `cocotb.top` es más limpio.

### Asimetría set/get en ConfigDB

Atención, gotcha real de pyUVM 3.0.0:

```python
# Permitido:
ConfigDB().set(None, "*", "KEY", value)
ConfigDB().get(None, "", "KEY")

# ILEGAL:
ConfigDB().get(None, "*", "KEY")
# → UVMError: '*' is illegal: inst_name wildcards only allowed when storing.
```

El `set` admite wildcards en el inst_name. El `get` no. Esta asimetría
no aparece en SystemVerilog UVM, donde ambos lados admiten wildcards.
Si vienes de SV, te morderá.

**Regla práctica**: para parámetros compartidos por varios componentes:

```python
# En el wrapper:
ConfigDB().set(None, "*", "MY_PARAM", 42)

# En cualquier componente:
self.my_param = ConfigDB().get(None, "", "MY_PARAM")
```

### `done` es un pulso, no un nivel

El monitor del Lab 3 captura `done=1` en un único ciclo. Si tu monitor
se duerme un ciclo (por ejemplo, un `await Timer` mal calculado), se
pierde la transacción. Por eso el `run_phase` del monitor está en un
loop estricto: una iteración por flanco, sin pausas adicionales.

### `prev_result` en el scoreboard

El NOP del DUT mantiene `result`. Para que el scoreboard pueda predecir
qué debe ver en un NOP, debe llevar el estado: tras cada operación
exitosa, actualiza `self.prev_result = exp_result`. Sin esto, el primer
NOP que aparezca tras una operación real fallará el check.

## Referencias

- pyUVM oficial: <https://pyuvm.github.io/pyuvm/>
- cocotb triggers: <https://docs.cocotb.org/en/stable/triggers.html>
- UVM 1.2 reference (SystemVerilog, para comparar):
  <https://www.accellera.org/downloads/standards/uvm>
