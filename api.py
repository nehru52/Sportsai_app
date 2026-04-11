import os
import json
import shutil
import sys
import tempfile
from typing import Optional

from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, File, HTTPException, UploadFile, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

sys.path.insert(0, "C:/sportsai-backend/data_collection")
from analyser import TECHNIQUE_CONFIG, analyse_biomechanics, load_thresholds
from pose_extractor import extract_pose
from action_detector import detect_actions
from court_detector import detect_court_in_video
from player_tracker import track_players
from ball_tracker import track_ball
from coach_feedback import generate_feedback
from progress_tracker import save_session, get_progress_report, load_history
from skeleton_overlay import render_annotated_video, render_side_by_side, render_coaching_video
from reference_library import get_elite_sequence
from phase_detector import detect_phases
from video_quality import check_video_quality
from visualiser import render_heatmap, render_pose_chart, render_tracking_video
from action_localiser import localise_technique, extract_clip
from smart_analyser import analyse_video_auto
from job_queue import create_job, get_job, start_job

app = FastAPI(title="SportsAI Volleyball Analysis API — Olympic Grade")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_methods=["*"], allow_headers=["*"],
    expose_headers=[
        "X-Verdict","X-Score","X-Technique","X-Peak-Frame","X-Focus",
        "X-Headline","X-Timeline","X-Summary","X-Phases","X-Elite-Clips",
        "X-Players-Detected","X-Total-Frames",
    ]
)

_thresholds: dict = {t: load_thresholds(t) for t in TECHNIQUE_CONFIG}


# ── helpers ───────────────────────────────────────────────────────────────────

def _verdict(report: dict) -> str:
    good  = sum(1 for r in report.values() if r["status"] == "GOOD")
    total = len(report)
    if good == total:        return "ELITE"
    if good >= total * 0.6:  return "GOOD"
    return "NEEDS WORK"


def _save_upload(video: UploadFile) -> str:
    suffix = os.path.splitext(video.filename)[-1] or ".mp4"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        shutil.copyfileobj(video.file, tmp)
        return tmp.name


def _handle_error(e: Exception):
    msg = str(e)
    if msg.startswith("VIDEO_QUALITY_FAIL:"):
        quality_data = json.loads(msg[len("VIDEO_QUALITY_FAIL:"):])
        raise HTTPException(422, detail={"error": "video_quality_insufficient", "quality": quality_data})
    raise HTTPException(422, detail={"error": str(e)})


def _best_segment(segments: list) -> dict | None:
    analysed = [s for s in segments if s.get("analysis")]
    if not analysed:
        return None
    return max(analysed, key=lambda s: (
        len(s["analysis"].get("metrics", {})),
        s["analysis"].get("confidence", 0),
    ))


def _extract_pose_for_render(video_path: str, technique: str) -> dict:
    """Extract pose for rendering — one pose per video frame, person locked, returns 2D coords."""
    import cv2 as _cv2
    import numpy as _np
    from pose_extractor import _get_yolo, _extract_biomechanics, _select_person, CONFIDENCE_THRESHOLD
    from pose_3d_lifter import lift_to_3d

    yolo  = _get_yolo()
    cap   = _cv2.VideoCapture(video_path)
    fps   = cap.get(_cv2.CAP_PROP_FPS) or 30.0
    img_w = int(cap.get(_cv2.CAP_PROP_FRAME_WIDTH))
    img_h = int(cap.get(_cv2.CAP_PROP_FRAME_HEIGHT))
    total = int(cap.get(_cv2.CAP_PROP_FRAME_COUNT))

    raw_poses  = [None] * total
    raw_confs  = [None] * total
    frame_idx  = 0
    confidences = []
    locked_centre = None
    LOCK_AFTER = 3
    locked_count = 0

    while True:
        ret, frame = cap.read()
        if not ret:
            break
        results = yolo(frame, verbose=False)
        if results and results[0].keypoints is not None:
            kps   = results[0].keypoints
            boxes = results[0].boxes
            if kps.conf is not None and len(kps.conf) > 0:
                best = _select_person(results, technique, img_h, locked_centre)
                conf = float(kps.conf[best].mean())
                if conf >= CONFIDENCE_THRESHOLD:
                    raw_poses[frame_idx] = kps.xy[best].cpu().numpy()
                    raw_confs[frame_idx] = kps.conf[best].cpu().numpy()
                    confidences.append(conf)
                    locked_count += 1
                    if locked_centre is None and locked_count >= LOCK_AFTER:
                        if boxes is not None and boxes.xywh is not None and best < len(boxes.xywh):
                            locked_centre = (float(boxes.xywh[best, 0]), float(boxes.xywh[best, 1]))
        frame_idx += 1
    cap.release()

    # Fill gaps
    last = None
    for i in range(total):
        if raw_poses[i] is not None: last = i
        elif last is not None: raw_poses[i] = raw_poses[last]; raw_confs[i] = raw_confs[last]
    last = None
    for i in range(total - 1, -1, -1):
        if raw_poses[i] is not None: last = i
        elif last is not None: raw_poses[i] = raw_poses[last]; raw_confs[i] = raw_confs[last]

    valid = [(p, c) for p, c in zip(raw_poses, raw_confs) if p is not None]
    if len(valid) < 5:
        raise ValueError("Too few valid pose frames for rendering")

    pose2d   = _np.array([p for p, _ in valid])
    kp_confs = _np.array([c for _, c in valid])
    pose_seq = lift_to_3d(pose2d, img_w, img_h, kp_confs)

    return {
        "pose_sequence_3d":   pose_seq,
        "pose_sequence_2d":   pose2d,
        "biomechanics":       _extract_biomechanics(pose_seq, technique, fps),
        "average_confidence": round(float(_np.mean(confidences)) if confidences else 0.0, 4),
        "total_frames":       total,
    }


# ── endpoints ─────────────────────────────────────────────────────────────────

@app.get("/")
def root():
    return {"status": "ok", "message": "SportsAI Volleyball Analysis API — Olympic Grade"}


@app.post("/analyse/auto/async")
async def analyse_auto_async(
    video: UploadFile = File(...),
    athlete_id: Optional[str] = Query(None),
    technique: Optional[str] = Query(None, description="spike | serve | block | dig | auto"),
):
    """
    Async analysis endpoint - returns immediately with job_id.
    Use /job/{job_id} to check status and get results.
    """
    tmp_path = _save_upload(video)
    job_id = create_job(tmp_path, technique or "auto", athlete_id)
    start_job(job_id)
    
    return {
        "job_id": job_id,
        "status": "processing",
        "message": "Analysis started. Poll /job/{job_id} for results."
    }


@app.get("/job/{job_id}")
def get_job_status(job_id: str):
    """Get job status and results."""
    job = get_job(job_id)
    if job["status"] == "not_found":
        raise HTTPException(404, "Job not found")
    
    return job


@app.post("/check-video")
async def check_video(video: UploadFile = File(...)):
    tmp_path = _save_upload(video)
    try:
        return check_video_quality(tmp_path).to_dict()
    finally:
        os.remove(tmp_path)


@app.post("/localise")
async def localise_action(video: UploadFile = File(...), technique: str = Query("spike")):
    tmp_path = _save_upload(video)
    try:
        return localise_technique(tmp_path, technique)
    except Exception as e:
        _handle_error(e)
    finally:
        os.remove(tmp_path)


@app.post("/analyse/auto")
async def analyse_auto(
    video: UploadFile = File(...),
    athlete_id: Optional[str] = Query(None),
    output: str = Query("json", description="json | video | both"),
):
    """
    Main endpoint. Upload any volleyball video — no technique hint needed.
    output=json  → full JSON analysis
    output=video → annotated MP4
    output=both  → MP4 with JSON in headers
    """
    tmp_path = _save_upload(video)
    output_dir = "C:/sportsai-backend/data/annotated_videos"
    os.makedirs(output_dir, exist_ok=True)

    try:
        result = analyse_video_auto(tmp_path, athlete_id=athlete_id)

        if output == "json":
            return result

        if result.get("bad_video_advice") or not result.get("segments"):
            return result

        best_seg = _best_segment(result["segments"])
        if not best_seg or not best_seg.get("analysis"):
            return result

        technique   = best_seg["technique"]
        start_frame = best_seg["start_frame"]
        end_frame   = best_seg["end_frame"]

        stem      = os.path.splitext(os.path.basename(tmp_path))[0]
        clip_path = os.path.join(output_dir, f"clip_{stem}.mp4")
        out_path  = os.path.join(output_dir, f"auto_{stem}.mp4")

        extract_clip(tmp_path, start_frame, end_frame, clip_path)

        import cv2 as _cv2
        cap = _cv2.VideoCapture(clip_path)
        clip_frames = int(cap.get(_cv2.CAP_PROP_FRAME_COUNT))
        cap.release()

        pose_result = _extract_pose_for_render(clip_path, technique)
        report      = best_seg["analysis"]["metrics"]
        feedback    = best_seg["analysis"]["coaching"]

        render_result = render_coaching_video(
            input_video_path=clip_path,
            output_video_path=out_path,
            pose_seq=pose_result["pose_sequence_3d"],
            report=report,
            feedback=feedback,
            total_video_frames=clip_frames,
            pose_seq_2d=pose_result["pose_sequence_2d"],
        )

        if os.path.exists(clip_path):
            os.remove(clip_path)

        summary = result.get("summary", {})
        verdict = best_seg["analysis"]["verdict"]
        score   = best_seg["analysis"]["score"]

        headers = {
            "X-Verdict":    verdict,
            "X-Score":      score,
            "X-Technique":  technique,
            "X-Peak-Frame": str(render_result["peak_frame"]),
            "X-Focus":      feedback.get("next_session_focus", ""),
            "X-Headline":   feedback.get("headline", ""),
        }

        if output == "both":
            headers["X-Timeline"] = json.dumps([
                {"technique": s["technique"], "start": s["start_time"], "end": s["end_time"]}
                for s in result.get("timeline", [])
            ])
            headers["X-Summary"] = json.dumps({
                "overall_verdict": summary.get("overall_verdict"),
                "top_priority":    summary.get("top_priority"),
                "top_strength":    summary.get("top_strength"),
                "score":           f"{summary.get('metrics_good')}/{summary.get('metrics_total')}",
            })

        return FileResponse(out_path, media_type="video/mp4",
                            filename=f"sportsai_{technique}_analysis.mp4",
                            headers=headers)

    except Exception as e:
        _handle_error(e)
    finally:
        os.remove(tmp_path)


@app.post("/analyse/{technique}")
async def analyse_technique(
    technique: str,
    video: UploadFile = File(...),
    athlete_id: Optional[str] = Query(None),
    ai_feedback: bool = Query(False),
):
    if technique not in TECHNIQUE_CONFIG:
        raise HTTPException(404, f"Unknown technique '{technique}'")
    tmp_path = _save_upload(video)
    try:
        result  = extract_pose(tmp_path, technique)
        report  = analyse_biomechanics(result["biomechanics"], _thresholds[technique], technique)
        good    = sum(1 for r in report.values() if r["status"] == "GOOD")
        verdict = _verdict(report)
        response = {
            "verdict": verdict, "score": f"{good}/{len(report)}",
            "metrics": report, "frames_analysed": len(result["pose_sequence_3d"]),
            "confidence": result["average_confidence"],
            "localisation": result.get("localisation"),
        }
        if athlete_id:
            save_session(athlete_id, technique, response)
            history = get_progress_report(athlete_id, technique)
            response["progress"] = {"sessions_total": history["sessions_total"],
                                    "trends": history.get("trends", {}),
                                    "injury_risk": history.get("injury_risk", [])}
        if ai_feedback:
            history_data = load_history(athlete_id, technique) if athlete_id else None
            response["coaching"] = generate_feedback(technique, report, verdict, history_data)
        return response
    except Exception as e:
        _handle_error(e)
    finally:
        os.remove(tmp_path)


@app.post("/analyse/action")
async def analyse_action(video: UploadFile = File(...)):
    tmp_path = _save_upload(video)
    try:
        return detect_actions(tmp_path)
    except Exception as e:
        _handle_error(e)
    finally:
        os.remove(tmp_path)


@app.post("/analyse/court")
async def analyse_court(video: UploadFile = File(...)):
    tmp_path = _save_upload(video)
    try:
        return detect_court_in_video(tmp_path)
    except Exception as e:
        _handle_error(e)
    finally:
        os.remove(tmp_path)


@app.post("/analyse/players")
async def analyse_players(video: UploadFile = File(...)):
    tmp_path = _save_upload(video)
    try:
        result = track_players(tmp_path)
        return {"total_frames": result["total_frames"],
                "players_detected": result["players_detected"],
                "track_lengths": {tid: len(frames) for tid, frames in result["tracks"].items()}}
    except Exception as e:
        _handle_error(e)
    finally:
        os.remove(tmp_path)


@app.post("/analyse/ball")
async def analyse_ball(video: UploadFile = File(...)):
    tmp_path = _save_upload(video)
    try:
        result = track_ball(tmp_path)
        return {"rallies": result["rallies"], "total_rallies": len(result["rallies"]),
                "detection_rate": result["detection_rate"], "total_frames": result["total_frames"]}
    except Exception as e:
        _handle_error(e)
    finally:
        os.remove(tmp_path)


@app.post("/analyse/full")
async def analyse_full(
    video: UploadFile = File(...),
    technique: str = Query("spike"),
    athlete_id: Optional[str] = Query(None),
    ai_feedback: bool = Query(False),
):
    if technique not in TECHNIQUE_CONFIG:
        raise HTTPException(404, f"Unknown technique '{technique}'")
    tmp_path = _save_upload(video)
    try:
        pose_result = extract_pose(tmp_path, technique)
        report      = analyse_biomechanics(pose_result["biomechanics"], _thresholds[technique], technique)
        good        = sum(1 for r in report.values() if r["status"] == "GOOD")
        verdict     = _verdict(report)
        actions     = detect_actions(tmp_path)
        players     = track_players(tmp_path)
        ball        = track_ball(tmp_path)
        court       = detect_court_in_video(tmp_path)
        response = {
            "technique": technique, "verdict": verdict, "score": f"{good}/{len(report)}",
            "metrics": report, "confidence": pose_result["average_confidence"],
            "actions": actions, "court": court,
            "players": {"total_frames": players["total_frames"], "players_detected": players["players_detected"]},
            "ball": {"rallies": ball["rallies"], "total_rallies": len(ball["rallies"]), "detection_rate": ball["detection_rate"]},
        }
        if athlete_id:
            save_session(athlete_id, technique, {"verdict": verdict, "score": f"{good}/{len(report)}", "metrics": report})
            history = get_progress_report(athlete_id, technique)
            response["progress"] = {"sessions_total": history["sessions_total"], "trends": history.get("trends", {})}
        if ai_feedback:
            history_data = load_history(athlete_id, technique) if athlete_id else None
            response["coaching"] = generate_feedback(technique, report, verdict, history_data)
        return response
    except Exception as e:
        _handle_error(e)
    finally:
        os.remove(tmp_path)


@app.get("/progress/{athlete_id}/{technique}")
async def get_progress(athlete_id: str, technique: str):
    if technique not in TECHNIQUE_CONFIG:
        raise HTTPException(404, f"Unknown technique '{technique}'")
    return get_progress_report(athlete_id, technique)


@app.post("/visualise/heatmap")
async def visualise_heatmap(video: UploadFile = File(...)):
    tmp_path = _save_upload(video)
    out_path = f"C:/sportsai-backend/data/annotated_videos/heatmap_{os.path.basename(tmp_path)}.png"
    try:
        tracking = track_players(tmp_path)
        import cv2 as _cv2
        cap = _cv2.VideoCapture(tmp_path)
        tracking["img_w"] = int(cap.get(_cv2.CAP_PROP_FRAME_WIDTH))
        tracking["img_h"] = int(cap.get(_cv2.CAP_PROP_FRAME_HEIGHT))
        cap.release()
        render_heatmap(tracking, out_path)
        return FileResponse(out_path, media_type="image/png", filename="sportsai_heatmap.png")
    except Exception as e:
        _handle_error(e)
    finally:
        os.remove(tmp_path)


@app.post("/visualise/pose-chart")
async def visualise_pose_chart(video: UploadFile = File(...), technique: str = Query("spike")):
    if technique not in TECHNIQUE_CONFIG:
        raise HTTPException(404, f"Unknown technique '{technique}'")
    tmp_path = _save_upload(video)
    out_path = f"C:/sportsai-backend/data/annotated_videos/posechart_{os.path.basename(tmp_path)}.png"
    try:
        result = extract_pose(tmp_path, technique)
        report = analyse_biomechanics(result["biomechanics"], _thresholds[technique], technique)
        render_pose_chart(result["pose_sequence_3d"], result["biomechanics"], report, technique, out_path)
        return FileResponse(out_path, media_type="image/png", filename=f"sportsai_{technique}_pose_chart.png")
    except Exception as e:
        _handle_error(e)
    finally:
        os.remove(tmp_path)


@app.post("/visualise/tracking")
async def visualise_tracking(video: UploadFile = File(...)):
    tmp_path = _save_upload(video)
    out_path = f"C:/sportsai-backend/data/annotated_videos/tracking_{os.path.basename(tmp_path)}.mp4"
    try:
        tracking = track_players(tmp_path)
        render_tracking_video(tmp_path, tracking, out_path)
        return FileResponse(out_path, media_type="video/mp4", filename="sportsai_tracking.mp4",
                            headers={"X-Players-Detected": str(tracking["players_detected"]),
                                     "X-Total-Frames": str(tracking["total_frames"])})
    except Exception as e:
        _handle_error(e)
    finally:
        os.remove(tmp_path)
