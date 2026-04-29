# AI-TO-AI PROJECT HANDOFF DOCUMENT

## PROJECT CONTEXT

**Project Name:** SportsAI - Volleyball Technique Analysis Platform  
**Tech Stack:** Python (FastAPI backend) + Vanilla JS frontend  
**Purpose:** Analyze volleyball videos using YOLO11x-pose + 3D pose lifting, provide biomechanics feedback with annotated video output

**Current Status:** 
- ✅ Backend API running on port 8001
- ✅ Frontend running on port 3000
- ✅ Video upload, analysis, and results display working
- ❌ **CRITICAL BUG:** Skeleton joint dots not rendering correctly on annotated videos

---

## CRITICAL BUG TO FIX

### User Report
"skeleton joint dots still doesn't work perfectly" - joints are missing, flickering, or not visible on the annotated video output

### Root Cause Analysis

**BUG #1: Invalid Coordinate Filtering (MOST CRITICAL)**
- **Location:** `data_collection/skeleton_overlay.py` lines 62-63 and 68-69
- **Problem:** The code uses `any(c <= 0 for c in p1)` which incorrectly skips valid joints
- **Example:** A joint at pixel position (5, 100) gets skipped because `any([5 <= 0, 100 <= 0])` evaluates incorrectly
- **Impact:** Many valid joints near frame edges are not drawn

**Current Broken Code:**
```python
# Line 62-63 (bone drawing)
if any(c <= 0 for c in p1) or any(c <= 0 for c in p2):
    continue

# Line 68-69 (joint drawing)  
if x <= 0 and y <= 0:
    continue
```

**Correct Logic:**
YOLO returns (0, 0) for undetected joints. We should only skip if BOTH x AND y are exactly 0, not if either is <= 0.

**BUG #2: Confidence Threshold Too High**
- **Location:** `data_collection/pose_extractor.py` line 18
- **Current:** `CONFIDENCE_THRESHOLD = 0.8`
- **Problem:** Rejects too many valid pose detections, causing missing frames
- **Impact:** Choppy skeleton with gaps

**BUG #3: No Visual Contrast**
- **Location:** `data_collection/skeleton_overlay.py` line 70
- **Problem:** Joints drawn as solid circles without outlines
- **Impact:** Hard to see on busy video backgrounds

**BUG #4: Using 3D Coordinates Instead of 2D**
- **Location:** `data_collection/skeleton_overlay.py` `render_annotated_video()` function
- **Problem:** Uses 3D lifted coordinates which have denormalization drift
- **Note:** `render_coaching_video()` already has the fix (accepts `pose_seq_2d` parameter)
- **Impact:** Joints positioned incorrectly on athlete's body

---

## EXACT FIXES REQUIRED

### FIX #1: Coordinate Filtering (CRITICAL - DO THIS FIRST)

**File:** `data_collection/skeleton_overlay.py`

**Line 62-63:** Replace:
```python
if any(c <= 0 for c in p1) or any(c <= 0 for c in p2):
    continue
```
With:
```python
if (p1[0] == 0 and p1[1] == 0) or (p2[0] == 0 and p2[1] == 0):
    continue
```

**Line 68-69:** Replace:
```python
if x <= 0 and y <= 0:
    continue
```
With:
```python
if x == 0 and y == 0:
    continue
```

**Explanation:** Only skip joints that are exactly (0, 0) which indicates YOLO didn't detect them. Don't skip joints with small positive coordinates.

---

### FIX #2: Add Joint Outlines for Visibility

**File:** `data_collection/skeleton_overlay.py`

**Line 70:** Replace:
```python
cv2.circle(overlay, (x, y), JOINT_RADIUS, color, -1)
```
With:
```python
# Draw black outline first (larger radius)
cv2.circle(overlay, (x, y), JOINT_RADIUS + 2, BLACK, -1)
# Draw colored joint on top
cv2.circle(overlay, (x, y), JOINT_RADIUS, color, -1)
# Draw white center dot for extra visibility
if JOINT_RADIUS >= 4:
    cv2.circle(overlay, (x, y), max(1, JOINT_RADIUS - 3), WHITE, -1)
```

**Explanation:** Three-layer rendering (black outline, colored fill, white center) makes joints visible on any background.

---

### FIX #3: Lower Confidence Threshold

**File:** `data_collection/pose_extractor.py`

**Line 18:** Replace:
```python
CONFIDENCE_THRESHOLD = 0.8  # Raised from 0.7 to reject more uncertain poses
```
With:
```python
CONFIDENCE_THRESHOLD = 0.5  # More permissive - accept reasonable detections
```

**Explanation:** 0.8 is too strict and rejects many valid poses. 0.5 is standard for YOLO pose detection.

---

### FIX #4: Use 2D Pixel Coordinates for Drawing

**File:** `data_collection/skeleton_overlay.py`

**Step 4a - Update function signature (line 126):**
```python
def render_annotated_video(
    input_video_path: str,
    output_video_path: str,
    pose_seq: np.ndarray,           # (T, 17, 3)
    biomechanics: dict,
    report: dict,
    feedback: dict,
    elite_reference: np.ndarray | None = None,  # (17, 3) single elite frame
    pose_seq_2d: np.ndarray | None = None,  # ADD THIS PARAMETER
) -> dict:
```

**Step 4b - Add after line 175 (after bad_joints calculation):**
```python
# Use 2D pixel coords if available (more accurate than 3D denormalized)
draw_seq = pose_seq_2d if pose_seq_2d is not None else pose_seq
```

**Step 4c - Update line 185 (in the while loop):**
Replace:
```python
if frame_idx < len(pose_seq):
    kp = pose_seq[frame_idx]
```
With:
```python
if frame_idx < len(draw_seq):
    kp = draw_seq[frame_idx]
```

**Explanation:** The API already passes `pose_seq_2d` (raw YOLO pixel coordinates) to `render_coaching_video()`. We need to add the same support to `render_annotated_video()`. 2D coordinates are more accurate than 3D coordinates that have been denormalized back to pixel space.

---

## FILE STRUCTURE REFERENCE

### Key Files Involved in This Bug:

```
project_root/
├── api.py                              # FastAPI backend, calls rendering functions
├── data_collection/
│   ├── pose_extractor.py              # YOLO pose detection, FIX #3 here
│   ├── skeleton_overlay.py            # Video rendering, FIX #1, #2, #4 here
│   ├── pose_3d_lifter.py              # 2D→3D pose lifting
│   └── smart_analyser.py              # Video analysis orchestration
└── frontend/
    ├── app.js                          # Frontend logic, video playback
    ├── index.html                      # Upload interface
    └── style.css                       # SportsAI design system
```

### How the Pipeline Works:

1. **User uploads video** → `frontend/app.js` → POST to `/analyse/auto`
2. **API receives video** → `api.py` → calls `analyse_video_auto()`
3. **Pose extraction** → `pose_extractor.py` → YOLO detects 2D keypoints
4. **3D lifting** → `pose_3d_lifter.py` → converts 2D to 3D coordinates
5. **Biomechanics** → calculates angles, velocities, metrics
6. **Rendering** → `skeleton_overlay.py` → draws s