#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import time, math, copy, itertools, csv
from collections import deque

import cv2 as cv
import numpy as np
from PIL import ImageFont, ImageDraw, Image

# ── 내부 모듈
from sensors.mmwave import MmWaveSensor
from sensors.fsr import FSRMonitor
from sensors.spi import open_spi, xfer_once
from sensors.obd_client import OBDClient, OBD_AVAILABLE

from vision.emotion import EmotionModule
from vision.drowsiness import DrowsinessModule
from vision.attention import ForwardAttentionModule
from vision.headpos import HeadPositionModule
from vision.pedal_tracker import PedalTracker

from ui.dashboard import render_dashboard_exact
from ui.overlay import draw_fullscreen_overlay_center_text
from common.calibration import CalibrationManager
from common.helpers import enhance_frame_for_face_detection

# ── Mediapipe(face mesh)
import mediapipe as mp
mp_face_mesh = mp.solutions.face_mesh
FACE_MESH = mp_face_mesh.FaceMesh(
    max_num_faces=1, refine_landmarks=True,
    min_detection_confidence=0.5, min_tracking_confidence=0.5
)

def create_jetson_csi_pipeline(camera_id=0, capture_width=1280, capture_height=720,
                               display_width=1280, display_height=720, framerate=30, flip_method=2):
    return (
        f"nvarguscamerasrc sensor-id={camera_id} ! "
        f"video/x-raw(memory:NVMM), width=(int){capture_width}, height=(int){capture_height}, "
        f"format=(string)NV12, framerate=(fraction){framerate}/1 ! "
        f"nvvidconv flip-method={flip_method} ! "
        f"video/x-raw, width=(int){display_width}, height=(int){display_height}, format=(string)BGRx ! "
        f"videoconvert ! video/x-raw, format=(string)BGR ! appsink drop=True"
    )

def main():
    # ── Driver 카메라 열기 (Jetson 파이프라인 → 실패시 0번)
    pipeline = create_jetson_csi_pipeline(flip_method=4)
    cap_driver = cv.VideoCapture(pipeline, cv.CAP_GSTREAMER)
    if not cap_driver.isOpened():
        cap_driver = cv.VideoCapture(0)
        if not cap_driver.isOpened():
            print("Error: cannot open any camera"); return

    # ── Pedal 카메라(원한다면 URL/인덱스 교체)
    pedal_cap = cv.VideoCapture(1)
    pedal_connected = pedal_cap.isOpened()

    # ── 모듈 준비
    emo           = EmotionModule()
    drowsy        = DrowsinessModule(ear_thresh=0.2, wait_time=2.0)
    forward       = ForwardAttentionModule()
    head_pos      = HeadPositionModule()
    emergency     = None  # 대시보드에서 오버레이 처리
    calibration   = CalibrationManager()
    pedal_tracker = PedalTracker()
    mmwave_sensor = MmWaveSensor(debug=False)
    fsr           = FSRMonitor(threshold=2000, check_interval=0.05, not_pressed_duration=5.0, debug=False)

    fsr.start()
    mmwave_sensor.start()

    obd = None
    if OBD_AVAILABLE:
        try:
            tmp = OBDClient(port='/dev/ttyACM0', baudrate=9600, timeout=1.0, debug=False)
            if tmp.start():
                obd = tmp
            else:
                print("[OBD] not started; continue without OBD")
        except Exception as e:
            print(f"[OBD] init error: {e}")

    # ── 그래프 히스토리
    hr_hist, br_hist = deque(maxlen=200), deque(maxlen=200)

    # ── 경과 타이머 상태
    drowsy_on_since = None
    twofoot_on_since = None
    forward_off_since = None

    # ── 임계값(초)
    DROWSY_WARN_SEC, TWOFOOT_WARN_SEC, FORWARD_WARN_SEC = 3.0, 5.0, 3.0

    # ── SPI 준비
    spi = open_spi()
    last_accel_percent = 0
    t0 = time.time()

    window = "Enhanced Driver Dashboard"
    cv.namedWindow(window, cv.WINDOW_NORMAL)
    cv.setWindowProperty(window, cv.WND_PROP_FULLSCREEN, cv.WINDOW_FULLSCREEN)

    print("Press ESC to exit, 'r' for 3s recalibration, 'p' for pedal calibration")

    while True:
        ok, frame = cap_driver.read()
        if not ok: break
        frame = cv.flip(frame, 1)

        # ── 전처리 & 랜드마크
        enhanced = enhance_frame_for_face_detection(frame)
        rgb = cv.cvtColor(enhanced, cv.COLOR_BGR2RGB); rgb.flags.writeable = False
        results = FACE_MESH.process(rgb); rgb.flags.writeable = True
        face_lms = results.multi_face_landmarks[0] if results.multi_face_landmarks else None
        lm_raw = face_lms.landmark if face_lms else None

        # ── 캘리브레이션 진행 상태
        is_calibrating, cal_remaining = calibration.update()

        # ── 각 모듈
        emotion = emo.infer(frame, face_lms) if face_lms is not None else "No Face"
        ear, is_drowsy = drowsy.process(frame, lm_raw)
        is_head_down, head_status = head_pos.process(lm_raw)
        forward_ratio, attn_status, is_forward_looking = forward.process(lm_raw)

        # ── mmWave
        heart_rate = mmwave_sensor.get_heart_rate()
        resp_rate  = mmwave_sensor.get_breath_rate()
        if heart_rate is not None: hr_hist.append(float(heart_rate))
        if resp_rate  is not None: br_hist.append(float(resp_rate))

        # ── 페달 카메라
        pedal_view = None
        if pedal_connected:
            ok_p, pf = pedal_cap.read()
            if ok_p:
                if not pedal_tracker.is_calibrated:
                    pedal_tracker.calibrate_brake_simple(pf)
                pedal_view, _ = pedal_tracker.update(pf)

        # ── OBD (없으면 데모 값)
        if obd:
            rpm   = obd.get_rpm()
            speed = obd.get_speed()
            accel_pos = obd.get_accel_pos()
        else:
            rpm = speed = accel_pos = None

        if rpm   is None:
            t = time.time() - t0
            rpm = max(0, min(8000, int(1500 + 1200*math.sin(t*1.2) + 500*math.sin(t*0.3))))
        if speed is None:
            t = time.time() - t0
            speed = max(0, min(200, int(60 + 40*math.sin(t*0.8))))

        accel_percent = int(max(0, min(100, accel_pos))) if accel_pos is not None else last_accel_percent
        last_accel_percent = accel_percent
        brake_percent = pedal_tracker.get_brake_percent()

        # ── SPI 전송/수신
        emotion_map = {"Neutral":0, "Happy":1, "Sad":2, "Surprise":4, "Angry":3}
        expression_code = emotion_map.get(emotion, 0)
        try:
            spi_result = xfer_once(
                spi,
                int(accel_percent),
                int(expression_code),
                int(heart_rate or 0),
                int(resp_rate or 0),
            )
        except Exception as e:
            print(f"[SPI] error: {e}")
            spi_result = {"pedal_flag":0, "cond_flags":0, "pm":0}

        pedal_flag_active     = bool(spi_result.get("pedal_flag", 0))
        condition_flags_active= bool(spi_result.get("cond_flags", 0))
        pedal_misuse_detected = bool(spi_result.get("pm", 0))

        # ── FSR 상태
        fsr_pressed = fsr.get_pressed() if fsr.available else None
        now_ts = time.time()

        # 타이머 누적
        drowsy_on_since   = drowsy_on_since   or (now_ts if is_drowsy else None)
        if not is_drowsy: drowsy_on_since = None

        twofoot_on_since  = twofoot_on_since  or (now_ts if fsr_pressed is False else None)
        if fsr_pressed is not False: twofoot_on_since = None

        forward_off_since = forward_off_since or (now_ts if not is_forward_looking else None)
        if is_forward_looking: forward_off_since = None

        drowsy_dur  = (now_ts - drowsy_on_since)   if drowsy_on_since   else 0.0
        twofoot_dur = (now_ts - twofoot_on_since)  if twofoot_on_since  else 0.0
        forward_dur = (now_ts - forward_off_since) if forward_off_since else 0.0

        # ── 대시보드 렌더
        dash = render_dashboard_exact(
            frame_driver=frame,
            frame_pedal=pedal_view,
            rpm=rpm, speed=speed,
            accel_percent=accel_percent, brake_percent=brake_percent,
            heart_rate=heart_rate, breath_rate=resp_rate,
            hr_hist=list(hr_hist), br_hist=list(br_hist),
            W=1366, H=768,
            fsr_pressed=fsr_pressed, twofoot_dur=twofoot_dur,
            pedal_flag_active=pedal_flag_active,
            condition_flags_active=condition_flags_active,
            pedal_misuse_detected=pedal_misuse_detected
        )

        # ── 경고/오버레이
        overlay_active = False
        if is_calibrating:
            draw_fullscreen_overlay_center_text(
                dash, f"캘리브레이션 중... {cal_remaining:.1f}초",
                bgr_color=(255,0,0), alpha=0.55, font_scale=1.8, thickness=5
            )
            overlay_active = True
        else:
            alert_text = None
            if drowsy_on_since   and drowsy_dur  >= DROWSY_WARN_SEC:  alert_text = "졸음운전이 감지되었습니다."
            elif forward_off_since and forward_dur >= FORWARD_WARN_SEC: alert_text = "전방미주시 상태입니다. 전방을 주시해주세요."
            elif twofoot_on_since  and twofoot_dur >= TWOFOOT_WARN_SEC:  alert_text = "양발운전이 감지되었습니다."

            if alert_text:
                draw_fullscreen_overlay_center_text(
                    dash, alert_text, bgr_color=(0,255,255), alpha=0.45, font_scale=1.6, thickness=4
                )
                overlay_active = True

        cv.imshow(window, dash)
        key = cv.waitKey(1) & 0xFF
        if key == 27: break
        elif key in (ord('r'), ord('R')):
            calibration.start_calibration()
            drowsy.recalibrate(); forward.recalibrate(); head_pos.recalibrate(); pedal_tracker.recalibrate()

    # ── 종료
    try: mmwave_sensor.stop()
    except: pass
    try: fsr.stop()
    except: pass
    cap_driver.release()
    if pedal_connected: pedal_cap.release()
    cv.destroyAllWindows()

if __name__ == "__main__":
    main()
