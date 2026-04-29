"""
Skeleton overlay renderer.
Draws the athlete's 3D pose skeleton on their video frame-by-frame,
with colour-coded joints (green=good, red=needs improvement) and
a ghost overlay of the elite reference pose for direct comparison.

Output: annotated video file the user can watch and immediately understand
what their body is doing wrong vs what it should look like.
"""
import cv2
import numpy as np
import os

# COCO 17-keypoint skeleton connections
SKELETON = [
    (0, 1), (0, 2),           # nose → eyes
    (1, 3), (2, 4),           # eyes → ears
    (5, 6),                   # shoulders
    (5, 7), (7, 9),           # left arm
    (6, 8), (8, 10),          # right arm
    (5, 11), (6, 12),         # torso sides
    (11, 12),                 # hips
    (11, 13), (13, 15),       # left leg
    (12, 14), (14, 16),       # right leg
]

# Colours
GREEN  = (0, 220, 0)
RED    = (0, 60, 220)
YELLOW = (0, 200, 220)
GHOST  = (180, 180, 180)     # elite reference ghost
WHITE  = (255, 255, 255)
BLACK  = (0, 0, 0)

JOINT_RADIUS   = 5
BONE_THICKNESS = 2
GHOST_ALPHA    = 0.35        # transparency of elite ghost overlay


def _draw_skeleton(
    frame: np.ndarray,
    keypoints: np.ndarray,          # (17, 2) or (17, 3) — XY used
    bad_joints: set[int],
    color_override: tuple | None = None,
    alpha: float = 1.0,
) -> np.ndarray:
    """Draw skeleton on frame. bad_joints are drawn red."""
    overlay = frame.copy()
    kp = keypoints[:, :2].astype(int)

    for i, j in SKELETON:
        if i >= len(kp) or j >= len(kp):
            continue
        p1, p2 = tuple(kp[i]), tuple(kp[j])
        if (p1[0] == 0 and p1[1] == 0) or (p2[0] == 0 and p2[1] == 0):
            continue
        color = color_override or (RED if (i in bad_joints or j in bad_joints) else GREEN)
        cv2.line(overlay, p1, p2, color, BONE_THICKNESS)

    for idx, (x, y) in enumerate(kp):
        if x == 0 and y == 0:
            continue
        color = color_override or (RED if idx in bad_joints else GREEN)
        # Draw black outline first (larger radius)
        cv2.circle(overlay, (x, y), JOINT_RADIUS + 2, BLACK, -1)
        # Draw colored joint on top
        cv2.circle(overlay, (x, y), JOINT_RADIUS, color, -1)
        # Draw white center dot for extra visibility
        if JOINT_RADIUS >= 4:
            cv2.circle(overlay, (x, y), max(1, JOINT_RADIUS - 3), WHITE, -1)

    if alpha < 1.0:
        cv2.addWeighted(overlay, alpha, frame, 1 - alpha, 0, frame)
        return frame
    return overlay


def _bad_joints_for_metrics(bad_metrics: list[str]) -> set[int]:
    """Map metric names to the joint indices they involve."""
    METRIC_JOINTS = {
        "arm_cock_angle":    {6, 8, 10},   # right shoulder, elbow, wrist
        "jump_height":       {15, 16},     # ankles
        "approach_speed":    {11, 12},     # hips
        "contact_point":     {10, 11, 12}, # wrist + hips
        "follow_through":    {6, 8, 10},
        "toss_height":       {9, 10},      # wrists
        "shoulder_rotation": {5, 6},       # shoulders
        "wrist_snap":        {9, 10},
        "body_lean":         {0, 11, 12},  # nose + hips
        "step_timing":       {15, 16},
        "reaction_time":     {11, 12, 13, 14},
        "penultimate_step":  {13, 14, 15, 16},
        "hand_position":     {9, 10},
        "shoulder_width":    {5, 6},
        "landing_balance":   {13, 14, 15, 16},
        "platform_angle":    {7, 8, 9, 10},
        "knee_bend":         {11, 13, 15},
        "hip_drop":          {11, 12},
        "arm_extension":     {5, 7, 9},
        "recovery_position": {11, 12, 13, 14, 15, 16},
    }
    joints = set()
    for m in bad_metrics:
        joints |= METRIC_JOINTS.get(m, set())
    return joints


def _find_peak_bad_frame(
    pose_seq: np.ndarray,
    bad_metrics: list[str],
    biomechanics: dict,
) -> int:
    """
    Find the frame index where the worst biomechanics occur.
    Uses the joint with highest deviation from neutral as proxy.
    """
    if not bad_metrics or len(pose_seq) == 0:
        return len(pose_seq) // 2

    bad_joints = _bad_joints_for_metrics(bad_metrics)
    if not bad_joints:
        return len(pose_seq) // 2

    # Frame with highest joint velocity in bad joints = moment of failure
    joint_list = list(bad_joints)
    velocities = np.linalg.norm(
        np.diff(pose_seq[:, joint_list, :2], axis=0), axis=2
    ).sum(axis=1)
    return int(np.argmax(velocities))


def render_annotated_video(
    input_video_path: str,
    output_video_path: str,
    pose_seq: np.ndarray,           # (T, 17, 3)
    biomechanics: dict,
    report: dict,
    feedback: dict,
    elite_reference: np.ndarray | None = None,  # (17, 3) single elite frame
    pose_seq_2d: np.ndarray | None = None,  # (T, 17, 2) raw pixel coords for drawing
) -> dict:
    """
    Render the athlete's video with:
    - Colour-coded skeleton (green=good joints, red=problem joints)
    - Elite ghost overlay (grey skeleton showing correct position)
    - HUD: metric status panel on the right
    - Frame counter + peak moment highlight
    - Text cue at the worst frame

    Returns {"output_path": str, "peak_frame": int}
    """
    cap = cv2.VideoCapture(input_video_path)
    fps    = cap.get(cv2.CAP_PROP_FPS) or 30.0
    width  = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    # Widen frame to fit HUD panel on right
    hud_width  = 320
    out_width  = width + hud_width

    os.makedirs(os.path.dirname(output_video_path) or ".", exist_ok=True)
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(output_video_path, fourcc, fps, (out_width, height))

    bad_metrics  = [m for m, v in report.items() if v["status"] == "NEEDS IMPROVEMENT"]
    good_metrics = [m for m, v in report.items() if v["status"] == "GOOD"]
    bad_joints   = _bad_joints_for_metrics(bad_metrics)
    peak_frame   = _find_peak_bad_frame(pose_seq, bad_metrics, biomechanics)

    # Use 2D pixel coords if available (more accurate than 3D denormalized)
    draw_seq = pose_seq_2d if pose_seq_2d is not None else pose_seq

    # Build HUD image (static, drawn once)
    hud = _build_hud(report, feedback, hud_width, height)

    frame_idx = 0
    while True:
        ret, frame = cap.read()
        if not ret:
            break

        # Draw skeleton if we have pose data for this frame
        if frame_idx < len(draw_seq):
            kp = draw_seq[frame_idx]

            # Elite ghost first (behind athlete)
            if elite_reference is not None:
                frame = _draw_skeleton(frame, elite_reference, set(), color_override=GHOST, alpha=GHOST_ALPHA)

            # Athlete skeleton on top
            frame = _draw_skeleton(frame, kp, bad_joints)

            # Highlight peak bad frame
            if frame_idx == peak_frame:
                cv2.rectangle(frame, (0, 0), (width - 1, height - 1), (0, 60, 220), 4)
                cue = feedback.get("fixes", [{}])[0].get("feel_cue", "") if feedback.get("fixes") else ""
                if cue:
                    _draw_text_box(frame, f"KEY MOMENT: {cue[:60]}", (10, height - 60), RED)

        # Frame counter
        cv2.putText(frame, f"Frame {frame_idx + 1}", (10, 25),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, WHITE, 2)

        # Combine frame + HUD
        combined = np.zeros((height, out_width, 3), dtype=np.uint8)
        combined[:, :width]  = frame
        combined[:, width:]  = hud

        writer.write(combined)
        frame_idx += 1

    cap.release()
    writer.release()

    return {"output_path": output_video_path, "peak_frame": peak_frame}


def _build_hud(report: dict, feedback: dict, width: int, height: int) -> np.ndarray:
    """Build the right-side HUD panel showing metric status."""
    hud = np.zeros((height, width, 3), dtype=np.uint8)
    hud[:] = (20, 20, 20)  # dark background

    y = 20
    font = cv2.FONT_HERSHEY_SIMPLEX

    # Title
    cv2.putText(hud, "ANALYSIS", (10, y), font, 0.7, WHITE, 2)
    y += 30

    verdict = feedback.get("headline", "")[:40]
    for line in _wrap(verdict, 28):
        cv2.putText(hud, line, (10, y), font, 0.45, YELLOW, 1)
        y += 18
    y += 10

    # Metrics
    cv2.putText(hud, "METRICS", (10, y), font, 0.55, WHITE, 1)
    y += 22

    for metric, val in report.items():
        status = val["status"]
        color  = GREEN if status == "GOOD" else RED
        label  = metric.replace("_", " ").upper()[:22]
        score  = f"{val['value']:.1f}"
        cv2.putText(hud, f"{'✓' if status == 'GOOD' else '✗'} {label}", (10, y), font, 0.38, color, 1)
        cv2.putText(hud, score, (width - 45, y), font, 0.38, color, 1)
        y += 18

    y += 10

    # Next session focus
    focus = feedback.get("next_session_focus", "")
    if focus:
        cv2.putText(hud, "FOCUS NEXT SESSION:", (10, y), font, 0.42, YELLOW, 1)
        y += 18
        for line in _wrap(focus, 30):
            cv2.putText(hud, line, (10, y), font, 0.38, WHITE, 1)
            y += 16

    return hud


def _draw_text_box(frame: np.ndarray, text: str, pos: tuple, color: tuple):
    font = cv2.FONT_HERSHEY_SIMPLEX
    (tw, th), _ = cv2.getTextSize(text, font, 0.55, 1)
    x, y = pos
    cv2.rectangle(frame, (x - 4, y - th - 4), (x + tw + 4, y + 4), BLACK, -1)
    cv2.putText(frame, text, (x, y), font, 0.55, color, 1)


def _wrap(text: str, width: int) -> list[str]:
    words = text.split()
    lines, line = [], ""
    for w in words:
        if len(line) + len(w) + 1 <= width:
            line += (" " if line else "") + w
        else:
            if line:
                lines.append(line)
            line = w
    if line:
        lines.append(line)
    return lines or [""]


# ── Side-by-side comparison renderer ─────────────────────────────────────────

# Phase label colours
PHASE_COLORS = {
    "APPROACH":       (255, 200, 0),
    "TAKEOFF":        (0, 200, 255),
    "ARM_COCK":       (200, 0, 255),
    "CONTACT":        (0, 60, 220),
    "FOLLOW_THROUGH": (0, 220, 100),
    "STANCE":         (255, 200, 0),
    "TOSS":           (0, 200, 255),
    "STEP":           (200, 0, 255),
    "JUMP":           (0, 200, 255),
    "REACH":          (200, 0, 255),
    "LAND":           (0, 220, 100),
    "READY":          (255, 200, 0),
    "MOVE":           (0, 200, 255),
    "LOW_POSITION":   (200, 0, 255),
    "RECOVERY":       (0, 220, 100),
    "FULL_MOVEMENT":  (200, 200, 200),
}

DIFF_COLOR  = (0, 140, 255)   # orange arrows for joint divergence
ELITE_COLOR = (80, 220, 80)   # bright green for elite skeleton


def _project_normalised_to_canvas(
    kp_norm: np.ndarray,   # (17, 3) normalised skeleton
    canvas_w: int,
    canvas_h: int,
    scale: float = 0.55,   # increased from 0.35 — fills more of the panel
) -> np.ndarray:
    """
    Map root-centred normalised skeleton to pixel coords on a canvas.
    Root (hips) is at centre. Y is flipped so head is up.
    Scale is relative to the shorter canvas dimension.
    """
    kp = kp_norm[:, :2].copy().astype(np.float32)

    # In image coords Y increases downward, but normalised skeleton
    # has Y increasing upward (head is negative Y from root).
    # Flip Y so head appears at top of canvas.
    kp[:, 1] = -kp[:, 1]

    # Scale to fill ~55% of the panel height
    h_range = canvas_h * scale
    kp = kp * h_range

    # Centre horizontally, place root (hips) at 60% down the canvas
    # so there's room for the head above and feet below
    kp[:, 0] += canvas_w / 2
    kp[:, 1] += canvas_h * 0.55

    return kp.astype(int)


def _draw_diff_arrows(
    canvas: np.ndarray,
    athlete_kp: np.ndarray,   # (17, 2) pixel coords on canvas
    elite_kp: np.ndarray,     # (17, 2) pixel coords on canvas
    bad_joints: set[int],
    threshold: float = 15.0,  # pixels — only draw arrow if divergence > threshold
):
    """Draw orange arrows from athlete joint position to where elite joint is."""
    for idx in bad_joints:
        if idx >= len(athlete_kp) or idx >= len(elite_kp):
            continue
        a = tuple(athlete_kp[idx])
        e = tuple(elite_kp[idx])
        dist = np.linalg.norm(np.array(a) - np.array(e))
        if dist < threshold:
            continue
        cv2.arrowedLine(canvas, a, e, DIFF_COLOR, 2, tipLength=0.3)


def render_side_by_side(
    input_video_path: str,
    output_video_path: str,
    pose_seq: np.ndarray,           # (T, 17, 3) athlete — pixel space
    elite_seq: np.ndarray,          # (CANONICAL_LEN, 17, 3) normalised elite
    phases: list,                   # list of Phase from phase_detector
    biomechanics: dict,
    report: dict,
    feedback: dict,
    technique: str,
) -> dict:
    """
    Render a side-by-side comparison video:
    - LEFT panel:  athlete's actual video with colour-coded skeleton overlay
    - RIGHT panel: black background with elite reference skeleton, phase-matched
    - Phase label banner across both panels
    - Difference arrows on right panel showing joint divergence
    - HUD strip at bottom with metric status + feel cue

    Returns {"output_path": str, "peak_frame": int}
    """
    from phase_detector import map_athlete_to_elite, phase_progress as get_phase_progress
    from reference_library import _normalise_skeleton

    cap    = cv2.VideoCapture(input_video_path)
    fps    = cap.get(cv2.CAP_PROP_FPS) or 30.0
    width  = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    total_video_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

    # Output: two panels side by side + bottom HUD strip
    hud_h      = 80
    panel_w    = width
    out_w      = panel_w * 2
    out_h      = height + hud_h

    os.makedirs(os.path.dirname(output_video_path) or ".", exist_ok=True)
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(output_video_path, fourcc, fps, (out_w, out_h))

    bad_metrics  = [m for m, v in report.items() if v["status"] == "NEEDS IMPROVEMENT"]
    bad_joints   = _bad_joints_for_metrics(bad_metrics)
    peak_frame   = _find_peak_bad_frame(pose_seq, bad_metrics, biomechanics)
    elite_len    = len(elite_seq)
    n_pose_frames = len(pose_seq)

    # Map video frame index → pose frame index
    # Handles slow-mo: video may have more frames than pose detections
    def _pose_idx(vid_frame: int) -> int:
        if n_pose_frames == 0:
            return 0
        return int(np.clip(
            round(vid_frame * n_pose_frames / max(total_video_frames, 1)),
            0, n_pose_frames - 1
        ))

    # Normalise athlete pose for right-panel comparison
    athlete_norm = _normalise_skeleton(pose_seq)   # (T, 17, 3) normalised

    # Pre-build bottom HUD
    hud = _build_comparison_hud(report, feedback, out_w, hud_h)

    frame_idx = 0
    while True:
        ret, frame = cap.read()
        if not ret:
            break

        # ── LEFT PANEL: athlete video + skeleton ──────────────────────────────
        left = frame.copy()
        p_idx = _pose_idx(frame_idx)
        if p_idx < n_pose_frames:
            left = _draw_skeleton(left, pose_seq[p_idx], bad_joints)
            if p_idx == peak_frame:
                cv2.rectangle(left, (0, 0), (panel_w - 1, height - 1), RED, 4)

        # ── RIGHT PANEL: elite reference skeleton on black ────────────────────
        right = np.zeros((height, panel_w, 3), dtype=np.uint8)
        right[:] = (15, 15, 25)

        if p_idx < n_pose_frames:
            # Phase-matched elite frame
            elite_idx = map_athlete_to_elite(phases, elite_len, p_idx)
            elite_frame_norm = elite_seq[elite_idx]   # (17, 3) normalised

            # Project both to right panel pixel coords using same scale
            # so they're directly comparable
            elite_px   = _project_normalised_to_canvas(elite_frame_norm, panel_w, height)
            athlete_px = _project_normalised_to_canvas(athlete_norm[p_idx], panel_w, height)

            # Draw elite skeleton (bright green) first
            right = _draw_skeleton(right, elite_px, set(), color_override=ELITE_COLOR)

            # Draw athlete skeleton (colour-coded) on top — same scale as elite
            # so the visual difference is meaningful
            right = _draw_skeleton(right, athlete_px, bad_joints, alpha=0.85)

            # Difference arrows only on bad joints
            _draw_diff_arrows(right, athlete_px, elite_px, bad_joints, threshold=8.0)

            # Labels
            cv2.putText(right, "YOU",   (10, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.55, RED, 2)
            cv2.putText(right, "ELITE", (panel_w - 90, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.55, ELITE_COLOR, 2)

        # ── Phase banner ──────────────────────────────────────────────────────
        ph_name, ph_prog = get_phase_progress(phases, p_idx)
        ph_color = PHASE_COLORS.get(ph_name, WHITE)
        banner_h = 32
        for panel in (left, right):
            cv2.rectangle(panel, (0, 0), (panel_w, banner_h), (0, 0, 0), -1)
            cv2.putText(panel, ph_name, (panel_w // 2 - 60, 22),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, ph_color, 2)
            # Phase progress bar
            bar_w = int(panel_w * ph_prog)
            cv2.rectangle(panel, (0, banner_h - 4), (bar_w, banner_h), ph_color, -1)

        # ── Frame counter ─────────────────────────────────────────────────────
        cv2.putText(left, f"Frame {frame_idx + 1}", (10, height - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, WHITE, 1)

        # ── Combine ───────────────────────────────────────────────────────────
        combined = np.zeros((out_h, out_w, 3), dtype=np.uint8)
        combined[:height, :panel_w]  = left
        combined[:height, panel_w:]  = right
        combined[height:, :]         = hud

        writer.write(combined)
        frame_idx += 1

    cap.release()
    writer.release()

    return {"output_path": output_video_path, "peak_frame": peak_frame}


def _build_comparison_hud(report: dict, feedback: dict, width: int, height: int) -> np.ndarray:
    """Bottom HUD strip: metric pills + next session focus."""
    hud = np.zeros((height, width, 3), dtype=np.uint8)
    hud[:] = (20, 20, 20)

    font = cv2.FONT_HERSHEY_SIMPLEX
    x, y = 10, height // 2 + 6

    # Metric pills
    for metric, val in report.items():
        status = val["status"]
        color  = GREEN if status == "GOOD" else RED
        label  = metric.replace("_", " ").upper()[:14]
        (tw, th), _ = cv2.getTextSize(label, font, 0.35, 1)
        cv2.rectangle(hud, (x - 2, y - th - 2), (x + tw + 2, y + 2), color, -1)
        cv2.putText(hud, label, (x, y), font, 0.35, BLACK, 1)
        x += tw + 10
        if x > width - 150:
            break

    # Focus text on right
    focus = feedback.get("next_session_focus", "")
    if focus:
        focus_text = f"FOCUS: {focus[:50]}"
        (fw, _), _ = cv2.getTextSize(focus_text, font, 0.4, 1)
        cv2.putText(hud, focus_text, (width - fw - 10, height // 2 + 6),
                    font, 0.4, YELLOW, 1)

    return hud


# ── Joint index → readable name ───────────────────────────────────────────────
JOINT_NAMES = {
    0: "HEAD", 5: "L.SHOULDER", 6: "R.SHOULDER",
    7: "L.ELBOW", 8: "R.ELBOW", 9: "L.WRIST", 10: "R.WRIST",
    11: "L.HIP", 12: "R.HIP", 13: "L.KNEE", 14: "R.KNEE",
    15: "L.ANKLE", 16: "R.ANKLE",
}

# Metric → short correction label shown on the joint
METRIC_CORRECTION_LABEL = {
    "arm_cock_angle":    "PULL ELBOW BACK",
    "jump_height":       "JUMP HIGHER",
    "approach_speed":    "SPEED UP",
    "contact_point":     "REACH FORWARD",
    "follow_through":    "SWING THROUGH",
    "toss_height":       "TOSS HIGHER",
    "shoulder_rotation": "ROTATE SHOULDERS",
    "wrist_snap":        "SNAP WRIST",
    "body_lean":         "LEAN FORWARD",
    "step_timing":       "FIX TIMING",
    "reaction_time":     "REACT FASTER",
    "penultimate_step":  "LONGER STEP",
    "hand_position":     "HANDS HIGHER",
    "shoulder_width":    "WIDEN ARMS",
    "landing_balance":   "LAND BALANCED",
    "platform_angle":    "FIX PLATFORM",
    "knee_bend":         "BEND KNEES",
    "hip_drop":          "DROP HIPS",
    "arm_extension":     "EXTEND ARMS",
    "recovery_position": "RECOVER FASTER",
}


def render_coaching_video(
    input_video_path: str,
    output_video_path: str,
    pose_seq: np.ndarray,                   # (T, 17, 3) 3D — biomechanics only
    report: dict,
    feedback: dict,
    total_video_frames: int,
    pose_seq_2d: np.ndarray | None = None,  # (T, 17, 2) raw pixel coords for drawing
) -> dict:
    cap    = cv2.VideoCapture(input_video_path)
    fps    = cap.get(cv2.CAP_PROP_FPS) or 30.0
    width  = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    # Use 2D coords for drawing if available — they're always accurate pixel positions
    # 3D coords have denormalisation drift when person is off-centre
    draw_seq = pose_seq_2d if pose_seq_2d is not None else pose_seq

    card_w = 380
    hud_h  = 70
    out_w  = width + card_w
    out_h  = height + hud_h

    os.makedirs(os.path.dirname(output_video_path) or ".", exist_ok=True)
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(output_video_path, fourcc, fps, (out_w, out_h))

    bad_metrics = [m for m, v in report.items() if v["status"] == "NEEDS IMPROVEMENT"]
    bad_joints  = _bad_joints_for_metrics(bad_metrics)
    n_pose      = len(pose_seq)
    peak_frame  = _find_peak_bad_frame(pose_seq, bad_metrics, {})

    def _pidx(vf):
        return int(np.clip(round(vf * n_pose / max(total_video_frames, 1)), 0, n_pose - 1))

    card = _build_coaching_card(report, feedback, card_w, height)
    hud  = _build_bottom_hud(report, feedback, out_w, hud_h)

    frame_idx = 0
    while True:
        ret, frame = cap.read()
        if not ret:
            break

        p_idx = _pidx(frame_idx)

        # Draw skeleton using 2D pixel coords (accurate) not 3D lifted (drifts)
        if p_idx < n_pose:
            frame = _draw_skeleton(frame, draw_seq[p_idx], bad_joints)

        # Peak frame: red border + feel cue at bottom of video
        if p_idx == peak_frame:
            cv2.rectangle(frame, (0, 0), (width - 1, height - 1), RED, 5)
            fix = (feedback.get("fixes") or [{}])[0]
            cue = fix.get("feel_cue", "")
            if cue:
                _draw_text_box(frame, f"FEEL: {cue[:60]}", (8, height - 50), RED)

        _draw_phase_banner(frame, frame_idx, total_video_frames, width)

        combined = np.zeros((out_h, out_w, 3), dtype=np.uint8)
        combined[:height, :width] = frame
        combined[:height, width:] = card
        combined[height:, :]      = hud

        writer.write(combined)
        frame_idx += 1

    cap.release()
    writer.release()
    return {"output_path": output_video_path, "peak_frame": peak_frame}


def _build_coaching_card(report: dict, feedback: dict, width: int, height: int) -> np.ndarray:
    card = np.zeros((height, width, 3), dtype=np.uint8)
    card[:] = (18, 18, 28)

    font  = cv2.FONT_HERSHEY_SIMPLEX
    PAD   = 12
    chars = (width - PAD * 2) // 8   # chars per line at font 0.45

    y = 22

    # Title
    cv2.putText(card, "COACHING REPORT", (PAD, y), font, 0.55, WHITE, 1)
    y += 6
    cv2.line(card, (PAD, y), (width - PAD, y), (80, 80, 100), 1)
    y += 18

    # Headline — yellow, wrapped
    for line in _wrap(feedback.get("headline", ""), chars):
        cv2.putText(card, line, (PAD, y), font, 0.45, YELLOW, 1)
        y += 20
    y += 8

    # Fixes
    fixes = (feedback.get("fixes") or [])[:3]
    for i, fix in enumerate(fixes):
        if y > height - 60:
            break

        metric = fix.get("metric", "").replace("_", " ").upper()
        feel   = fix.get("feel_cue", "")
        drill  = fix.get("drill", "")
        rx     = fix.get("prescription", "")

        # Fix header bar
        cv2.rectangle(card, (PAD - 2, y - 16), (width - PAD + 2, y + 6), RED, -1)
        cv2.putText(card, f"FIX {i+1}  {metric}", (PAD + 2, y), font, 0.48, WHITE, 1)
        y += 20

        # Feel cue — most important, yellow
        cv2.putText(card, "FEEL:", (PAD, y), font, 0.42, YELLOW, 1)
        y += 18
        for line in _wrap(feel, chars):
            cv2.putText(card, line, (PAD + 4, y), font, 0.42, YELLOW, 1)
            y += 18
        y += 4

        # Drill
        cv2.putText(card, f"DRILL: {drill}", (PAD, y), font, 0.42, GREEN, 1)
        y += 18
        for line in _wrap(rx, chars)[:3]:
            cv2.putText(card, line, (PAD + 4, y), font, 0.40, (160, 210, 160), 1)
            y += 17
        y += 10

    # Metric status — bottom section
    remaining = height - y - 10
    if remaining > len(report) * 20 + 20:
        cv2.line(card, (PAD, y), (width - PAD, y), (80, 80, 100), 1)
        y += 14
        cv2.putText(card, "METRICS", (PAD, y), font, 0.45, WHITE, 1)
        y += 18
        for metric, val in report.items():
            if y > height - 10:
                break
            color = GREEN if val["status"] == "GOOD" else RED
            icon  = "OK" if val["status"] == "GOOD" else "FIX"
            label = metric.replace("_", " ")
            cv2.putText(card, f"{icon}  {label}", (PAD, y), font, 0.42, color, 1)
            y += 20

    return card


def _build_bottom_hud(report: dict, feedback: dict, width: int, height: int) -> np.ndarray:
    hud = np.zeros((height, width, 3), dtype=np.uint8)
    hud[:] = (12, 12, 20)
    cv2.line(hud, (0, 0), (width, 0), (80, 80, 100), 1)
    font  = cv2.FONT_HERSHEY_SIMPLEX
    focus = feedback.get("next_session_focus", "")
    if focus:
        cv2.putText(hud, "NEXT SESSION:", (12, 28), font, 0.5, YELLOW, 1)
        cv2.putText(hud, focus[:80], (12, 54), font, 0.48, WHITE, 1)
    return hud


def _draw_phase_banner(frame: np.ndarray, frame_idx: int, total: int, width: int):
    """Simple time-based phase banner — no model needed."""
    pct = frame_idx / max(total - 1, 1)
    phases = ["APPROACH", "TAKEOFF", "CONTACT", "FOLLOW-THROUGH"]
    idx    = min(int(pct * len(phases)), len(phases) - 1)
    label  = phases[idx]
    color  = PHASE_COLORS.get(label.replace("-", "_"), WHITE)

    cv2.rectangle(frame, (0, 0), (width, 28), (0, 0, 0), -1)
    (tw, _), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.65, 2)
    cv2.putText(frame, label, (width // 2 - tw // 2, 20),
                cv2.FONT_HERSHEY_SIMPLEX, 0.65, color, 2)
    # Progress bar
    bar_w = int(width * pct)
    cv2.rectangle(frame, (0, 26), (bar_w, 28), color, -1)
