"""
Multi-person player tracker using YOLO11x-pose + ByteTrack.
Tracks up to 12 players (6v6) across frames with persistent IDs.
Assigns team side (left/right) based on court X position.

ByteTrack is included in ultralytics — no extra install needed.
"""
import numpy as np
import os

YOLO_MODEL_PATH = os.path.join(os.path.dirname(__file__), "yolo11x-pose.pt")
CONFIDENCE_THRESHOLD = 0.5
MAX_PLAYERS = 12

_yolo = None


def _get_yolo():
    global _yolo
    if _yolo is None:
        from ultralytics import YOLO
        _yolo = YOLO(YOLO_MODEL_PATH)
    return _yolo


def _assign_teams(tracks: list, img_w: int) -> list:
    """
    Simple team assignment: players left of centre → team A, right → team B.
    Works for standard sideline camera angle.
    """
    mid = img_w / 2
    for t in tracks:
        cx = t["bbox"][0] + t["bbox"][2] / 2
        t["team"] = "A" if cx < mid else "B"
    return tracks


def track_players(video_path: str) -> dict:
    """
    Run multi-person tracking on a full video.

    Returns:
        {
          "tracks": {
              "1": [{"frame": int, "bbox": [x,y,w,h], "keypoints": [[x,y,conf]x17], "team": "A"|"B"}, ...],
              ...
          },
          "total_frames": int,
          "players_detected": int,   # unique track IDs
        }
    """
    import cv2

    model = _get_yolo()
    cap = cv2.VideoCapture(video_path)
    img_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    frame_num = 0
    all_tracks: dict[str, list] = {}

    while True:
        ret, frame = cap.read()
        if not ret:
            break
        frame_num += 1

        # persist=True keeps ByteTrack IDs consistent across frames
        results = model.track(
            frame,
            persist=True,
            conf=CONFIDENCE_THRESHOLD,
            max_det=MAX_PLAYERS,
            verbose=False,
        )

        if not results or results[0].boxes is None:
            continue

        boxes = results[0].boxes
        kps   = results[0].keypoints

        if boxes.id is None:
            continue

        frame_tracks = []
        for i, track_id in enumerate(boxes.id.int().tolist()):
            box  = boxes.xywh[i].cpu().numpy().tolist()   # [cx, cy, w, h]
            conf = float(boxes.conf[i])

            keypoints = None
            if kps is not None and i < len(kps.data):
                keypoints = kps.data[i].cpu().numpy().tolist()  # (17, 3) [x,y,conf]

            frame_tracks.append({
                "frame":     frame_num,
                "bbox":      box,
                "conf":      round(conf, 3),
                "keypoints": keypoints,
                "team":      None,
            })

            tid = str(track_id)
            if tid not in all_tracks:
                all_tracks[tid] = []
            all_tracks[tid].append(frame_tracks[-1])

        _assign_teams(frame_tracks, img_w)

    cap.release()

    return {
        "tracks": all_tracks,
        "total_frames": frame_num,
        "players_detected": len(all_tracks),
    }


def get_player_pose_sequences(tracking_result: dict) -> dict:
    """
    Extract per-player pose sequences from tracking result.
    Returns {track_id: np.ndarray (T, 17, 3)} — ready for biomechanics.
    """
    sequences = {}
    for tid, frames in tracking_result["tracks"].items():
        kp_list = [f["keypoints"] for f in frames if f["keypoints"] is not None]
        if len(kp_list) >= 5:
            sequences[tid] = np.array(kp_list, dtype=np.float32)  # (T, 17, 3)
    return sequences
