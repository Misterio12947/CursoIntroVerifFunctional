// ============================================================================
// FIFO síncrona parametrizable.
// ----------------------------------------------------------------------------
// - Reset síncrono activo en alto.
// - Push y pop simultáneos permitidos (la ocupación no cambia).
// - Push con full=1: se ignora (no se acepta el dato).
// - Pop con empty=1: se ignora (pop_data no se actualiza, estado intacto).
// - pop_data es combinacional: el dato sale en el mismo ciclo que pop_valid.
// ============================================================================

`timescale 1ns/1ps

module fifo #(
    parameter DEPTH = 8,           // capacidad del FIFO
    parameter WIDTH = 8            // ancho de cada palabra
) (
    input  wire             clk,
    input  wire             rst,
    // Interfaz de escritura.
    input  wire             push_valid,
    input  wire [WIDTH-1:0] push_data,
    // Interfaz de lectura.
    input  wire             pop_valid,
    output wire [WIDTH-1:0] pop_data,
    // Flags.
    output wire             full,
    output wire             empty
);

    // ---- Constantes derivadas ----
    localparam PTR_W = $clog2(DEPTH);
    localparam CNT_W = $clog2(DEPTH + 1);   // necesita representar DEPTH

    // ---- Estado interno ----
    reg [WIDTH-1:0] mem [0:DEPTH-1];
    reg [PTR_W-1:0] wr_ptr;
    reg [PTR_W-1:0] rd_ptr;
    reg [CNT_W-1:0] count;

    // ---- Salidas combinacionales ----
    assign pop_data = mem[rd_ptr];
    assign full     = (count == DEPTH);
    assign empty    = (count == 0);

    // ---- Habilitaciones efectivas ----
    wire do_push = push_valid && !full;
    wire do_pop  = pop_valid  && !empty;

    // ---- Lógica secuencial ----
    integer i;
    always @(posedge clk) begin
        if (rst) begin
            wr_ptr <= 0;
            rd_ptr <= 0;
            count  <= 0;
            for (i = 0; i < DEPTH; i = i + 1)
                mem[i] <= {WIDTH{1'b0}};
        end else begin
            // Escritura.
            if (do_push) begin
                mem[wr_ptr] <= push_data;
                wr_ptr      <= (wr_ptr == DEPTH-1) ? 0 : wr_ptr + 1;
            end
            // Lectura.
            if (do_pop) begin
                rd_ptr <= (rd_ptr == DEPTH-1) ? 0 : rd_ptr + 1;
            end
            // Contador de ocupación.
            case ({do_push, do_pop})
                2'b10: count <= count + 1;     // solo push
                2'b01: count <= count - 1;     // solo pop
                2'b11: count <= count;         // push+pop simultáneos
                default: count <= count;       // ni push ni pop
            endcase
        end
    end

endmodule
