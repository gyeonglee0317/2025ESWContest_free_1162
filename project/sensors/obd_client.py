OBD_AVAILABLE = True

class OBDClient:
    def __init__(self, port="/dev/ttyACM0", baudrate=9600, timeout=1.0, debug=False):
        self.port, self.baudrate, self.timeout, self.debug = port, baudrate, timeout, debug
        self._running = False
    def start(self): self._running = False; return False  # 실제 연결 없으면 False
    def get_rpm(self):         return None
    def get_speed(self):       return None
    def get_accel_pos(self):   return None
