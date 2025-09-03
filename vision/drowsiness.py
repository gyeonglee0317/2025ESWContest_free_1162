import time, numpy as np

def _denorm(x, y, w, h):
    return int(min(max(x * w, 0), w - 1)), int(min(max(y * h, 0), h - 1))

def _distance(p1, p2):
    import numpy as np
    return float(np.hypot(p1[0] - p2[0], p1[1] - p2[1]))

class DrowsinessModule:
    def __init__(self, ear_thresh=0.2, wait_time=2.0):
        self.eye_idxs = {
            "left":  [362, 385, 387, 263, 373, 380],
            "right": [33, 160, 158, 133, 153, 144],
        }
        self.EAR_THRESH = ear_thresh
        self.WAIT_TIME = wait_time
        self.state = {"start_time": time.perf_counter(), "drowsy_time": 0.0, "is_drowsy": False}

    def recalibrate(self):
        self.state = {"start_time": time.perf_counter(), "drowsy_time": 0.0, "is_drowsy": False}

    def _get_ear(self, lms, idxs, w, h):
        coords = []
        for i in idxs:
            lm = lms[i]; coords.append(_denorm(lm.x, lm.y, w, h))
        try:
            p2p6 = _distance(coords[1], coords[5])
            p3p5 = _distance(coords[2], coords[4])
            p1p4 = _distance(coords[0], coords[3])
            ear = (p2p6 + p3p5) / (2.0 * p1p4) if p1p4 > 1e-6 else 0.0
        except Exception:
            ear = 0.0
        return ear, coords

    def process(self, frame_bgr, landmarks):
        h, w = frame_bgr.shape[:2]
        if landmarks is None:
            self.recalibrate(); return 0.0, False
        left_ear, _ = self._get_ear(landmarks, self.eye_idxs["left"], w, h)
        right_ear, _= self._get_ear(landmarks, self.eye_idxs["right"], w, h)
        ear = (left_ear + right_ear) / 2.0
        if ear < self.EAR_THRESH:
            now = time.perf_counter()
            self.state["drowsy_time"] += now - self.state["start_time"]
            self.state["start_time"] = now
            if self.state["drowsy_time"] >= self.WAIT_TIME:
                self.state["is_drowsy"] = True
        else:
            self.recalibrate()
        return ear, self.state["is_drowsy"]
