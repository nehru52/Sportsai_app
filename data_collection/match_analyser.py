"""
Match Analyser — full match video analysis with per-player tracking.

Handles both modes:
  - Training Mode: short clip, single player, deep biomechanics (existing)
  - Match Mode: full match video, all players tracked, per-player reports

Key optimisations vs naive approach:
  1. Frame sampling — process 1 in SAMPLE_RATE frames (80% compute reduction)
  2. ByteTrack via Ultralytics — persistent player IDs across the full video
  3. Per-player action spotting — VolleyVision on each player's crop
  4. Clip extraction — only run deep pipeline on detected technique windows
  5. Per-player accumulation — group results by track_id

Architecture:
  Full video → [Frame sampler] → [ByteTrack] → [Action spotter per player]
  → [Clip extractor] → [Existing smart_analyser per clip] → [Per-player report]
"""
import os
import cv2
import numpy as np
import tempfile
from collections import defaultdict

BASE_DIR    = "C:/sportsai-backend"
SAMPLE_RATE = 2      # process 1 in 2 frames for match videos (15fps from 30fps) - ACCURATE
MIN_TRACK_FRAMES = 15  # ignore players seen for fewer than this many frames
CLIP_PADDING_SEC = 1.5  # seconds before/after detected action
MAX_TECHNIQUES_PER_PLAYER = 3  # limit techniques analyzed per player


def analyse_match(
    video_path: str,
    mode: str = "auto",   # "auto" | "match" | "training"
    athlete_id: str | None = None,
) -> dict:
    """
    Unified entry point for both training clips and full match videos.

    mode="auto"     → detects based on video duration (<60s = training, >60s = match)
    mode="training" → single player, full biomechanics, existing pipeline
    mode="match"    → all players, per-player reports, frame sampling

    Returns:
        {
            "mode": "training" | "match",
            "players": {track_id: {reports, coaching}},  # match mode
            "result": {...},   # training mode (existing smart_analyser output)
            "timeline": [...],
            "summary": {...},
        }
    """
    import cv2 as _cv2
    cap = _cv2.VideoCapture(video_path)
    fps = cap.get(_cv2.CAP_PROP_FPS) or 30.0
    total_frames = int(cap.get(_cv2.CAP_PROP_FRAME_COUNT))
    duration_sec = total_frames / fps
    cap.release()

    if mode == "auto":
        mode = "match" if duration_sec > 60 else "training"

    if mode == "training":
        from smart_analyser import analyse_video_auto
        result = analyse_video_auto(video_path, athlete_id=athlete_id)
        return {"mode": "training", "result": result, "duration_sec": round(duration_sec, 1)}

    return _analyse_match_mode(video_path, fps, total_frames, duration_sec, athlete_id)


def _analyse_match_mode(
    video_path: str,
    fps: float,
    total_frames: int,
    duration_sec: float,
    athlete_id: str | None,
) -> dict:
    """Full match analysis — all players, frame sampling, per-player reports."""
    from pose_extractor import _get_yolo, _DEVICE
    from action_localiser import extract_clip
    from smart_analyser import analyse_video_auto
    from video_quality import check_video_quality

    # Quick quality check (no person check — match videos have many people)
    quality = check_video_quality(video_path, run_person_check=False)

    yolo = _get_yolo()
    cap  = cv2.VideoCapture(video_path)

    # Rally detection: skip frames where no one is moving (timeouts, breaks)
    rally_active = False
    frames_since_movement = 0
    MOVEMENT_THRESHOLD = 3  # consecutive frames with movement to start rally
    STILLNESS_THRESHOLD = 15  # consecutive frames without movement to end rally

    # Per-player data: track_id → list of frame detections
    player_frames: dict[int, list] = defaultdict(list)
    frame_idx = 0
    processed_frames = 0
    skipped_frames = 0

    print(f"[match_analyser] Scanning {duration_sec:.0f}s video with rally detection...")

    prev_positions = {}  # track_id → last position for movement detection

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        # Frame sampling — skip most frames
        if frame_idx % SAMPLE_RATE == 0:
            results = yolo.track(
                frame,
                persist=True,
                conf=0.4,
                verbose=False,
                device=_DEVICE,
            )
            
            movement_detected = False
            
            if results and results[0].boxes is not None and results[0].boxes.id is not None:
                boxes = results[0].boxes
                kps   = results[0].keypoints

                # Check for movement across all players
                for i, track_id in enumerate(boxes.id.int().tolist()):
                    curr_pos = boxes.xywh[i].cpu().numpy()[:2]  # x, y center
                    
                    if track_id in prev_positions:
                        # Calculate movement distance
                        prev_pos = prev_positions[track_id]
                        movement = np.linalg.norm(curr_pos - prev_pos)
                        if movement > 10:  # pixels - significant movement
                            movement_detected = True
                    
                    prev_positions[track_id] = curr_pos

                # Rally state machine
                if movement_detected:
                    frames_since_movement = 0
                    if not rally_active:
                        MOVEMENT_THRESHOLD -= 1
                        if MOVEMENT_THRESHOLD <= 0:
                            rally_active = True
                            MOVEMENT_THRESHOLD = 3
                            print(f"[match_analyser] Rally started at {frame_idx/fps:.1f}s")
                else:
                    frames_since_movement += 1
                    if rally_active and frames_since_movement >= STILLNESS_THRESHOLD:
                        rally_active = False
                        frames_since_movement = 0
                        print(f"[match_analyser] Rally ended at {frame_idx/fps:.1f}s")

                # Only process frames during active rallies
                if rally_active:
                    processed_frames += 1
                    for i, track_id in enumerate(boxes.id.int().tolist()):
                        if kps is not None and i < len(kps.data):
                            player_frames[track_id].append({
                                "frame":     frame_idx,
                                "time_sec":  frame_idx / fps,
                                "bbox":      boxes.xywh[i].cpu().numpy().tolist(),
                                "keypoints": kps.data[i].cpu().numpy(),  # (17, 3)
                            })
                else:
                    skipped_frames += 1

        frame_idx += 1

    cap.release()

    print(f"[match_analyser] Processed {processed_frames} rally frames, skipped {skipped_frames} dead frames")
    print(f"[match_analyser] Time saved: {skipped_frames * SAMPLE_RATE / fps / 60:.1f} minutes")

    # Filter out players seen too briefly
    active_players = {
        tid: frames for tid, frames in player_frames.items()
        if len(frames) >= MIN_TRACK_FRAMES
    }

    print(f"[match_analyser] Found {len(active_players)} active players")

    # For each player, detect technique windows and run biomechanics
    player_reports = {}
    timeline = []

    for track_id, frames in active_players.items():
        print(f"[match_analyser] Analysing player {track_id}...")
        player_result = _analyse_player(
            video_path, track_id, frames, fps, total_frames
        )
        if player_result:
            player_reports[str(track_id)] = player_result
            for seg in player_result.get("segments", []):
                timeline.append({
                    "player_id": track_id,
                    "technique": seg["technique"],
                    "start_time": seg.get("start_time"),
                    "end_time":   seg.get("end_time"),
                })

    # Sort timeline by start time
    timeline.sort(key=lambda x: x.get("start_time") or "")

    summary = _build_match_summary(player_reports, duration_sec)
    summary["rally_frames_processed"] = processed_frames
    summary["dead_frames_skipped"] = skipped_frames
    summary["time_saved_minutes"] = round(skipped_frames * SAMPLE_RATE / fps / 60, 1)

    return {
        "mode":         "match",
        "duration_sec": round(duration_sec, 1),
        "players_detected": len(active_players),
        "players":      player_reports,
        "timeline":     timeline,
        "summary":      summary,
        "quality":      quality.to_dict(),
    }


def _analyse_player(
    video_path: str,
    track_id: int,
    frames: list,
    fps: float,
    total_frames: int,
) -> dict | None:
    """
    For one tracked player: detect their technique windows and run biomechanics.
    Uses the existing smart_analyser pipeline on extracted clips.
    """
    from action_localiser import extract_clip
    from smart_analyser import analyse_video_auto

    if not frames:
        return None

    # Find frames where this player is most active (high joint velocity)
    # Use wrist height as proxy for technique detection
    technique_windows = _detect_player_techniques(frames, fps)

    if not technique_windows:
        return {"player_id": track_id, "segments": [], "techniques_detected": []}

    segments = []
    for window in technique_windows[:MAX_TECHNIQUES_PER_PLAYER]:   # configurable limit
        start_frame = max(0, window["start_frame"] - int(CLIP_PADDING_SEC * fps))
        end_frame   = min(total_frames - 1, window["end_frame"] + int(CLIP_PADDING_SEC * fps))

        tmp_clip = tempfile.mktemp(suffix=".mp4")
        try:
            extract_clip(video_path, start_frame, end_frame, tmp_clip)
            result = analyse_video_auto(tmp_clip, athlete_id=None)

            if result.get("segments"):
                for seg in result["segments"]:
                    if seg.get("analysis"):
                        seg["player_id"]   = track_id
                        seg["match_start"] = round(start_frame / fps, 2)
                        segments.append(seg)
        except Exception as e:
            print(f"[match_analyser] Player {track_id} clip failed: {e}")
        finally:
            if os.path.exists(tmp_clip):
                os.remove(tmp_clip)

    return {
        "player_id":          track_id,
        "segments":           segments,
        "techniques_detected": list({s["technique"] for s in segments}),
        "total_techniques":   len(segments),
    }


def _detect_player_techniques(frames: list, fps: float) -> list:
    """
    Find frames where this player is performing a technique.
    Uses wrist height (spike/serve) and hip drop (dig) as signals.
    Returns list of {start_frame, end_frame, technique_hint} dicts.
    """
    if len(frames) < 5:
        return []

    windows = []
    kp_list = [f["keypoints"] for f in frames if f["keypoints"] is not None]
    if len(kp_list) < 5:
        return []

    kp_arr = np.array(kp_list)   # (N, 17, 3)

    # Wrist Y velocity — high = arm moving fast = technique happening
    wrist_y = np.minimum(kp_arr[:, 9, 1], kp_arr[:, 10, 1])
    wrist_vel = np.abs(np.diff(wrist_y))

    threshold = np.percentile(wrist_vel, 80)
    in_window = False
    win_start = 0

    for i, vel in enumerate(wrist_vel):
        if vel > threshold and not in_window:
            in_window = True
            win_start = i
        elif vel <= threshold * 0.3 and in_window:
            in_window = False
            if i - win_start >= 3:
                start_f = frames[win_start]["frame"]
                end_f   = frames[min(i, len(frames)-1)]["frame"]
                windows.append({"start_frame": start_f, "end_frame": end_f})

    if in_window and len(frames) - win_start >= 3:
        windows.append({
            "start_frame": frames[win_start]["frame"],
            "end_frame":   frames[-1]["frame"],
        })

    return windows


def _build_match_summary(player_reports: dict, duration_sec: float) -> dict:
    """Build overall match summary across all players."""
    all_techniques = []
    player_verdicts = {}

    for pid, report in player_reports.items():
        for seg in report.get("segments", []):
            if seg.get("analysis"):
                all_techniques.append(seg["technique"])
                v = seg["analysis"].get("verdict", "")
                if pid not in player_verdicts or v == "ELITE":
                    player_verdicts[pid] = v

    from collections import Counter
    tech_counts = Counter(all_techniques)

    return {
        "duration_sec":        round(duration_sec, 1),
        "players_analysed":    len(player_reports),
        "technique_counts":    dict(tech_counts),
        "player_verdicts":     player_verdicts,
        "total_techniques":    len(all_techniques),
    }
