import cv2 as cv, numpy as np

def denorm(x, y, w, h):
    return int(min(max(x * w, 0), w - 1)), int(min(max(y * h, 0), h - 1))

def distance(p1, p2):
    return float(np.hypot(p1[0] - p2[0], p1[1] - p2[1]))

def enhance_frame_for_face_detection(frame):
    gray = cv.cvtColor(frame, cv.COLOR_BGR2GRAY)
    enhanced = cv.equalizeHist(gray)
    clahe = cv.createCLAHE(clipLimit=3.0, tileGridSize=(8,8))
    enhanced = clahe.apply(enhanced)
    enhanced = cv.GaussianBlur(enhanced, (3, 3), 0)
    gamma = 1.2
    enhanced = (np.power(enhanced / 255.0, gamma) * 255.0).astype(np.uint8)
    return cv.cvtColor(enhanced, cv.COLOR_GRAY2BGR)
