import numpy as np, cv2 as cv

class PedalTracker:
    def __init__(self, th_green=25, area_min=80, alpha=0.6, path_points=101):
        self.TH_GREEN = th_green
        self.AREA_MIN = area_min
        self.KERNEL = np.ones((3,3), np.uint8)
        self.alpha = alpha
        self.path_points = path_points
        self.ema_green = None
        self.roi_green = None
        self.init_green_y = None
        self.THRESH_DIFF = 10
        self._brake_percent = 0
        self.zero_pos = None
        self.full_pos = None
        self.full_brake_path = None
        self.is_calibrated = False

    def find_nearest_index(self, points, current):
        dists = [np.linalg.norm(np.array(current) - np.array(p)) for p in points]
        return int(np.argmin(dists))

    def find_point_by_saliency(self, frame):
        bgr = frame.astype(np.int16)
        B, G, R = bgr[:,:,0], bgr[:,:,1], bgr[:,:,2]
        L = (R + G + B) // 3
        Sg = (G - L)
        mask_g = (Sg > self.TH_GREEN).astype(np.uint8) * 255
        mask_g = cv.morphologyEx(mask_g, cv.MORPH_OPEN, self.KERNEL, iterations=1)

        def largest_center(mask):
            cnts,_ = cv.findContours(mask, cv.RETR_EXTERNAL, cv.CHAIN_APPROX_SIMPLE)
            if not cnts: return None, None
            c = max(cnts, key=cv.contourArea)
            if cv.contourArea(c) < self.AREA_MIN: return None, None
            M = cv.moments(c)
            if M["m00"] == 0: return None, None
            cx = int(M["m10"]/M["m00"]); cy = int(M["m01"]/M["m00"])
            return (cx, cy), c

        green_pt, green_cnt = largest_center(mask_g)
        return green_pt, green_cnt, mask_g

    def update(self, frame):
        if frame is None: return frame, ""
        view = frame.copy()
        H, W = frame.shape[:2]

        if self.roi_green:
            x, y, w, h = map(int, self.roi_green)
            x = max(0, min(x, W-1)); y = max(0, min(y, H-1))
            w = max(1, min(w, W-x)); h = max(1, min(h, H-y))
            crop_green = frame[y:y+h, x:x+w]
        else:
            crop_green = frame; x, y = 0, 0

        green_pt, green_cnt, mask_g = self.find_point_by_saliency(crop_green)
        action_text = ""

        if green_pt and self.full_brake_path and self.is_calibrated:
            gx, gy = green_pt[0]+x, green_pt[1]+y
            self.ema_green = gy if self.ema_green is None else self.alpha*self.ema_green + (1-self.alpha)*gy
            if self.init_green_y is None:
                self.init_green_y = gy
            elif abs(gy - self.init_green_y) >= self.THRESH_DIFF:
                action_text = "BRAKE"

            idx = self.find_nearest_index(self.full_brake_path, (gx, gy))
            self._brake_percent = idx
            cv.circle(view, (gx, gy), 8, (0, 255, 0), -1)
            cv.putText(view, f"BRAKE: {self._brake_percent}%", (gx+10, gy-10),
                       cv.FONT_HERSHEY_SIMPLEX, 0.6, (0,255,0), 2)
        return view, action_text

    def get_brake_percent(self): return self._brake_percent

    def calibrate_brake_simple(self, frame):
        if frame is None: return False
        green_pt, _, _ = self.find_point_by_saliency(frame)
        if green_pt:
            self.zero_pos = green_pt
            self.full_pos = (green_pt[0], green_pt[1] + 50)
            self.full_brake_path = [
                ( int(self.zero_pos[0] + (self.full_pos[0]-self.zero_pos[0])*i/(self.path_points-1)),
                  int(self.zero_pos[1] + (self.full_pos[1]-self.zero_pos[1])*i/(self.path_points-1)) )
                for i in range(self.path_points)
            ]
            self.is_calibrated = True
            return True
        return False

    def recalibrate(self):
        self.ema_green = None
        self.init_green_y = None
        self._brake_percent = 0
        self.zero_pos = self.full_pos = None
        self.full_brake_path = None
        self.is_calibrated = False
