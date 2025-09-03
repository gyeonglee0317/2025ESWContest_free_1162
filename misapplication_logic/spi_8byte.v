module spi_8byte (
    input wire clk,
    input wire rst_n,
    input wire sclk,
    input wire mosi,
    input wire ss,
    output wire miso,

    input wire pm,
    input wire [15:0] rate_inst,
    input wire [15:0] rate_avg,
    input wire [7:0] bpm_short_avg,
    input wire [7:0] bpm_long_avg,
    input wire [5:0] rr_short_avg,
    input wire [5:0] rr_long_avg,
    input wire pedal_flag,
    input wire expression_flag,
    input wire bpm_flag,
    input wire rr_flag,
    
    // Received 64-bit from MOSI
    output reg [63:0] rx_data
);

    // Synchronizers
    reg [1:0] sclk_sync, ss_sync, mosi_sync, pm_sync;
    always @(posedge clk) begin
        sclk_sync <= {sclk_sync[0], sclk};
        ss_sync <= {ss_sync[0], ss};
        mosi_sync <= {mosi_sync[0], mosi};
        pm_sync <= {pm_sync[0], pm};
    end

    wire sclk_rising = (sclk_sync == 2'b01);
    wire sclk_falling = (sclk_sync == 2'b10);
    wire ss_active = ~ss_sync[1];

    // Shift/Counters
    reg [5:0] bit_cnt;        // 0..63
    reg [63:0] rx_buffer;
    reg [63:0] tx_buffer;
    reg miso_reg;

    assign miso = miso_reg;

    // 프레임 패킹 (MSB-first)
    wire [63:0] tx_pack = {
        rate_inst,                              // [63:48] 가속 페달 변화량 (rate_inst) 
        rate_avg,                               // [47:32] 평군 가속 페달 작동량 (rate_avg) 
        bpm_long_avg,                           // [31:24] 심박수_long_avg (bpm_short_avg) 
        bpm_short_avg,                          // [23:16] 심박수_short_avg (bpm_long_avg) 
        rr_long_avg [5:0],                      // [15:10] 호흡수_long_avg (rr_short_avg) 
        rr_short_avg[5:0],                      // [9:4] 호흡수_short_avg (rr_long_avg)
        pedal_flag,                             // pedal_flag
        (expression_flag | bpm_flag | rr_flag),  // expression_flag || bpm_flag || rr_flag
        1'b0, pm_sync[1]                        // [1:0] = 페달 오조작 여부 ({1'b0, pm})
    };

    // 임시 조합 변수 (동일 사이클에서 올바른 비트를 내보내기 위함)
    reg [63:0] tx_next;            // blocking 사용

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            bit_cnt  <= 6'd0;
            rx_buffer <= 64'd0;
            tx_buffer <= 64'd0;
            rx_data <= 64'd0;
            miso_reg <= 1'b0;
        end else begin
            if (!ss_active) begin
                bit_cnt <= 6'd0;
                miso_reg <= 1'b0;
            end else begin
                // MOSI: Mode-1, falling edge에서 sample
                if (sclk_falling) begin
                    rx_buffer <= {rx_buffer[62:0], mosi_sync[1]};
                    bit_cnt <= bit_cnt + 6'd1;

                    if (bit_cnt == 6'd63) begin
                        rx_data <= {rx_buffer[62:0], mosi_sync[1]};
                    end
                end

                // MISO: Mode-1, rising edge에서 data 준비
                if (sclk_rising) begin
                    // 같은 사이클에서 사용할 소스 선택 (blocking '=')
                    if (bit_cnt == 6'd0) begin
                        tx_next = tx_pack;          // 새 프레임 시작: 최신 페이로드
                    end else begin
                        tx_next = tx_buffer;        // 진행 중: 기존 시프트 레지스터
                    end
                    
                    miso_reg  <= tx_next[63];           // 이번 rising에서 내보낼 비트 = tx_next[63]
                    tx_buffer <= {tx_next[62:0], 1'b0}; // 다음 사이클을 위한 시프트
                end
            end
        end
    end

endmodule