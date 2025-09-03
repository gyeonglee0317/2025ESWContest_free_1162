module PMPD(
    input wire clk,
    input wire rst_n,
    input wire sclk,
    input wire mosi,
    input wire ss,
    output wire miso,           // miso는 페달 오조작 여부를 반환해야함
    output wire drive
);

    // SPI_slave                >> spi로 받은 값들을 바로 64bit buffer로 보내야함
    // [63:32] = 0
    // [31:24] 페달 작동량
    // [23:16] 표정
    // [15:8] 호흡수
    // [7:0] 심박수
    wire [63:0] state_buffer;
    wire pm;
   
    wire [15:0] rate_inst;
    wire [15:0] rate_avg;
    wire [7:0] bpm_short_avg;
    wire [7:0] bpm_long_avg;
    wire [5:0] rr_short_avg;
    wire [5:0] rr_long_avg;
   
    wire pedal_flag;
    wire expression_flag;
    wire bpm_flag;
    wire rr_flag;
  
    spi_8byte spi (
        .clk(clk),
        .rst_n(rst_n),
        .sclk(sclk),
        .mosi(mosi),
        .ss(ss), 
        .miso(miso), 
        .pm(pm),
        .rate_inst(rate_inst),
        .rate_avg(rate_avg),
        .bpm_short_avg(bpm_short_avg),
        .bpm_long_avg(bpm_long_avg),
        .rr_short_avg(rr_short_avg),
        .rr_long_avg(rr_long_avg),
        .pedal_flag(pedal_flag),
        .expression_flag(expression_flag),
        .bpm_flag(bpm_flag),
        .rr_flag(rr_flag),
        .rx_data(state_buffer)
    );

    // 분주기 (10Hz, 1Hz)
    wire tick_1hz;
    wire tick_10hz;
    
    multi_clock_divider prescaler(
        .clk(clk),
        .rst_n(rst_n),
        .tick_1hz(tick_1hz),
        .tick_10hz(tick_10hz)
    );
    
    // 페달 변화량 감지
    check_pedal check_pedal(
        .clk(clk),
        .rst_n(rst_n),
        .tick_10hz(tick_10hz),
        .pedal_buffer(state_buffer[31:24]),
        .pedal_flag(pedal_flag),
        .rate_inst(rate_inst),
        .rate_avg(rate_avg)
    );

    // 표정 감지
    check_expression check_expression(
        .clk(clk),
        .rst_n(rst_n),
        .expression_buffer(state_buffer[23:16]),
        .expression_flag(expression_flag)        
    );
    
    // 심박수 감지
    check_bpm check_bpm(
        .clk(clk),
        .rst_n(rst_n),
        .tick_10hz(tick_10hz),
        .bpm_buffer(state_buffer[15:8]),
        .bpm_flag(bpm_flag),
        .short_avg(bpm_short_avg),
        .long_avg(bpm_long_avg)
    );
    
    // 호흡수 감지   
    check_respiration check_respiration(
        .clk(clk),
        .rst_n(rst_n),
        .tick_1hz(tick_1hz),
        .rr_buffer(state_buffer[7:0]),
        .rr_flag(rr_flag),
        .short_avg(rr_short_avg),
        .long_avg(rr_long_avg)
    );

    // flag 만족 시 PMPD 동작
    drive_device drive_device(
        .clk(clk),
        .rst_n(rst_n),
        .pedal_flag(pedal_flag),
        .expression_flag(expression_flag),
        .bpm_flag(bpm_flag),
        .rr_flag(rr_flag),
        .pm(pm),
        .drive(drive)
    );

endmodule