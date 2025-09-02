import cv2 as cv, numpy as np
from .utils import put_korean_text, _fit_into_box, _semi_gauge, _semi_speed_gauge, _vbar, _scroll_plot

def render_dashboard_exact(frame_driver, frame_pedal,
                           rpm, speed,
                           accel_percent, brake_percent,
                           heart_rate, breath_rate,
                           hr_hist, br_hist,
                           W=1366, H=768, fsr_pressed=None, twofoot_dur=None,
                           pedal_flag_active=False, condition_flags_active=False, pedal_misuse_detected=False):
    canvas = np.zeros((H, W, 3), dtype=np.uint8)

    # 좌측 비디오 타일
    d_x = int(W*0.01); d_y = int(H*0.02); d_w = int(W*0.45); d_h = int(H*0.45)
    cv.rectangle(canvas, (d_x, d_y), (d_x+d_w, d_y+d_h), (255,255,0), 3)
    _fit_into_box(canvas, (d_x+3, d_y+3, d_w-6, d_h-6), frame_driver)

    p_x = int(W*0.01); p_y = int(H*0.52); p_w = int(W*0.45); p_h = int(H*0.45)
    cv.rectangle(canvas, (p_x, p_y), (p_x+p_w, p_y+p_h), (255,255,0), 3)
    _fit_into_box(canvas, (p_x+3, p_y+3, p_w-6, p_h-6), frame_pedal)

    if fsr_pressed is not None:
        twofoot = (fsr_pressed is False)
        tf_text  = f"Two-Footed Driving: {twofoot_dur:.1f}s" if twofoot else "Two-Footed Driving: X"
        tf_color = (0,0,255) if twofoot else (0,255,0)
        cv.putText(canvas, tf_text, (int(W*0.15), int(H*0.57)), cv.FONT_HERSHEY_SIMPLEX, 1.0, tf_color, 3, cv.LINE_AA)

    # 반원 게이지 (RPM / SPEED)
    r_c = int(W*0.10)
    cx1, cy1 = int(W*0.58), int(H*0.25)
    cx2, cy2 = int(W*0.79), int(H*0.25)
    _semi_gauge(canvas, cx1, cy1, r_c, 0 if rpm is None else rpm, 8000)
    _semi_speed_gauge(canvas, cx2, cy2, r_c, 0 if speed is None else speed, 200)
    if rpm   is not None: cv.putText(canvas, f"{int(rpm)}rpm",   (int(W*0.53), int(H*0.30)), cv.FONT_HERSHEY_SIMPLEX, 1.0, (255,255,255), 2)
    if speed is not None: cv.putText(canvas, f"{int(speed)}km/h",(int(W*0.74), int(H*0.30)), cv.FONT_HERSHEY_SIMPLEX, 1.0, (255,255,255), 2)

    # 세로 바 (ACCEL / BRAKE)
    a_x = int(W*0.905); a_y = int(H*0.03); a_w = int(W*0.03); a_h = int(H*0.23)
    _vbar(canvas, a_x, a_y, a_w, a_h, 0 if accel_percent is None else accel_percent, (0,0,255))
    cv.putText(canvas, "ACCEL", (a_x-8, a_y-8), cv.FONT_HERSHEY_SIMPLEX, 0.5, (0,0,255), 2)
    cv.putText(canvas, f"{int(accel_percent)}%", (int(W*0.898), int(H*0.30)), cv.FONT_HERSHEY_SIMPLEX, 1.0, (255,255,255), 2)

    b_x = int(W*0.955); b_y = int(H*0.03); b_w = int(W*0.03); b_h = int(H*0.23)
    _vbar(canvas, b_x, b_y, b_w, b_h, 0 if brake_percent is None else brake_percent, (0,255,0))
    cv.putText(canvas, "BRAKE", (b_x-8, b_y-8), cv.FONT_HERSHEY_SIMPLEX, 0.5, (0,255,0), 2)
    cv.putText(canvas, f"{int(brake_percent)}%", (int(W*0.95), int(H*0.30)), cv.FONT_HERSHEY_SIMPLEX, 1.0, (255,255,255), 2)

    # 그래프 2개 (심박/호흡)
    h_x = int(W*0.68); h_y = int(H*0.34); h_w = int(W*0.3); h_h = int(H*0.17)
    _scroll_plot(canvas, h_x, h_y, h_w, h_h, hr_hist, (0,0,255), 40, 150, "")
    canvas = put_korean_text(canvas, "심박수", int(W*0.48), int(H*0.35), font_size=40)

    r_x = int(W*0.68); r_y = int(H*0.54); r_w = int(W*0.3); r_h = int(H*0.17)
    _scroll_plot(canvas, r_x, r_y, r_w, r_h, br_hist, (0,128,0), 8, 30, "")
    canvas = put_korean_text(canvas, "호흡수", int(W*0.48), int(H*0.55), font_size=40)

    # FLOW 원 3개 (SPI 플래그)
    def circle(xr, yg, ok):
        cx = int(W*xr); cy = int(H*0.854); r = int(H*0.1)
        color = (0,0,255) if ok else (128,128,128)
        cv.circle(canvas, (cx, cy), r, color, -1)

    circle(0.562, 0.854, pedal_flag_active)     # 페달작동 이상
    circle(0.727, 0.854, pedal_flag_active and condition_flags_active)  # 특이 생체신호
    circle(0.892, 0.854, pedal_misuse_detected) # 오조작 감지

    # 라벨
    canvas = put_korean_text(canvas, "페달\n작동량\n이상", int(W*0.543), int(H*0.78), font_size=30)
    canvas = put_korean_text(canvas, "특이\n생체신호\n감지", int(W*0.685), int(H*0.78), font_size=30)
    canvas = put_korean_text(canvas, "페달\n오조작\n감지", int(W*0.862), int(H*0.78), font_size=30)

    # 심박/호흡 수치
    cv.putText(canvas, f"{heart_rate}bpm", (int(W*0.48), int(H*0.48)), cv.FONT_HERSHEY_SIMPLEX, 1.5, (255,255,255), 3)
    cv.putText(canvas, f"{breath_rate}brpm",(int(W*0.48), int(H*0.68)), cv.FONT_HERSHEY_SIMPLEX, 1.5, (255,255,255), 3)

    return np.ascontiguousarray(canvas)
