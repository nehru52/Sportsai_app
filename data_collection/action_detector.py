"""
Action detection using VolleyVision's YOLOv8m model with sliding window temporal smoothing.
Wraps models/VolleyVision/Stage II - Players & Actions logic as a callable module.

Classes: block(0), defense(1), serve(2), set(3), spike(4)
Trained on 14K images, 92.31% mAP50.
"""
import os
from collections import deque, Counter

BASE_DIR = "C:/sportsai-backend"
WEIGHTS_PATH = os.path.join(
    BASE_DIR,
    "models/VolleyVision/Stage II - Players & Actions/actions/yV8_medium/weights/best.pt"
)

CLASSES = {0: "block", 1: "defense", 2: "serve", 3: "set", 4: "spike"}
WINDOW_SIZE = 5       # frames in sliding window
MIN_COUNT = 3         # detections needed to confirm an event
CONF_THRESHOLD = 0.5

_action_model = None


def _get_model():
    global _action_model
    if _action_model is None:
        from ultralytics import YOLO
        _action_model = YOLO(WEIGHTS_PATH)
    return _action_model


def detect_actions(video_path: str) -> dict:
    """
    Run action detection on a video file.

    Returns:
        {
          "events": [{"frame": int, "action": str, "confidence": float}, ...],
          "dominant_action": str | None,
          "action_counts": {"spike": 3, ...},
          "total_frames": int,
        }
    """
    import cv2

    model = _get_model()
    cap = cv2.VideoCapture(video_path)
    sliding_window = deque(maxlen=WINDOW_SIZE)
    events = []
    action_counts: dict[str, int] = {}
    frame_num = 0
    last_event = None

    while True:
        ret, frame = cap.read()
        if not ret:
            break
        frame_num += 1

        results = model.predict(frame, conf=CONF_THRESHOLD, verbose=False)
        if results and len(results[0].boxes) > 0:
            cls_ids = results[0].boxes.cls.tolist()
            confs = results[0].boxes.conf.tolist()
            # pick highest-confidence detection this frame
            best = max(zip(cls_ids, confs), key=lambda x: x[1])
            cls_name = CLASSES[int(best[0])]
            sliding_window.append(cls_name)

            top_cls, top_count = Counter(sliding_window).most_common(1)[0]
            if top_count >= MIN_COUNT and top_cls != last_event:
                events.append({
                    "frame": frame_num,
                    "action": top_cls,
                    "confidence": round(float(best[1]), 3),
                })
                action_counts[top_cls] = action_counts.get(top_cls, 0) + 1
                last_event = top_cls
        else:
            sliding_window.append(None)
            last_event = None

    cap.release()

    dominant = max(action_counts, key=action_counts.get) if action_counts else None
    return {
        "events": events,
        "dominant_action": dominant,
        "action_counts": action_counts,
        "total_frames": frame_num,
    }
