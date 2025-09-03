module check_expression(
    input wire clk,
    input wire rst_n,
    input wire [7:0] expression_buffer,
    output reg expression_flag
);

    localparam [7:0] exp_surprized = 8'd4;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            expression_flag <= 1'b0;
        end
        else begin
            expression_flag <= (expression_buffer == exp_surprized);
        end
    end

endmodule
