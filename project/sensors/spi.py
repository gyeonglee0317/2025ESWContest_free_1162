import spidev

BUS, DEV = 0, 0
MODE, SPEED, BITS = 1, 11_000_000, 8  # CPOL=0, CPHA=1

def open_spi():
    spi = spidev.SpiDev()
    spi.open(BUS, DEV)
    spi.mode = MODE
    spi.max_speed_hz = SPEED
    spi.bits_per_word = BITS
    spi.cshigh = False
    return spi

def pack_tx_frame(pedal: int, expression: int, bpm: int, rr: int) -> list:
    pedal, expression, bpm, rr = pedal & 0xFF, expression & 0xFF, bpm & 0xFF, rr & 0xFF
    w = 0
    w |= (pedal & 0xFF) << 24
    w |= (expression & 0xFF) << 16
    w |= (bpm & 0xFF) << 8
    w |= (rr & 0xFF)
    return [(w >> s) & 0xFF for s in (56,48,40,32,24,16,8,0)]

def unpack_rx_frame(rx_bytes: list) -> dict:
    if len(rx_bytes) != 8: raise ValueError("rx_bytes must be length 8")
    w = 0
    for b in rx_bytes: w = ((w << 8) | (b & 0xFF)) & 0xFFFFFFFFFFFFFFFF
    return {
        "rate_inst":     (w >> 48) & 0xFFFF,
        "rate_avg":      (w >> 32) & 0xFFFF,
        "bpm_long_avg":  (w >> 24) & 0xFF,
        "bpm_short_avg": (w >> 16) & 0xFF,
        "rr_long_avg":   (w >> 10) & 0x3F,
        "rr_short_avg":  (w >>  4) & 0x3F,
        "pedal_flag":    (w >> 3) & 0x1,
        "cond_flags":    (w >> 2) & 0x1,
        "pm":            w & 0x1,
        "raw64_hex":     f"0x{w:016X}"
    }

def xfer_once(spi, pedal: int, expression: int, bpm: int, rr: int) -> dict:
    tx = pack_tx_frame(pedal, expression, bpm, rr)
    rx = spi.xfer2(tx)
    return unpack_rx_frame(rx)
