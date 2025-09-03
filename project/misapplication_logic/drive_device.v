module drive_device (
    input wire clk,
    input wire rst_n,
    input wire pedal_flag,
    input wire expression_flag,
    input wire bpm_flag,
    input wire rr_flag,
    output wire pm,
    output reg drive
);

    parameter CLK_FREQ = 125_000_000;   // fpga board Hz
    parameter HIGH_SEC = 1;             // High
    parameter LOW_SEC = 2;              // Low

    // 상태 정의
    localparam S_IDLE = 2'b00;
    localparam S_HIGH = 2'b01;
    localparam S_LOW = 2'b10;

    // 카운트 값 (125MHz 기준)
    localparam HIGH_COUNT = CLK_FREQ * HIGH_SEC; // 1초
    localparam LOW_COUNT = CLK_FREQ * LOW_SEC;  // 2초

    reg [1:0] state;
    reg [31:0] counter; // 32비트로 충분

    assign pm = pedal_flag && (expression_flag || bpm_flag || rr_flag);

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            state <= S_IDLE;
            counter <= 32'd0;
            drive <= 1'b0;
        end else begin
            case (state)
                S_IDLE: begin
                    drive <= 1'b0;
                    if (pm) begin
                        state <= S_HIGH;
                        counter <= HIGH_COUNT - 1;
                        drive <= 1'b1;
                    end
                end

                S_HIGH: begin
                    drive <= 1'b1;
                    if (counter != 0) begin
                        counter <= counter - 1'b1;
                    end else begin
                        state <= S_LOW;
                        counter <= LOW_COUNT - 1;
                        drive <= 1'b0;
                    end
                end

                S_LOW: begin
                    drive <= 1'b0;
                    if (counter != 0) begin
                        counter <= counter - 1'b1;
                    end else begin
                        state <= S_IDLE;
                    end
                end

                default: begin
                    state <= S_IDLE;
                    counter <= 32'd0;
                    drive <= 1'b0;
                end
            endcase
        end
    end

endmodule
