import cv2 as cv
from .utils import put_korean_center_text

def draw_fullscreen_overlay_center_text(img, message, bgr_color, alpha=0.55, font_scale=1.6, thickness=4):
    """화면 전체 반투명 + 중앙 한국어 문구"""
    h, w = img.shape[:2]
    overlay = img.copy()
    cv.rectangle(overlay, (0, 0), (w, h), bgr_color, -1)
    cv.addWeighted(img, 1 - alpha, overlay, alpha, 0, img)
    base = int(36 * (h / 768.0) * font_scale)
    font_size = max(24, base)
    stroke = max(2, int(thickness * 0.8))
    return put_korean_center_text(img, message, font_size=font_size, stroke=stroke)
