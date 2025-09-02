import time
from collections import deque

class ForwardAttentionModule:
    def __init__(self):
        self.LEFT_EYE_CORNERS  = (33, 133)
        self.RIGHT_EYE_CORNERS = (362, 263)
        self.LEFT_EYE_LIDS     = (159, 145)
        self.RIGHT_EYE_LIDS    = (386, 374)
        self.LEFT_IRIS_POINTS  = [468, 469, 470, 471, 472]
        self.RIGHT_IRIS_POINTS = [473, 474, 475, 476, 477]
        self.forward_history = deque(maxlen=30)
        self.forward_lost_start = None
        self.DANGER_TIME = 3.0
        self.FORWARD_X_RANGE = (0.25, 0.75)
        self.FORWARD_Y_RANGE = (0.25, 0.75)

    def recalibrate(self):
        self.forward_history = deque(maxlen=30)
        self.forward_lost_start = None

    @staticmethod
    def _ratio(v, lo, hi):
        d = max(hi - lo, 1e-6)
        return min(max((v - lo) / d, 0.0), 1.0)

    def _get_iris_center(self, landmarks, iris_points):
        try:
            pts = [landmarks[i] for i in iris_points if i < len(landmarks)]
            if len(pts) == 0: return None, None
            weights = [3.0] + [1.0]*(len(pts)-1)
            s = sum(weights[:len(pts)])
            ax = sum(p.x*w for p, w in zip(pts, weights)) / s
            ay = sum(p.y*w for p, w in zip(pts, weights)) / s
            return ax, ay
        except Exception:
            return None, None

    def _gaze_xy(self, lms):
        try:
            lc1, lc2 = self.LEFT_EYE_CORNERS
            lt, lb   = self.LEFT_EYE_LIDS
            rc1, rc2 = self.RIGHT_EYE_CORNERS
            rt, rb   = self.RIGHT_EYE_LIDS
            lix, liy = self._get_iris_center(lms, self.LEFT_IRIS_POINTS)
            rix, riy = self._get_iris_center(lms, self.RIGHT_IRIS_POINTS)
            if lix is None or rix is None:
                return ( (lms[lc1].x + lms[lc2].x)/2.0 + (lms[rc1].x + lms[rc2].x)/2.0 )/2.0, \
                       ( (lms[lt].y  + lms[lb].y )/2.0 + (lms[rt].y  + lms[rb].y )/2.0 )/2.0
            xL = self._ratio(lix, min(lms[lc1].x, lms[lc2].x), max(lms[lc1].x, lms[lc2].x))
            yL = self._ratio(liy, min(lms[lt].y,  lms[lb].y ), max(lms[lt].y,  lms[lb].y ))
            xR = self._ratio(rix, min(lms[rc1].x, lms[rc2].x), max(lms[rc1].x, lms[rc2].x))
            yR = self._ratio(riy, min(lms[rt].y,  lms[rb].y ), max(lms[rt].y,  lms[rb].y ))
            return (xL + xR)/2.0, (yL + yR)/2.0
        except Exception:
            return 0.5, 0.5

    def process(self, landmarks):
        now = time.time()
        if landmarks is None:
            self.forward_history.append(0)
            if self.forward_lost_start is None:
                self.forward_lost_start = now
            return 0.0, "DANGER", False

        gx, gy = self._gaze_xy(landmarks)
        is_forward = (self.FORWARD_X_RANGE[0] <= gx <= self.FORWARD_X_RANGE[1] and
                      self.FORWARD_Y_RANGE[0] <= gy <= self.FORWARD_Y_RANGE[1])
        self.forward_history.append(1 if is_forward else 0)

        if is_forward:
            self.forward_lost_start = None
            ratio = sum(self.forward_history)/len(self.forward_history)
            return ratio, "FORWARD", True

        if self.forward_lost_start is None:
            self.forward_lost_start = now

        ratio = sum(self.forward_history)/len(self.forward_history)
        status = "DANGER" if (now - self.forward_lost_start > self.DANGER_TIME) else ("DISTRACTED" if ratio > 0.3 else "DANGER")
        return ratio, status, False
