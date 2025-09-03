module check_respiration(
    input wire clk,
    input wire rst_n,
    input wire tick_1hz,
    input wire [7:0]  rr_buffer,
    output reg rr_flag,
    output reg [5:0] short_avg,
    output reg [5:0] long_avg
);

    localparam integer SHORT_SAMPLES = 16;      // 16s ,1Hz
    localparam integer LONG_SAMPLES = 120;      // 120s ,1Hz
    localparam integer SUMS_WIDTH_S = 12;       // 256*16=4096, 12bit
    localparam integer SUMS_WIDTH_L = 15;       // 256*120=30720, 15bit
    localparam integer CMP_WIDTH = 32;          // 비교항 여유비트

    // shift registers
    reg [7:0] fir_short [0:SHORT_SAMPLES-1];
    reg [7:0] fir_long [0:LONG_SAMPLES -1];

    // sums & counters
    reg [SUMS_WIDTH_S-1:0] sum_short, sum_short_next;
    reg [SUMS_WIDTH_L-1:0] sum_long , sum_long_next;
    reg [4:0] filled_short; // 0..16
    reg [6:0] filled_long;  // 0..120

    // 조합 임시(이번 tick의 다음 합)
    reg [7:0] prev_tail_s, prev_tail_l;

    // compare terms: 2400*sum_short_next >= 368*sum_long_next
    reg [CMP_WIDTH-1:0] lhs, rhs;

    // 내부 평균(8비트) → 출력(6비트) 포화 변환
    reg [7:0] short_avg8;
    reg [7:0] long_avg8;

    integer i;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            rr_flag <= 1'b0;
            sum_short <= {SUMS_WIDTH_S{1'b0}};
            sum_long <= {SUMS_WIDTH_L{1'b0}};
            sum_short_next <= {SUMS_WIDTH_S{1'b0}};
            sum_long_next <= {SUMS_WIDTH_L{1'b0}};
            filled_short <= 5'd0;
            filled_long <= 7'd0;
            short_avg <= 6'd0;
            long_avg <= 6'd0;
            short_avg8 <= 8'd0;
            long_avg8 <= 8'd0;
            for (i=0; i<SHORT_SAMPLES; i=i+1) fir_short[i] <= 8'd0;
            for (i=0; i<LONG_SAMPLES;  i=i+1) fir_long[i] <= 8'd0;
            prev_tail_s <= 8'd0;
            prev_tail_l <= 8'd0;
        end
        else if (tick_1hz) begin
            // 1) 다음 합 계산
            prev_tail_s = fir_short[SHORT_SAMPLES-1];
            prev_tail_l = fir_long [LONG_SAMPLES -1];

            // 새 합 = 이전 합 - 가장 오래된 값 + 새로운 값
            sum_short_next = sum_short - {{(SUMS_WIDTH_S-8){1'b0}}, prev_tail_s} + {{(SUMS_WIDTH_S-8){1'b0}}, rr_buffer};
            sum_long_next  = sum_long- {{(SUMS_WIDTH_L-8){1'b0}}, prev_tail_l} + {{(SUMS_WIDTH_L-8){1'b0}}, rr_buffer};

            // 2) 이중 평균 비교 (나눗셈 없이, Notion 정리 참고)
            lhs = {{(CMP_WIDTH-SUMS_WIDTH_S){1'b0}}, sum_short_next} * 32'd2400;
            rhs = {{(CMP_WIDTH-SUMS_WIDTH_L){1'b0}}, sum_long_next } * 32'd368;

            if ( (filled_short == SHORT_SAMPLES[4:0]) && (filled_long == LONG_SAMPLES[6:0]) )
                rr_flag <= (lhs >= rhs);
            else
                rr_flag <= 1'b0;

            // 3) 시프트 레지스터 갱신
            for (i=SHORT_SAMPLES-1; i>0; i=i-1) begin
                fir_short[i] <= fir_short[i-1];
            end
            fir_short[0] <= rr_buffer;

            for (i=LONG_SAMPLES-1; i>0; i=i-1) begin
                fir_long[i] <= fir_long[i-1];
            end
            fir_long[0] <= rr_buffer;

            // 4) 합/평균/카운터 갱신
            sum_short <= sum_short_next;
            sum_long <= sum_long_next;

            // 8비트 평균 계산
            short_avg8 <= sum_short_next >> 4;       // /16
            long_avg8 <= sum_long_next  / 8'd120;   // /120

            // 6비트 포화 출력
            if (short_avg8 > 8'd63) 
                short_avg <= 6'd63;
            else
                short_avg <= short_avg8[5:0];

            if (long_avg8  > 8'd63)
                long_avg  <= 6'd63;
            else 
                long_avg  <= long_avg8[5:0];

            // 가장 처음에 값이 들어올 때, sample이 다 채워졌는지 확인
            if (filled_short < SHORT_SAMPLES[4:0]) filled_short <= filled_short + 5'd1;
            if (filled_long  < LONG_SAMPLES[6:0])  filled_long  <= filled_long  + 7'd1;
        end
    end

endmodule
