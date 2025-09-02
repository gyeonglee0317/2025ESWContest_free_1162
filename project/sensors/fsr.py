import threading, time
import board, busio
import adafruit_ads1x15.ads1115 as ADS
from adafruit_ads1x15.analog_in import AnalogIn

class FSRMonitor:
    """ADS1115 FSR(발판 압력) → 눌림 여부 비차단 제공"""
    def __init__(self, i2c_scl=None, i2c_sda=None,
                 threshold=2000, check_interval=0.05,
                 not_pressed_duration=5.0, debug=False):
        self.threshold = int(threshold)
        self.check_interval = float(check_interval)
        self.not_pressed_duration = float(not_pressed_duration)
        self.debug = debug

        self._running = False
        self._thread = None
        self._pressed = False
        self._raw = 0; self._voltage = 0.0
        self._last_released_time = None

        self._i2c = self._ads = self._chan = None
        self.available = False
        try:
            scl = board.SCL if i2c_scl is None else i2c_scl
            sda = board.SDA if i2c_sda is None else i2c_sda
            self._i2c = busio.I2C(scl, sda)
            self._ads = ADS.ADS1115(self._i2c)
            self._chan = AnalogIn(self._ads, ADS.P0)
            self.available = True
        except Exception as e:
            print(f"[FSR] Init failed: {e}")
            self.available = False

    def _loop(self):
        was_pressed = False
        while self._running:
            try:
                if not self.available or self._chan is None:
                    self._pressed = False; time.sleep(0.5); continue
                raw = self._chan.value; volt = self._chan.voltage
                self._raw, self._voltage = raw, volt
                pressed_now = raw > self.threshold
                if pressed_now and not was_pressed:
                    if self.debug: print(f"[FSR] pressed (raw={raw}, V={volt:.3f})")
                    self._last_released_time = None
                elif (not pressed_now) and was_pressed:
                    if self.debug: print(f"[FSR] released (raw={raw}, V={volt:.3f})")
                    self._last_released_time = time.time()
                was_pressed = pressed_now
                self._pressed = pressed_now

                if (not pressed_now) and (self._last_released_time is not None):
                    if (time.time() - self._last_released_time) >= self.not_pressed_duration:
                        if self.debug: print("[FSR] Warning: released >= 5s")
                        self._last_released_time = None
                time.sleep(self.check_interval)
            except Exception as e:
                if self.debug: print(f"[FSR] loop error: {e}")
                time.sleep(0.1)

    def start(self):
        if self._running or not self.available: 
            if not self.available: print("[FSR] Not available. Skipping start.")
            return
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()
        print("[FSR] monitor started.")

    def stop(self):
        self._running = False
        if self._thread: self._thread.join(timeout=1.0)
        print("[FSR] monitor stopped.")

    def get_pressed(self): return bool(self._pressed)
    def get_raw(self):     return int(self._raw), float(self._voltage)
