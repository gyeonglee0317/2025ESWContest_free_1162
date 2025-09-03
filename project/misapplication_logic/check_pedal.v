module check_pedal (
    input wire clk,
    input wire rst_n,
    input wire tick_10hz,
    input wire [7:0] pedal_buffer,
    output reg pedal_flag,
    output reg [15:0] rate_inst,
    output reg [15:0] rate_avg
);

    // 임계값 (%/s)
    localparam [15:0] THRESH_LOW = 16'd25;    // 즉시 ≥ 25
    localparam [15:0] THRESH_HIGH = 16'd75;   // 평균 ≥ 75
    localparam [15:0] THRESH_PEAK = 16'd99;   // 즉시 ≥ 99

    // 내부 상태
    reg [7:0] pedal_curr;
    reg [7:0] pedal_prev;

    // 즉시 변화율(%/s)
    //reg [15:0] rate_inst;
    reg [15:0] rate_next;       // 이번 tick에 계산된 즉시율

    // FIR(이동평균) 8탭: 각 탭은 0..100(%/s)
    reg [15:0] fir_reg [0:7];   // 탭 레지스터
    reg [13:0] fir_sum;         // 합(최대 8*1000=8000 < 2^14)
    reg [13:0] fir_sum_next;    // 이번 tick에 적용될 다음 합
    //reg [15:0] rate_avg;        // 평균(%/s) = fir_sum >> 3

    // 윈도 채움 여부
    reg [3:0] filled;           // 0..8

    // 조합 임시
    reg signed [9:0] diff_sample;   // -255..+255
    reg [9:0] delta_pos;            // +변화만(0..255)

    integer i;

    // 동기 로직
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            pedal_flag <= 1'b0;
            pedal_curr <= 8'd0;
            pedal_prev <= 8'd0;
            rate_inst <= 16'd0;
            rate_next <= 16'd0;
            rate_avg <= 16'd0;
            for (i=0; i<8; i=i+1) fir_reg[i] <= 16'd0;
            fir_sum <= 14'd0;
            fir_sum_next <= 14'd0;
            filled <= 4'd0;
        end
        else if (tick_10hz) begin
            // 1) 새 샘플 기준 조합 계산 (blocking)
            // 이전 pedal_curr를 기준으로 delta 계산 → 그 다음에 샘플 업데이트
            diff_sample = $signed({1'b0, pedal_buffer}) - $signed({1'b0, pedal_curr});
            delta_pos = (diff_sample > 0) ? diff_sample[9:0] : 10'd0;  // +변화만
            rate_next = delta_pos * 16'd10;                            // %/s

            // 2) 롤링합(새 샘플을 같은 tick에 반영)
            //    주의: 아직 fir_reg[]는 이전 값들이므로 fir_reg[7]는 '이전 tail'
            fir_sum_next = fir_sum - fir_reg[7] + rate_next;

            // 3) FIR 시프트 + 주입 (nonblocking)
            for (i=7; i>0; i=i-1) begin
                fir_reg[i] <= fir_reg[i-1];
            end
            fir_reg[0] <= rate_next;

            // 4) 레지스터 갱신 (nonblocking)
            rate_inst <= rate_next;
            fir_sum <= fir_sum_next;
            rate_avg <= {2'b00, fir_sum_next} >> 3;  // (= fir_sum_next/8)

            // 5) 판정 (이번 tick의 rate_next와 평균(rate_avg_next) 기반)
            if (filled == 4'd8) begin
                if ( ((rate_next >= THRESH_LOW) && ( (fir_sum_next >> 3) >= THRESH_HIGH )) || (rate_next >= THRESH_PEAK) )
                    pedal_flag <= 1'b1;
                else
                    pedal_flag <= 1'b0;
            end
            else begin
                pedal_flag <= 1'b0;
            end

            // 6) 샘플/채움 카운터 갱신 (마지막에)
            pedal_prev <= pedal_curr;
            pedal_curr <= pedal_buffer;

            if (filled < 4'd8) filled <= filled + 4'd1;
        end
    end

endmodule
