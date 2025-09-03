module multi_clock_divider (
    input wire clk,
    input wire rst_n,
    output reg tick_1hz,
    output reg tick_10hz
);

    reg [26:0] cnt_1hz;
    reg [23:0] cnt_10hz;

    localparam MAX_1HZ   = 27'd124_999_999;  // 125M - 1
    localparam MAX_10HZ  = 24'd12_499_999;   // 12.5M - 1

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            cnt_1hz <= 0;
            cnt_10hz <= 0;
            tick_1hz <= 0;
            tick_10hz <= 0;
        end else begin
            // 1 Hz 분주기
            if (cnt_1hz == MAX_1HZ) begin
                cnt_1hz <= 0;
                tick_1hz <= 1;
            end else begin
                cnt_1hz <= cnt_1hz + 1;
                tick_1hz <= 0;
            end

            // 10 Hz 분주기
            if (cnt_10hz == MAX_10HZ) begin
                cnt_10hz <= 0;
                tick_10hz <= 1;
            end else begin
                cnt_10hz <= cnt_10hz + 1;
                tick_10hz <= 0;
            end
        end
    end
endmodule