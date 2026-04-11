"""
Volleyball ball tracking using YOLO11x (fine-tuned on volleyball detection).
Falls back to VolleyVision's YOLOv7-tiny ball weights if available.

Computes trajectory, speed, and rally segmentation from ball positions.
"""
import numpy as np
import os
from collections import deque

BASE_DIR = "C:/sportsai-backend"

# VolleyVision Stage I has YOLOv7-tiny ball weights — use those if present
VV_BALL_WEIGHTS = os.path.join(
    BASE_DIR, "models/VolleyVision/Stage I - Volleyball/yV7-tiny/weights/best.pt"
)
# Fallback: general YOLO (less accurate for small ball)
FALLBACK_WEIGHTS = os.path.join(os.path.dirname(__file__), "yolo11x-pose.pt")

BALL_CONF   = 0.35   # lower threshold — ball is small and fast
MAX_MISSING = 10     # frames before a rally gap is declared

_ball_model = None


def _get_model():
    global _ball_model
    if _ball_model is None:
        from ultralytics import YOLO
        weights = VV_BALL_WEIGHTS if os.path.exists(VV_BALL_WEIGHTS) else FALLBACK_WEIGHTS
        _ball_model = YOLO(weights)
        print(f"[ball_tracker] loaded {weights}")
    return _ball_model


def _estimate_speed(positions: list, fps: float) -> list:
    """Pixel-space speed between consecutive detections (px/frame → px/s)."""
    speeds = [0.0]
    for i in range(1, len(positions)):
        if positions[i] and positions[i - 1]:
            dx = positions[i][0] - positions[i - 1][0]
            dy = positions[i][1] - positions[i - 1][1]
            speeds.append(round(float(np.hypot(dx, dy) * fps), 2))
        else:
            speeds.append(None)
    return speeds


def _segment_rallies(positions: list) -> list:
    """
    Split trajectory into rallies based on gaps (ball missing > MAX_MISSING frames).
    Returns list of {"start_frame", "end_frame", "length_frames"}.
    """
    rallies = []
    in_rally = False
    start = 0
    missing = 0

    for i, pos in enumerate(positions):
        if pos is not None:
            if not in_rally:
                in_rally = True
                start = i
            missing = 0
        else:
            missing += 1
            if in_rally and missing > MAX_MISSING:
                rallies.append({"start_frame": start, "end_frame": i - missing, "length_frames": i - missing - start})
                in_rally = False

    if in_rally:
        rallies.append({"start_frame": start, "end_frame": len(positions) - 1, "length_frames": len(positions) - 1 - start})

    return rallies


def track_ball(video_path: str) -> dict:
    """
    Track the volleyball across all frames.

    Returns:
        {
          "positions": [{"frame": int, "x": float, "y": float, "conf": float} | None, ...],
          "speeds_px_per_sec": [float | None, ...],
          "rallies": [{"start_frame", "end_frame", "length_frames"}, ...],
          "total_frames": int,
          "detection_rate": float,
        }
    """
    import cv2

    model = _get_model()
    cap = cv2.VideoCapture(video_path)
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    frame_num = 0
    positions = []

    while True:
        ret, frame = cap.read()
        if not ret:
            break
        frame_num += 1

        results = model(frame, conf=BALL_CONF, verbose=False)
        detected = None

        if results and len(results[0].boxes) > 0:
            # Pick highest-confidence detection (ball = class 0 in VolleyVision)
            boxes = results[0].boxes
            best  = int(boxes.conf.argmax())
            cx, cy = boxes.xywh[best, :2].cpu().numpy()
            conf   = float(boxes.conf[best])
            detected = {"frame": frame_num, "x": round(float(cx), 1), "y": round(float(cy), 1), "conf": round(conf, 3)}

        positions.append(detected)

    cap.release()

    pos_xy = [(p["x"], p["y"]) if p else None for p in positions]
    speeds = _estimate_speed(pos_xy, fps)
    rallies = _segment_rallies(pos_xy)
    detected_count = sum(1 for p in positions if p is not None)

    return {
        "positions": positions,
        "speeds_px_per_sec": speeds,
        "rallies": rallies,
        "total_frames": frame_num,
        "detection_rate": round(detected_count / max(frame_num, 1), 3),
    }
