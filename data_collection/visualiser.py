"""
Visualiser — generates heatmaps, pose data charts, and player tracking overlays.

Three outputs:
  1. Heatmap image      — where each player spent time on court (position density)
  2. Pose chart image   — joint angle timeseries for key biomechanics metrics
  3. Tracking video     — full video with all players labelled, team colours, trails

All returned as file paths the API serves directly.
"""
import cv2
import numpy as np
import os

# Team colours (BGR)
TEAM_A_COLOR = (50, 200, 50)     # green
TEAM_B_COLOR = (50, 50, 220)     # red
TRAIL_ALPHA  = 0.4
TRAIL_LEN    = 30                # frames of movement trail to show

# COCO skeleton
SKELETON = [
    (0,1),(0,2),(1,3),(2,4),(5,6),
    (5,7),(7,9),(6,8),(8,10),
    (5,11),(6,12),(11,12),
    (11,13),(13,15),(12,14),(14,16),
]


# ── 1. HEATMAP ────────────────────────────────────────────────────────────────

def render_heatmap(
    tracking_result: dict,
    output_path: str,
    court_width: int = 900,
    court_height: int = 540,
) -> str:
    """
    Generate a court heatmap showing where each player spent time.
    Brighter = more time spent in that zone.

    Returns output_path.
    """
    img_w = tracking_result.get("img_w", court_width)
    img_h = tracking_result.get("img_h", court_height)

    # Separate heatmaps per team
    heat_a = np.zeros((img_h, img_w), dtype=np.float32)
    heat_b = np.zeros((img_h, img_w), dtype=np.float32)

    for tid, frames in tracking_result["tracks"].items():
        for f in frames:
            cx, cy = f["bbox"][0], f["bbox"][1]
            x = int(np.clip(cx, 0, img_w - 1))
            y = int(np.clip(cy, 0, img_h - 1))
            team = f.get("team", "A")
            if team == "A":
                heat_a[y, x] += 1
            else:
                heat_b[y, x] += 1

    # Gaussian blur to spread the density
    heat_a = cv2.GaussianBlur(heat_a, (61, 61), 0)
    heat_b = cv2.GaussianBlur(heat_b, (61, 61), 0)

    # Normalise each to 0-255
    def _norm(h):
        if h.max() > 0:
            h = h / h.max()
        return (h * 255).astype(np.uint8)

    heat_a_norm = _norm(heat_a)
    heat_b_norm = _norm(heat_b)

    # Colourmap: team A = green-yellow, team B = red-orange
    colored_a = cv2.applyColorMap(heat_a_norm, cv2.COLORMAP_SUMMER)
    colored_b = cv2.applyColorMap(heat_b_norm, cv2.COLORMAP_HOT)

    # Court background (dark green)
    court = np.zeros((img_h, img_w, 3), dtype=np.uint8)
    court[:] = (20, 60, 20)
    _draw_court_lines(court, img_w, img_h)

    # Blend heatmaps onto court
    mask_a = heat_a_norm > 10
    mask_b = heat_b_norm > 10
    court[mask_a] = cv2.addWeighted(
        court[mask_a], 0.3, colored_a[mask_a], 0.7, 0
    )
    court[mask_b] = cv2.addWeighted(
        court[mask_b], 0.3, colored_b[mask_b], 0.7, 0
    )

    # Legend
    _draw_legend(court, img_w, img_h)

    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    cv2.imwrite(output_path, court)
    return output_path


def render_shot_map(
    actions: list,
    output_path: str,
    court_width: int = 800,
    court_height: int = 400,
) -> str:
    """
    Generate a top-down shot map showing discrete action points (serves, spikes).
    
    actions: List of dicts, each with '2d_coords' [x, y] in meters and 'action_type'.
    """
    # Canvas with padding
    pad = 40
    canvas = np.zeros((court_height + pad * 2, court_width + pad * 2, 3), dtype=np.uint8)
    canvas[:] = (30, 80, 30)  # slightly lighter green
    
    # Draw court lines (scaled)
    _draw_court_lines_scaled(canvas, court_width, court_height, pad)
    
    font = cv2.FONT_HERSHEY_SIMPLEX
    
    for act in actions:
        coords = act.get("2d_coords")
        if not coords or len(coords) < 2:
            continue
        
        x_m, y_m = coords
        # Map 18x9 meters to court_width x court_height
        px = int(pad + (x_m / 18.0) * court_width)
        py = int(pad + (y_m / 9.0) * court_height)
        
        atype = act.get("action_type", "").lower()
        if "serve" in atype:
            color = (0, 255, 255)  # yellow
            label = "S"
        elif "spike" in atype or "attack" in atype:
            color = (0, 0, 255)    # red
            label = "A"
        else:
            color = (255, 255, 255)
            label = "•"
            
        cv2.circle(canvas, (px, py), 10, color, -1)
        cv2.circle(canvas, (px, py), 10, (0, 0, 0), 1)
        if label != "•":
            cv2.putText(canvas, label, (px - 5, py + 5), font, 0.4, (0, 0, 0), 1, cv2.LINE_AA)

    # Legend
    cv2.putText(canvas, "S = Serve (Yellow)", (20, canvas.shape[0] - 15), font, 0.5, (0, 255, 255), 1)
    cv2.putText(canvas, "A = Attack (Red)", (200, canvas.shape[0] - 15), font, 0.5, (0, 0, 255), 1)

    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    cv2.imwrite(output_path, canvas)
    return output_path


def _draw_court_lines_scaled(img: np.ndarray, w: int, h: int, pad: int):
    """Draw 2D volleyball court lines to scale."""
    LINE = (255, 255, 255)
    thick = 2
    
    # Outer boundary
    cv2.rectangle(img, (pad, pad), (pad + w, pad + h), LINE, thick)
    
    # Net (Centre line)
    cv2.line(img, (pad + w // 2, pad), (pad + w // 2, pad + h), (200, 200, 200), 3)
    
    # Attack lines (3m from net)
    # 3m / 18m = 1/6 of total length
    atk_dist = w // 6
    cv2.line(img, (pad + w // 2 - atk_dist, pad), (pad + w // 2 - atk_dist, pad + h), LINE, thick)
    cv2.line(img, (pad + w // 2 + atk_dist, pad), (pad + w // 2 + atk_dist, pad + h), LINE, thick)


def _draw_court_lines(img: np.ndarray, w: int, h: int):
    """Draw basic volleyball court lines."""
    LINE = (100, 160, 100)
    thick = 2
    # Boundary
    cv2.rectangle(img, (10, 10), (w - 10, h - 10), LINE, thick)
    # Net (centre line)
    cv2.line(img, (w // 2, 10), (w // 2, h - 10), (200, 200, 200), 3)
    # Attack lines (3m from net, ~1/6 of court width each side)
    atk = w // 6
    cv2.line(img, (w // 2 - atk, 10), (w // 2 - atk, h - 10), LINE, thick)
    cv2.line(img, (w // 2 + atk, 10), (w // 2 + atk, h - 10), LINE, thick)
    # Labels
    font = cv2.FONT_HERSHEY_SIMPLEX
    cv2.putText(img, "TEAM A", (20, 30), font, 0.6, (100, 220, 100), 1)
    cv2.putText(img, "TEAM B", (w - 100, 30), font, 0.6, (100, 100, 220), 1)
    cv2.putText(img, "NET", (w // 2 - 15, h - 15), font, 0.45, (200, 200, 200), 1)


def _draw_legend(img: np.ndarray, w: int, h: int):
    font = cv2.FONT_HERSHEY_SIMPLEX
    cv2.rectangle(img, (w - 160, h - 60), (w - 10, h - 10), (30, 30, 30), -1)
    cv2.putText(img, "High activity", (w - 150, h - 40), font, 0.38, (255, 255, 255), 1)
    cv2.putText(img, "Low activity",  (w - 150, h - 20), font, 0.38, (120, 120, 120), 1)


# ── 2. POSE CHART ─────────────────────────────────────────────────────────────

def render_pose_chart(
    pose_seq: np.ndarray,       # (T, 17, 3)
    biomechanics: dict,
    report: dict,
    technique: str,
    output_path: str,
    fps: float = 30.0,
) -> str:
    """
    Render a joint angle timeseries chart as an image.
    Shows the key metrics for the technique over time, with elite range shaded.
    Green line = within elite range, red = outside.

    Returns output_path.
    """
    # Which joint angle triplets to plot per technique
    ANGLE_TRIPLETS = {
        "spike": [
            ("Hitting Arm (elbow)", 6, 8, 10),
            ("Knee Bend",           11, 13, 15),
            ("Hip-Shoulder",        11, 5, 6),
        ],
        "serve": [
            ("Serving Arm",         6, 8, 10),
            ("Trunk Lean",          0, 11, 15),
            ("Shoulder Rotation",   5, 11, 6),
        ],
        "block": [
            ("Arm Reach",           5, 7, 9),
            ("Knee Drive",          11, 13, 15),
            ("Hip Width",           11, 12, 16),
        ],
        "dig": [
            ("Platform Arm",        5, 7, 9),
            ("Knee Bend",           11, 13, 15),
            ("Hip Drop",            0, 11, 12),
        ],
    }

    triplets = ANGLE_TRIPLETS.get(technique, ANGLE_TRIPLETS["spike"])
    T = len(pose_seq)
    time_axis = np.arange(T) / fps

    chart_h = 200
    chart_w = max(T * 3, 600)
    n_charts = len(triplets)
    total_h  = chart_h * n_charts + 60
    canvas   = np.zeros((total_h, chart_w, 3), dtype=np.uint8)
    canvas[:] = (18, 18, 28)

    font = cv2.FONT_HERSHEY_SIMPLEX

    # Title
    cv2.putText(canvas, f"{technique.upper()} — Joint Angle Analysis",
                (10, 30), font, 0.7, (220, 220, 220), 1)

    for i, (label, j1, j2, j3) in enumerate(triplets):
        y_off = 50 + i * chart_h

        # Compute angles
        ba = pose_seq[:, j1] - pose_seq[:, j2]
        bc = pose_seq[:, j3] - pose_seq[:, j2]
        cos = np.einsum("fd,fd->f", ba, bc) / (
            np.linalg.norm(ba, axis=1) * np.linalg.norm(bc, axis=1) + 1e-8
        )
        angles = np.degrees(np.arccos(np.clip(cos, -1, 1)))

        a_min, a_max = angles.min(), angles.max()
        a_range = max(a_max - a_min, 1.0)

        # Background panel
        cv2.rectangle(canvas, (0, y_off), (chart_w, y_off + chart_h - 5),
                      (25, 25, 38), -1)

        # Elite range band (shaded) — use ±1 std from mean as "good zone"
        elite_mean = float(np.mean(angles))
        elite_std  = float(np.std(angles))
        band_top    = int(y_off + chart_h - 10 -
                         (elite_mean + elite_std - a_min) / a_range * (chart_h - 30))
        band_bottom = int(y_off + chart_h - 10 -
                         (elite_mean - elite_std - a_min) / a_range * (chart_h - 30))
        band_top    = int(np.clip(band_top,    y_off + 5, y_off + chart_h - 10))
        band_bottom = int(np.clip(band_bottom, y_off + 5, y_off + chart_h - 10))
        cv2.rectangle(canvas, (40, band_top), (chart_w - 10, band_bottom),
                      (30, 60, 30), -1)

        # Plot angle line
        pts = []
        for t in range(T):
            x = int(40 + (t / max(T - 1, 1)) * (chart_w - 50))
            y = int(y_off + chart_h - 10 -
                    (angles[t] - a_min) / a_range * (chart_h - 30))
            y = int(np.clip(y, y_off + 5, y_off + chart_h - 10))
            pts.append((x, y))

        for t in range(1, len(pts)):
            in_range = band_top <= pts[t][1] <= band_bottom
            color = (60, 200, 60) if in_range else (60, 60, 220)
            cv2.line(canvas, pts[t - 1], pts[t], color, 2)

        # Y-axis labels
        cv2.putText(canvas, f"{a_max:.0f}°", (2, y_off + 20), font, 0.35, (160, 160, 160), 1)
        cv2.putText(canvas, f"{a_min:.0f}°", (2, y_off + chart_h - 12), font, 0.35, (160, 160, 160), 1)

        # Chart label
        cv2.putText(canvas, label, (45, y_off + 18), font, 0.5, (220, 220, 100), 1)

        # Phase markers (vertical lines at 20%, 40%, 60%, 80%)
        for pct in [0.2, 0.4, 0.6, 0.8]:
            px = int(40 + pct * (chart_w - 50))
            cv2.line(canvas, (px, y_off + 5), (px, y_off + chart_h - 10),
                     (60, 60, 80), 1)

    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    cv2.imwrite(output_path, canvas)
    return output_path


# ── 3. TRACKING VIDEO ─────────────────────────────────────────────────────────

def render_tracking_video(
    input_video_path: str,
    tracking_result: dict,
    output_path: str,
) -> str:
    """
    Render full video with:
    - Bounding boxes per player (team colour)
    - Track ID label
    - Skeleton overlay per player
    - Movement trail (last 30 frames)
    - Player count HUD

    Returns output_path.
    """
    cap    = cv2.VideoCapture(input_video_path)
    fps    = cap.get(cv2.CAP_PROP_FPS) or 30.0
    width  = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(output_path, fourcc, fps, (width, height))

    # Build frame → list of track data lookup
    frame_lookup: dict[int, list] = {}
    for tid, frames in tracking_result["tracks"].items():
        for f in frames:
            fn = f["frame"]
            if fn not in frame_lookup:
                frame_lookup[fn] = []
            frame_lookup[fn].append({"tid": tid, **f})

    # Trail: track_id → deque of centre positions
    from collections import deque
    trails: dict[str, deque] = {}

    frame_num = 0
    font = cv2.FONT_HERSHEY_SIMPLEX

    while True:
        ret, frame = cap.read()
        if not ret:
            break
        frame_num += 1

        players_this_frame = frame_lookup.get(frame_num, [])

        for p in players_this_frame:
            tid   = p["tid"]
            team  = p.get("team", "A")
            color = TEAM_A_COLOR if team == "A" else TEAM_B_COLOR
            cx, cy, bw, bh = p["bbox"]
            x1 = int(cx - bw / 2)
            y1 = int(cy - bh / 2)
            x2 = int(cx + bw / 2)
            y2 = int(cy + bh / 2)

            # Bounding box
            cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)

            # Track ID label
            label = f"#{tid} {'A' if team == 'A' else 'B'}"
            cv2.putText(frame, label, (x1, y1 - 6), font, 0.5, color, 2)

            # Skeleton
            if p.get("keypoints"):
                kp = np.array(p["keypoints"])   # (17, 3)
                _draw_player_skeleton(frame, kp, color)

            # Trail
            centre = (int(cx), int(cy))
            if tid not in trails:
                trails[tid] = deque(maxlen=TRAIL_LEN)
            trails[tid].append(centre)

        # Draw trails
        for tid, trail in trails.items():
            pts = list(trail)
            team = "A"
            for p in players_this_frame:
                if p["tid"] == tid:
                    team = p.get("team", "A")
                    break
            color = TEAM_A_COLOR if team == "A" else TEAM_B_COLOR
            for j in range(1, len(pts)):
                alpha = j / len(pts)
                c = tuple(int(v * alpha) for v in color)
                cv2.line(frame, pts[j - 1], pts[j], c, 2)

        # HUD
        team_a = sum(1 for p in players_this_frame if p.get("team") == "A")
        team_b = sum(1 for p in players_this_frame if p.get("team") == "B")
        cv2.rectangle(frame, (0, 0), (220, 36), (0, 0, 0), -1)
        cv2.putText(frame, f"Team A: {team_a}  Team B: {team_b}  Frame: {frame_num}",
                    (6, 24), font, 0.5, (220, 220, 220), 1)

        writer.write(frame)

    cap.release()
    writer.release()
    return output_path


def _draw_player_skeleton(frame: np.ndarray, kp: np.ndarray, color: tuple):
    """Draw skeleton for a single player."""
    pts = kp[:, :2].astype(int)
    confs = kp[:, 2] if kp.shape[1] > 2 else np.ones(len(kp))
    for i, j in SKELETON:
        if i >= len(pts) or j >= len(pts):
            continue
        if confs[i] < 0.3 or confs[j] < 0.3:
            continue
        p1, p2 = tuple(pts[i]), tuple(pts[j])
        if any(v <= 0 for v in p1) or any(v <= 0 for v in p2):
            continue
        cv2.line(frame, p1, p2, color, 1)
    for idx, (x, y) in enumerate(pts):
        if x > 0 and y > 0 and confs[idx] > 0.3:
            cv2.circle(frame, (x, y), 3, color, -1)
