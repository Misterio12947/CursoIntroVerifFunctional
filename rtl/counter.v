// Contador síncrono de 8 bits.
// - reset síncrono activo en alto
// - habilitación por nivel (en)
// - wrap-around natural de 255 a 0 (no se gestiona overflow)

`timescale 1ns/1ps

module counter (
    input  wire       clk,
    input  wire       rst,
    input  wire       en,
    output reg  [7:0] count
);

    always @(posedge clk) begin
        if (rst)
            count <= 8'd0;
        else if (en)
            count <= count + 8'd1;
    end

endmodule
