import cv2 as cv, numpy as np, math
from PIL import ImageFont, ImageDraw, Image

# 한국어 폰트 경로 (환경에 맞게 교체-현재 Jetson 환경)
KOREAN_FONT_PATH = "/home/simson/gyeonglee/dashboard/nanum-all_new/Nanum/NanumGothic/NanumFontSetup_TTF_GOTHIC/NanumGothicExtraBold.ttf"

def put_korean_text(img, text, x, y, font_path=KOREAN_FONT_PATH, color=(255,255,255), font_size=28, stroke=0, stroke_color=(0,0,0)):
    img_pil = Image.fromarray(cv.cvtColor(img, cv.COLOR_BGR2RGB))
    draw = ImageDraw.Draw(img_pil)
    font = ImageFont.truetype(font_path, int(font_size))
    if stroke > 0:
        draw.text((int(x), int(y)), text, font=font, fill=stroke_color, stroke_width=int(stroke), stroke_fill=stroke_color)
    draw.text((int(x), int(y)), text, font=font, fill=tuple(color), stroke_width=int(stroke), stroke_fill=stroke_color)
    return cv.cvtColor(np.array(img_pil), cv.COLOR_RGB2BGR)

def put_korean_center_text(img, text, font_path=KOREAN_FONT_PATH, color=(255,255,255), font_size=36, stroke=3, stroke_color=(0,0,0)):
    h, w = img.shape[:2]
    img_pil = Image.fromarray(cv.cvtColor(img, cv.COLOR_BGR2RGB))
    draw = ImageDraw.Draw(img_pil)
    font = ImageFont.truetype(font_path, int(font_size))
    tw, th = draw.textbbox((0,0), text, font=font)[2:]
    x = (w - tw) // 2; y = (h - th) // 2
    if stroke > 0:
        draw.text((x, y), text, font=font, fill=stroke_color, stroke_width=int(stroke), stroke_fill=stroke_color)
    draw.text((x, y), text, font=font, fill=tuple(color), stroke_width=int(stroke), stroke_fill=stroke_color)
    return cv.cvtColor(np.array(img_pil), cv.COLOR_RGB2BGR)

def _fit_into_box(dst, rect, src):
    x, y, w, h = rect
    if src is None or w<=0 or h<=0: return
    Hs, Ws = src.shape[:2]
    if Hs<=0 or Ws<=0: return
    s = min(w/float(Ws), h/float(Hs))
    nw, nh = int(Ws*s), int(Hs*s)
    if nw<=0 or nh<=0: return
    resized = cv.resize(src, (nw, nh))
    ox = x + (w-nw)//2; oy = y + (h-nh)//2
    dst[oy:oy+nh, ox:ox+nw] = resized

def _semi_gauge(canvas, cx, cy, r, value, vmax):
    cv.ellipse(canvas, (cx, cy), (r, r), 0, 180, 360, (128,128,128), 4, cv.LINE_AA)
    cv.ellipse(canvas, (cx, cy), (r-10, r-10), 0, 180, 360, (128,128,128), 2, cv.LINE_AA)
    num_ticks = 9
    for i in range(num_ticks):
        ang = math.radians(180 - (180 * i / (num_ticks - 1)))
        x1 = int(cx + (r-5)*math.cos(ang)); y1 = int(cy - (r-5)*math.sin(ang))
        x2 = int(cx + (r-20)*math.cos(ang)); y2 = int(cy - (r-20)*math.sin(ang))
        cv.line(canvas, (x1, y1), (x2, y2), (255,255,255), 3, cv.LINE_AA)
    v = 0.0 if vmax<=0 else max(0.0, min(1.0, float(value)/float(vmax)))
    ang = math.radians(180 - 180 * v)
    x2 = int(cx + (r-25)*math.cos(ang)); y2 = int(cy - (r-25)*math.sin(ang))
    color = (0,0,255) if value > vmax*0.85 else (0,165,255) if value > vmax*0.7 else (0,255,0)
    cv.line(canvas, (cx, cy), (x2, y2), color, 4, cv.LINE_AA)
    cv.circle(canvas, (cx, cy), 8, (255,255,255), -1, cv.LINE_AA); cv.circle(canvas, (cx, cy), 5, (0,0,0), -1, cv.LINE_AA)

def _semi_speed_gauge(canvas, cx, cy, r, value, vmax):
    _semi_gauge(canvas, cx, cy, r, value, vmax)

def _vbar(canvas, x, y, w, h, percent, fill_color):
    cv.rectangle(canvas, (x, y), (x+w, y+h), (255,255,0), 3)
    p = max(0.0, min(100.0, float(percent))) / 100.0
    fh = int(h * p)
    if fh>0:
        cv.rectangle(canvas, (x+3, y+h-fh+3), (x+w-3, y+h-3), fill_color, -1, cv.LINE_AA)

def _scroll_plot(canvas, x, y, w, h, hist, color, ymin, ymax, title, fill_ratio=0.8):
    cv.rectangle(canvas, (x, y), (x+w, y+h), (255,255,255), -1)
    if title:
        cv.putText(canvas, title, (x+10, y+25), cv.FONT_HERSHEY_SIMPLEX, 0.6, (0,0,0), 2, cv.LINE_AA)
    if not hist or len(hist) < 2: return
    draw_w = max(2, int(w * float(fill_ratio)))
    vals = hist[-w:]
    def mapy(v): v = min(max(v, ymin), ymax); return int(y + h - (v - ymin) / (ymax - ymin + 1e-9) * h)
    pts = []
    n = len(vals)
    for i, v in enumerate(vals):
        if v is None: continue
        xi = x + int(i * (draw_w - 1) / (n - 1)) if n > 1 else x
        pts.append((xi, mapy(v)))
    if len(pts) >= 2:
        import numpy as np
        cv.polylines(canvas, [np.array(pts, dtype=np.int32)], False, color, 2, cv.LINE_AA)
