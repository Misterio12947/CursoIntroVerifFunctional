// ============================================================================
// FPU IEEE 754 single-precision: suma flotante de 32 bits.
// ----------------------------------------------------------------------------
// - 1 etapa de pipeline (resultado y done registrados, 1 ciclo de latencia).
// - Reset síncrono activo en alto.
// - Handshake start (entrada) -> done (salida, pulso de 1 ciclo después).
// - Política de redondeo: truncate (NO round-to-nearest-even).
//   Esto genera discrepancias de hasta ±1 ULP frente a numpy.float32.
//   El scoreboard del testbench compara con tolerancia ±1 ULP.
//
// LIMITACIONES (documentadas en fpu_uvm_reference.md):
//   - No maneja NaN. Si a o b son NaN, comportamiento indefinido.
//   - No maneja Infinity correctamente. Aproximación.
//   - Denormales: tratados como cero (flush to zero).
//   - No detecta overflow/underflow del exponente.
//
// Diseño pedagógico: el RTL prioriza legibilidad sobre eficiencia.
// ============================================================================

`timescale 1ns/1ps

module fpu (
    input  wire        clk,
    input  wire        rst,
    input  wire [31:0] a,
    input  wire [31:0] b,
    input  wire        start,
    output reg  [31:0] result,
    output reg         done
);

    // ------------------------------------------------------------------------
    // Combinacional: cálculo del resultado para el siguiente flanco.
    // ------------------------------------------------------------------------

    // Desempaquetar a y b.
    wire        sign_a       = a[31];
    wire [7:0]  exp_a        = a[30:23];
    wire [23:0] mantissa_a   = {1'b1, a[22:0]};   // bit implícito

    wire        sign_b       = b[31];
    wire [7:0]  exp_b        = b[30:23];
    wire [23:0] mantissa_b   = {1'b1, b[22:0]};

    // Alineación: identificar el mayor exponente y shift del menor.
    reg         op_sign_big, op_sign_small;
    reg  [23:0] op_mant_big;
    reg  [23:0] op_mant_small_aligned;
    reg  [7:0]  final_exp;

    always @* begin
        if (exp_a >= exp_b) begin
            op_sign_big           = sign_a;
            op_sign_small         = sign_b;
            op_mant_big           = mantissa_a;
            op_mant_small_aligned = mantissa_b >> (exp_a - exp_b);
            final_exp             = exp_a;
        end else begin
            op_sign_big           = sign_b;
            op_sign_small         = sign_a;
            op_mant_big           = mantissa_b;
            op_mant_small_aligned = mantissa_a >> (exp_b - exp_a);
            final_exp             = exp_b;
        end
    end

    // Sumar o restar según signos.
    // sum_mant es 25 bits para capturar carry potencial.
    reg  [24:0] sum_mant;
    reg         result_sign;

    always @* begin
        if (op_sign_big == op_sign_small) begin
            sum_mant    = {1'b0, op_mant_big} + {1'b0, op_mant_small_aligned};
            result_sign = op_sign_big;
        end else begin
            if (op_mant_big >= op_mant_small_aligned) begin
                sum_mant    = {1'b0, op_mant_big} - {1'b0, op_mant_small_aligned};
                result_sign = op_sign_big;
            end else begin
                sum_mant    = {1'b0, op_mant_small_aligned} - {1'b0, op_mant_big};
                result_sign = op_sign_small;
            end
        end
    end

    // Normalizar: si hay carry (bit 24), shift derecha y exp+1.
    // Si bit 23 es 0, shift izquierda iterativo (hasta 24 iteraciones,
    // suficiente para single precision).
    reg  [24:0] norm_mant;
    reg  [7:0]  norm_exp;
    integer     i;

    always @* begin
        norm_mant = sum_mant;
        norm_exp  = final_exp;

        if (norm_mant[24]) begin
            // Carry: shift derecha 1, exp+1.
            norm_mant = norm_mant >> 1;
            norm_exp  = norm_exp + 1;
        end else begin
            // Normalizar izquierda mientras bit 23 sea 0 y exp > 0.
            for (i = 0; i < 24; i = i + 1) begin
                if (norm_mant[23] == 1'b0 && norm_exp > 0) begin
                    norm_mant = norm_mant << 1;
                    norm_exp  = norm_exp - 1;
                end
            end
        end
    end

    // Resultado combinacional empaquetado.
    // Si sum_mant es 0, resultado es cero positivo (puro).
    wire [31:0] result_next = (sum_mant == 25'b0)
        ? 32'b0
        : {result_sign, norm_exp, norm_mant[22:0]};

    // ------------------------------------------------------------------------
    // Secuencial: registra result y done.
    // ------------------------------------------------------------------------
    always @(posedge clk) begin
        if (rst) begin
            result <= 32'd0;
            done   <= 1'b0;
        end else if (start) begin
            result <= result_next;
            done   <= 1'b1;
        end else begin
            done   <= 1'b0;
            // result se mantiene hasta el siguiente start.
        end
    end

endmodule
