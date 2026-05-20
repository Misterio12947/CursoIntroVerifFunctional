// ============================================================================
// FPU buggy — variante de rtl/fpu.v con un bug deliberado.
// ----------------------------------------------------------------------------
// USO PEDAGÓGICO: este archivo se utiliza como ejercicio de bug-hunting en
// labs/lab4_fpu_uvm/. El alumno ejecuta su testbench contra este RTL y debe:
//   1. Observar el patrón de fallos en el log del scoreboard.
//   2. Inferir qué operación está fallando (qué entradas reproducen el bug).
//   3. Localizar la línea ofensiva en este archivo.
//   4. Describir el bug en su propio README.
//
// NO se incluye en el CI. El job lab4-fpu-uvm usa fpu.v (correcto).
//
// AVISO PARA EL INSTRUCTOR: el bug está claramente marcado con un
// comentario "BUG B:" en la línea afectada. Los estudiantes deben
// descubrirlo por el comportamiento del testbench, no leyendo este header.
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

    // Desempaquetar.
    wire        sign_a       = a[31];
    wire [7:0]  exp_a        = a[30:23];
    wire [23:0] mantissa_a   = {1'b1, a[22:0]};

    wire        sign_b       = b[31];
    wire [7:0]  exp_b        = b[30:23];
    wire [23:0] mantissa_b   = {1'b1, b[22:0]};

    // Alineación.
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
    reg  [24:0] sum_mant;
    reg         result_sign;

    always @* begin
        if (op_sign_big == op_sign_small) begin
            sum_mant    = {1'b0, op_mant_big} + {1'b0, op_mant_small_aligned};
            result_sign = op_sign_big;
        end else begin
            if (op_mant_big >= op_mant_small_aligned) begin
                sum_mant    = {1'b0, op_mant_big} + {1'b0, op_mant_small_aligned};  // BUG B: should be -
                result_sign = op_sign_big;
            end else begin
                sum_mant    = {1'b0, op_mant_small_aligned} - {1'b0, op_mant_big};
                result_sign = op_sign_small;
            end
        end
    end

    // Normalizar.
    reg  [24:0] norm_mant;
    reg  [7:0]  norm_exp;
    integer     i;

    always @* begin
        norm_mant = sum_mant;
        norm_exp  = final_exp;

        if (norm_mant[24]) begin
            norm_mant = norm_mant >> 1;
            norm_exp  = norm_exp + 1;
        end else begin
            for (i = 0; i < 24; i = i + 1) begin
                if (norm_mant[23] == 1'b0 && norm_exp > 0) begin
                    norm_mant = norm_mant << 1;
                    norm_exp  = norm_exp - 1;
                end
            end
        end
    end

    wire [31:0] result_next = (sum_mant == 25'b0)
        ? 32'b0
        : {result_sign, norm_exp, norm_mant[22:0]};

    // Secuencial.
    always @(posedge clk) begin
        if (rst) begin
            result <= 32'd0;
            done   <= 1'b0;
        end else if (start) begin
            result <= result_next;
            done   <= 1'b1;
        end else begin
            done   <= 1'b0;
        end
    end

endmodule
