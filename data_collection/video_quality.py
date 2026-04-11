"""
Video Quality Gate — runs before pose extraction.

Checks three signals:
  1. Blur score     — Laplacian variance, <100 = too blurry
  2. Brightness     — mean pixel value, <40 = too dark, >220 = overexposed
  3. Resolution     — minimum 480p height required
  4. Duration       — minimum 0.5s, maximum 5 minutes
  5. Person visible — YOLO quick-check on sampled frames

Returns a structured QualityReport so the API can give the user
a specific, actionable error instead of a silent crash.
"""
import cv2
import numpy as np
from dataclasses import dataclass, field

# Thresholds
MIN_BLUR        = 80.0    # Laplacian variance
MIN_BRIGHTNESS  = 35.0
MAX_BRIGHTNESS  = 225.0
MIN_HEIGHT      = 480
MIN_FRAMES      = 15      # ~0.5s at 30fps
MAX_FRAMES      = 9000    # 5 minutes at 30fps
MIN_PERSON_CONF = 0.50    # lower than pose threshold — just checking visibility
SAMPLE_FRAMES   = 12      # frames to sample for quality checks


@dataclass
class QualityReport:
    ok: bool
    issues: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    # Measured values (useful for debugging / frontend display)
    avg_blur: float = 0.0
    avg_brightness: float = 0.0
    resolution: str = ""
    duration_sec: float = 0.0
    person_visible_pct: float = 0.0
    recommendations: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "ok":                  self.ok,
            "issues":              self.issues,
            "warnings":            self.warnings,
            "recommendations":     self.recommendations,
            "measured": {
                "avg_blur_score":      round(self.avg_blur, 1),
                "avg_brightness":      round(self.avg_brightness, 1),
                "resolution":          self.resolution,
                "duration_sec":        round(self.duration_sec, 1),
                "person_visible_pct":  round(self.person_visible_pct * 100, 1),
            },
        }


def check_video_quality(video_path: str, run_person_check: bool = True) -> QualityReport:
    """
    Full quality gate. Returns QualityReport with ok=True if safe to process.

    Args:
        video_path:        path to video file
        run_person_check:  set False to skip YOLO person check (faster, less accurate)
    """
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        return QualityReport(
            ok=False,
            issues=["Cannot open video file — file may be corrupt or unsupported format"],
            recommendations=["Re-export as MP4 (H.264) and try again"],
        )

    fps        = cap.get(cv2.CAP_PROP_FPS) or 30.0
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    width      = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height     = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    duration   = total_frames / fps

    issues      = []
    warnings    = []
    recs        = []
    blur_scores = []
    brightness_scores = []

    # ── Resolution check ──────────────────────────────────────────────────────
    if height < MIN_HEIGHT:
        issues.append(f"Resolution too low: {width}x{height} (minimum 480p height required)")
        recs.append("Record at 720p or higher for accurate pose detection")

    # ── Duration check ────────────────────────────────────────────────────────
    if total_frames < MIN_FRAMES:
        issues.append(f"Video too short: {duration:.1f}s — need at least 0.5s")
        recs.append("Record the full movement including approach and follow-through")
    elif total_frames > MAX_FRAMES:
        warnings.append(f"Long video ({duration:.0f}s) — analysis may take several minutes")

    # ── Sample frames for blur + brightness ───────────────────────────────────
    sample_indices = np.linspace(0, max(total_frames - 1, 0), SAMPLE_FRAMES, dtype=int)
    sampled_frames = []

    for idx in sample_indices:
        cap.set(cv2.CAP_PROP_POS_FRAMES, int(idx))
        ret, frame = cap.read()
        if not ret:
            continue
        sampled_frames.append(frame)

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        # Blur: Laplacian variance
        blur = cv2.Laplacian(gray, cv2.CV_64F).var()
        blur_scores.append(blur)

        # Brightness: mean pixel value
        brightness = float(gray.mean())
        brightness_scores.append(brightness)

    cap.release()

    avg_blur       = float(np.mean(blur_scores))       if blur_scores       else 0.0
    avg_brightness = float(np.mean(brightness_scores)) if brightness_scores else 0.0

    # ── Blur check ────────────────────────────────────────────────────────────
    if avg_blur < MIN_BLUR:
        if avg_blur < 40:
            issues.append(f"Video is too blurry (blur score: {avg_blur:.0f}, need >{MIN_BLUR})")
            recs.append("Hold the camera steady or use a tripod — motion blur destroys joint detection")
        else:
            warnings.append(f"Video is slightly blurry (score: {avg_blur:.0f}) — results may be less accurate")
            recs.append("A steadier camera angle will improve accuracy")

    # ── Brightness check ──────────────────────────────────────────────────────
    if avg_brightness < MIN_BRIGHTNESS:
        issues.append(f"Video is too dark (brightness: {avg_brightness:.0f}, need >{MIN_BRIGHTNESS})")
        recs.append("Record in better lighting — the athlete's full body must be clearly visible")
    elif avg_brightness > MAX_BRIGHTNESS:
        warnings.append(f"Video may be overexposed (brightness: {avg_brightness:.0f})")
        recs.append("Avoid recording directly into bright light or sunlight behind the athlete")

    # ── Person visibility check (YOLO quick pass) ─────────────────────────────
    person_visible_pct = 0.0
    if run_person_check and sampled_frames and not issues:
        # Only run if no hard issues yet — saves time
        person_visible_pct = _check_person_visible(sampled_frames)
        if person_visible_pct < 0.5:
            issues.append(
                f"Athlete not clearly visible in {person_visible_pct*100:.0f}% of frames "
                f"(need >50%) — check framing and occlusion"
            )
            recs.append("Frame the athlete's full body in the shot — head to feet must be visible")
        elif person_visible_pct < 0.75:
            warnings.append(
                f"Athlete partially visible in some frames ({person_visible_pct*100:.0f}% detection rate) "
                f"— accuracy may be reduced"
            )
            recs.append("Keep the athlete fully in frame throughout the movement")

    # ── Pose tracking stability check ─────────────────────────────────────────
    # Check for extreme joint jumps in sampled frames (tracking instability)
    # Only if we have enough frames and no hard issues
    if not issues and len(sampled_frames) >= 4:
        stability_warning = _check_tracking_stability(sampled_frames)
        if stability_warning:
            warnings.append(stability_warning)
            recs.append("A fixed camera angle (side-on, 10-15m from athlete) gives the most stable tracking")

    ok = len(issues) == 0

    return QualityReport(
        ok=ok,
        issues=issues,
        warnings=warnings,
        recommendations=list(dict.fromkeys(recs)),   # deduplicate
        avg_blur=avg_blur,
        avg_brightness=avg_brightness,
        resolution=f"{width}x{height}",
        duration_sec=duration,
        person_visible_pct=person_visible_pct,
    )


def _check_person_visible(frames: list) -> float:
    """Quick YOLO person detection on sampled frames. Returns fraction visible."""
    try:
        from ultralytics import YOLO
        import os
        model_path = os.path.join(os.path.dirname(__file__), "yolo11x-pose.pt")
        model = YOLO(model_path)
        detected = 0
        for frame in frames:
            results = model(frame, verbose=False)
            if results and results[0].keypoints is not None:
                kps = results[0].keypoints
                if kps.conf is not None and len(kps.conf) > 0:
                    if float(kps.conf.mean()) > MIN_PERSON_CONF:
                        detected += 1
        return detected / len(frames)
    except Exception:
        return 1.0   # if check fails, don't block — let pose extractor handle it


def _check_tracking_stability(frames: list) -> str | None:
    """
    Run YOLO on a few frames and check if keypoints are stable between them.
    Returns a warning string if unstable, None if ok.
    """
    try:
        from ultralytics import YOLO
        import os
        model_path = os.path.join(os.path.dirname(__file__), "yolo11x-pose.pt")
        model = YOLO(model_path)
        keypoints_list = []
        for frame in frames[:6]:
            results = model(frame, verbose=False)
            if results and results[0].keypoints is not None:
                kps = results[0].keypoints
                if kps.conf is not None and len(kps.conf) > 0:
                    best = int(kps.conf.mean(dim=1).argmax())
                    xy = kps.xy[best].cpu().numpy()
                    keypoints_list.append(xy)

        if len(keypoints_list) < 2:
            return None

        # Check for large jumps in hip position between consecutive detections
        jumps = []
        for i in range(1, len(keypoints_list)):
            hip_prev = keypoints_list[i - 1][11]
            hip_curr = keypoints_list[i][11]
            jump = float(np.linalg.norm(hip_curr - hip_prev))
            jumps.append(jump)

        avg_jump = np.mean(jumps)
        if avg_jump > 150:   # pixels — large jump = camera moving or tracking lost
            return f"Camera appears to be moving or tracking is unstable (avg joint jump: {avg_jump:.0f}px)"
        return None
    except Exception:
        return None
