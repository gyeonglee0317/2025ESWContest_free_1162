class HeadPositionModule:
    def __init__(self):
        self.NOSE_TIP = 1
        self.FOREHEAD_CENTER = 9
        self.CHIN_CENTER = 175
        self.baseline_head_y = None
        self.head_tilt_threshold = 0.08
        self.calibration_frames = []
        self.calibration_count = 0
        self.is_calibrated = False

    def recalibrate(self):
        self.baseline_head_y = None
        self.calibration_frames = []
        self.calibration_count = 0
        self.is_calibrated = False

    def _get_head_y_position(self, landmarks):
        try:
            nose_y = landmarks[self.NOSE_TIP].y
            chin_y = landmarks[self.CHIN_CENTER].y
            return (nose_y + chin_y) / 2.0
        except Exception:
            return None

    def process(self, landmarks):
        if landmarks is None:
            return False, "No_Face"
        current_head_y = self._get_head_y_position(landmarks)
        if current_head_y is None: return False, "ERROR"
        if not self.is_calibrated:
            self.calibration_frames.append(current_head_y)
            self.calibration_count += 1
            if self.calibration_count >= 30:
                self.baseline_head_y = sum(self.calibration_frames) / len(self.calibration_frames)
                self.is_calibrated = True
            return False, "CALIBRATING"
        head_drop = current_head_y - self.baseline_head_y
        is_head_down = head_drop > self.head_tilt_threshold
        return is_head_down, f"DROP:{head_drop:.3f}"
