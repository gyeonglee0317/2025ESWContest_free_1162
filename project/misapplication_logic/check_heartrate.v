module check_bpm (
    input wire clk,
    input wire rst_n,
    input wire tick_10hz,
    input wire [7:0] bpm_buffer,
    output reg bpm_flag,
    output reg [7:0] short_avg,
    output reg [7:0] long_avg
);

    localparam integer SHORT_SAMPLES = 8;   // 0.8s, 10Hz
    localparam integer LONG_SAMPLES = 64;   // 6.4s, 10Hz
    localparam integer SUMS_WIDTH_S = 11;   // 8+3=11, 256*8 = 2048, 11bit 필요
    localparam integer SUMS_WIDTH_L = 14;   // 8+6=14, 256*64, 14bit 필요

    // registor (Short/Long)
    reg [7:0] fir_short [0:SHORT_SAMPLES-1];
    reg [7:0] fir_long [0:LONG_SAMPLES-1];

    // 누적합 및 카운터 index
    reg [SUMS_WIDTH_S-1:0] sum_short;
    reg [SUMS_WIDTH_L-1:0] sum_long;
    reg [3:0] filled_short; // 0~8
    reg [6:0] filled_long;  // 0~64

    // 조합 임시 (이번 사이클의 새 샘플 반영한 합)
    reg [7:0] prev_tail_s, prev_tail_l;     // registor에서 가장 오래된 값
    reg [SUMS_WIDTH_S-1:0] sum_short_next;
    reg [SUMS_WIDTH_L-1:0] sum_long_next;

    // 비교 항: 32*sum_short_next vs 5*sum_long_next >> Notion 정리 참고
    // 비트폭 여유 확보
    reg [SUMS_WIDTH_S+5-1:0] lhs;  // <<5
    reg [SUMS_WIDTH_L+3-1:0] rhs;  // *5

    integer i;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            bpm_flag <= 1'b0;
            sum_short <= {SUMS_WIDTH_S{1'b0}};
            sum_long <= {SUMS_WIDTH_L{1'b0}};
            filled_short <= 4'd0;
            filled_long <= 7'd0;
            short_avg <= 8'd0;
            long_avg <= 8'd0;
            for (i=0; i<SHORT_SAMPLES; i=i+1) fir_short[i] <= 8'd0;
            for (i=0; i<LONG_SAMPLES; i=i+1) fir_long[i]  <= 8'd0;
            prev_tail_s <= 8'd0;
            prev_tail_l <= 8'd0;
            sum_short_next <= {SUMS_WIDTH_S{1'b0}};
            sum_long_next <= {SUMS_WIDTH_L{1'b0}}; 
        end
        else if (tick_10hz) begin
            // 1) 이번 샘플(hr_bpm) 반영한 '다음 합' 계산 (조합)
            prev_tail_s = fir_short [SHORT_SAMPLES-1];
            prev_tail_l = fir_long [LONG_SAMPLES-1];

            // 새 합 = 이전 합 - 가장 오래된 값 + 새로운 값
            sum_short_next = sum_short - {{(SUMS_WIDTH_S-8){1'b0}}, prev_tail_s} + {{(SUMS_WIDTH_S-8){1'b0}}, bpm_buffer};
            sum_long_next  = sum_long - {{(SUMS_WIDTH_L-8){1'b0}}, prev_tail_l} + {{(SUMS_WIDTH_L-8){1'b0}}, bpm_buffer};

            // 2) 이중 평균 비교 (나눗셈 없이, Notion 정리 참고)
            lhs = {5'd0, sum_short_next} << 5;
            rhs = (sum_long_next * 5);

            if ( (filled_short == SHORT_SAMPLES[3:0]) && (filled_long == LONG_SAMPLES[6:0]) )
                bpm_flag <= (lhs >= rhs);
            else
                bpm_flag <= 1'b0;

            // 3) 시프트 레지스터 갱신
            for (i=SHORT_SAMPLES-1; i>0; i=i-1) begin
                fir_short[i] <= fir_short[i-1];
            end
            fir_short[0] <= bpm_buffer;

            for (i=LONG_SAMPLES-1; i>0; i=i-1) begin
                fir_long[i] <= fir_long[i-1];
            end
            fir_long[0] <= bpm_buffer;

            // 4) 누적합/평균/카운터 갱신
            sum_short <= sum_short_next;
            sum_long  <= sum_long_next;

            short_avg <= sum_short_next >> 3;  // /8
            long_avg  <= sum_long_next  >> 6;  // /64

            // 가장 처음에 값이 들어올 때, sample이 다 채워졌는지 확인
            if (filled_short < SHORT_SAMPLES[3:0]) filled_short <= filled_short + 4'd1;
            if (filled_long  < LONG_SAMPLES[6:0]) filled_long  <= filled_long  + 7'd1;
        end
    end

endmodule
