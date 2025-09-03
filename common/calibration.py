import time

class CalibrationManager:
    def __init__(self):
        self.is_calibrating = False
        self.calibration_start_time = None
        self.CALIBRATION_DURATION = 3.0

    def start_calibration(self):
        self.is_calibrating = True
        self.calibration_start_time = time.time()
        print("=== STARTING 3-SECOND CALIBRATION ===")

    def update(self):
        if not self.is_calibrating: return False, 0.0
        now = time.time(); elapsed = now - self.calibration_start_time
        if elapsed >= self.CALIBRATION_DURATION:
            self.is_calibrating = False
            print("=== CALIBRATION COMPLETE ===")
            return False, 0.0
        remaining = self.CALIBRATION_DURATION - elapsed
        return True, remaining
