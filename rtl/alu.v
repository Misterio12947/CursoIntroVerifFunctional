// ============================================================================
// ALU síncrona de 8 bits.
// ----------------------------------------------------------------------------
// - Reset síncrono activo en alto.
// - 7 operaciones implementadas + 1 reservada (NOP).
// - Handshake: start (entrada) -> done (salida, 1 ciclo después).
// - result, zero, carry registrados.
// - Combinacional registrada: 1 ciclo de latencia.
// ============================================================================

`timescale 1ns/1ps

module alu (
    input  wire       clk,
    input  wire       rst,
    input  wire [7:0] a,
    input  wire [7:0] b,
    input  wire [2:0] op,
    input  wire       start,
    output reg  [7:0] result,
    output reg        zero,
    output reg        carry,
    output reg        done
);

    // Códigos de operación.
    localparam OP_ADD = 3'b000;
    localparam OP_SUB = 3'b001;
    localparam OP_AND = 3'b010;
    localparam OP_OR  = 3'b011;
    localparam OP_XOR = 3'b100;
    localparam OP_SHL = 3'b101;
    localparam OP_SHR = 3'b110;
    localparam OP_NOP = 3'b111;

    // ---- Lógica combinacional: calcula resultado y carry para cada op ----
    reg  [7:0] result_next;
    reg        carry_next;

    // a + b en 9 bits para capturar carry.
    wire [8:0] add_full = {1'b0, a} + {1'b0, b};

    always @* begin
        // Defaults (válidos para NOP y operaciones lógicas sin carry).
        result_next = result;     // NOP: mantén valor anterior.
        carry_next  = 1'b0;

        case (op)
            OP_ADD: begin
                result_next = add_full[7:0];
                carry_next  = add_full[8];
            end
            OP_SUB: begin
                result_next = a - b;
                carry_next  = (b > a);   // borrow
            end
            OP_AND: begin
                result_next = a & b;
                carry_next  = 1'b0;
            end
            OP_OR: begin
                result_next = a | b;
                carry_next  = 1'b0;
            end
            OP_XOR: begin
                result_next = a ^ b;
                carry_next  = 1'b0;
            end
            OP_SHL: begin
                result_next = {a[6:0], 1'b0};
                carry_next  = a[7];      // bit desplazado fuera.
            end
            OP_SHR: begin
                result_next = {1'b0, a[7:1]};
                carry_next  = a[0];      // bit desplazado fuera.
            end
            OP_NOP: begin
                result_next = result;    // explícito para legibilidad.
                carry_next  = 1'b0;
            end
            default: begin
                result_next = result;
                carry_next  = 1'b0;
            end
        endcase
    end

    // ---- Lógica secuencial: registra resultado, flags y done ----
    always @(posedge clk) begin
        if (rst) begin
            result <= 8'd0;
            zero   <= 1'b1;
            carry  <= 1'b0;
            done   <= 1'b0;
        end else if (start) begin
            result <= result_next;
            zero   <= (result_next == 8'd0);
            carry  <= carry_next;
            done   <= 1'b1;
        end else begin
            done   <= 1'b0;     // pulso de 1 ciclo.
            // result, zero, carry: se mantienen.
        end
    end

endmodule
