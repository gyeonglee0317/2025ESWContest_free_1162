import time, struct, threading, serial

SERIAL_PORT = '/dev/ttyTHS1'
BAUD_RATE   = 115200
SOF_BYTE    = 0x01
FRAME_HEADER_SIZE = 8
TYPE_HEART_RATE   = 0x0A15
TYPE_BREATH_RATE  = 0x0A14

class MmWaveSensor:
    """mmWave 센서 데이터 수신/분석"""
    def __init__(self, port=SERIAL_PORT, baudrate=BAUD_RATE, debug=False):
        self.port, self.baudrate, self.debug = port, baudrate, debug
        self.ser = None
        self.connected = False
        self.has_data  = False
        self.last_update = 0.0
        self._latest_data = {"heart_rate": None, "breath_rate": None}
        self._frame_buffer = bytearray()
        self._is_frame_started = False
        self._is_running = False
        self._thread = None

    def _cksum(self, data):
        s = 0
        for b in data: s ^= b
        return (~s) & 0xFF

    def _parse_payload(self, data_type, payload):
        try:
            if data_type == TYPE_HEART_RATE:
                self._latest_data["heart_rate"] = struct.unpack('<f', payload)[0]
            elif data_type == TYPE_BREATH_RATE:
                self._latest_data["breath_rate"] = struct.unpack('<f', payload)[0]
            self.has_data = True
            self.last_update = time.time()
        except Exception as e:
            if self.debug: print("payload parse error:", e)

    def _process_frame(self):
        hdr = self._frame_buffer[:FRAME_HEADER_SIZE]
        if self._cksum(hdr[:FRAME_HEADER_SIZE-1]) != hdr[7]: return
        payload = self._frame_buffer[FRAME_HEADER_SIZE:-1]
        if self._cksum(payload) != self._frame_buffer[-1]: return
        dtype = (hdr[5] << 8) | hdr[6]
        self._parse_payload(dtype, payload)

    def _read_loop(self):
        while self._is_running:
            try:
                b = self.ser.read(1)
                if not b:
                    if self.has_data and (time.time() - self.last_update > 2.0):
                        self.has_data = False
                    continue
                b = b[0]
                if not self._is_frame_started and b == SOF_BYTE:
                    self._is_frame_started = True
                    self._frame_buffer.clear()
                    self._frame_buffer.append(b)
                elif self._is_frame_started:
                    self._frame_buffer.append(b)
                    if len(self._frame_buffer) >= FRAME_HEADER_SIZE:
                        data_len = (self._frame_buffer[3] << 8) | self._frame_buffer[4]
                        if data_len > 200:
                            self._is_frame_started = False; continue
                        total_len = FRAME_HEADER_SIZE + data_len + 1
                        if len(self._frame_buffer) >= total_len:
                            self._process_frame()
                            self._is_frame_started = False
            except Exception as e:
                print("[mmWave] read error:", e); time.sleep(0.1)

    def start(self):
        if self._is_running: return
        try:
            self.ser = serial.Serial(self.port, self.baudrate, timeout=1)
            self.connected = True
        except serial.SerialException as e:
            print(f"[mmWave] open fail: {e}")
            self.connected = False
            return
        self._is_running = True
        self._thread = threading.Thread(target=self._read_loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._is_running = False
        if self._thread: self._thread.join(timeout=1.0)
        if self.ser and self.ser.is_open: self.ser.close()
        self.connected = False; self.has_data = False; self.last_update = 0.0

    def get_heart_rate(self):  return self._latest_data["heart_rate"] if self.has_data else None
    def get_breath_rate(self): return self._latest_data["breath_rate"] if self.has_data else None
