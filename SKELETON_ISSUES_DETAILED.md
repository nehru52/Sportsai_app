# Skeleton Joint Rendering Issues - Detailed Analysis

## 🔍 ROOT CAUSES IDENTIFIED

### Issue 1: Invalid Coordinate Filtering (CRITICAL)
**Location:** `skeleton_overlay.py` line 62-63 and 68-69

**Problem Code:**
```python
# Line 62-63 (bone drawing)
if any(c <= 0 for c in p1) or any(c <= 0 for c in p2):
    continue

# Line 68-69 (joint drawing)
if x <= 0 and y <= 0:
    continue
```

**Why This Breaks:**
1. **Skips valid joints near edges**: A joint at position (5, 100) would be skipped because x <= 0 is checked with `any()`
2. **Wrong logic**: Uses `any(c <= 0)` for bones but `x <= 0 and y <= 0` for joints (inconsistent)
3. **Should check confidence instead**: YOLO returns (0, 0) for undetected joints, but we should use confidence scores

**Fix:**
```python
# For bones - check if BOTH coordinates are 0 (undetected)
if (p1[0] == 0 and p1[1] == 0) or (p2[0] == 0 and p2[1] == 0):
    continue

# For joints - check if BOTH coordinates are 0 (undetected)
if x == 0 and y == 0:
    continue
```

---

### Issue 2: Missing Confidence Threshold in Rendering
**Location:** `skeleton_overlay.py` `_draw_skeleton()` function

**Problem:**
- Function doesn't receive or check joint confidence scores
- Draws all joints even if YOLO confidence is low
- No way to filter out uncertain detections

**Current Signature:**
```python
def _draw_skeleton(
    frame: np.ndarray,
    keypoints: np.ndarray,          # (17, 2) or (17, 3) — XY used
    bad_joints: set[int],
    color_override: tuple | None = None,
    alpha: float = 1.0,
) -> np.ndarray:
```

**Should Be:**
```python
def _draw_skeleton(
    frame: np.ndarray,
    keypoints: np.ndarray,          # (17, 2) or (17, 3) — XY used
    bad_joints: set[int],
    confidences: np.ndarray | None = None,  # (17,) per-joint confidence
    color_override: tuple | None = None,
    alpha: float = 1.0,
    conf_threshold: float = 0.3,
) -> np.ndarray:
```

**Fix:**
```python
for idx, (x, y) in enumerate(kp):
    if x == 0 and y == 0:
        continue
    # Skip low-confidence joints
    if confidences is not None and confidences[idx] < conf_threshold:
        continue
    color = color_override or (RED if idx in bad_joints else GREEN)
    cv2.circle(overlay, (x, y), JOINT_RADIUS, color, -1)
```

---

### Issue 3: No Joint Outline for Visibility
**Location:** `skeleton_overlay.py` line 70

**Problem:**
- Joints are drawn as solid circles without outlines
- Hard to see on busy backgrounds
- No depth/contrast

**Current Code:**
```python
cv2.circle(overlay, (x, y), JOINT_RADIUS, color, -1)
```

**Fix:**
```python
# Draw black outline first (larger radius)
cv2.circle(overlay, (x, y), JOINT_RADIUS + 2, BLACK, -1)
# Draw colored joint on top
cv2.circle(overlay, (x, y), JOINT_RADIUS, color, -1)
# Optional: white inner dot for extra visibility
cv2.circle(overlay, (x, y), JOINT_RADIUS - 2, WHITE, -1)
```

---

### Issue 4: Confidence Threshold Too High
**Location:** `pose_extractor.py` line 18

**Problem:**
```python
CONFIDENCE_THRESHOLD = 0.8  # Raised from 0.7 to reject more uncertain poses
```

**Why This Breaks:**
- 0.8 is VERY high - rejects many valid poses
- YOLO confidence varies by joint (wrists often lower than hips)
- Entire frame rejected if average confidence < 0.8
- Results in missing frames and choppy skeleton

**Fix:**
```python
CONFIDENCE_THRESHOLD = 0.5  # More permissive - accept reasonable detections
```

**Better Fix (per-joint filtering):**
```python
# In pose_extractor.py, store per-joint confidences
# In skeleton_overlay.py, only draw joints with confidence > 0.3
```

---

### Issue 5: Integer Conversion Loses Sub-Pixel Accuracy
**Location:** `skeleton_overlay.py` line 48

**Problem:**
```python
kp = keypoints[:, :2].astype(int)
```

**Why This Matters:**
- YOLO returns float coordinates (e.g., 123.7, 456.2)
- Converting to int (123, 456) loses precision
- Causes jittery movement as joints snap to pixel grid
- Especially visible in slow-motion or high-FPS videos

**Fix:**
```python
kp = keypoints[:, :2].astype(np.float32)
# Convert to int only when drawing
for idx, (x, y) in enumerate(kp):
    x_int, y_int = int(round(x)), int(round(y))
    if x_int == 0 and y_int == 0:
        continue
    cv2.circle(overlay, (x_int, y_int), JOINT_RADIUS, color, -1)
```

---

### Issue 6: No Temporal Smoothing
**Location:** `pose_extractor.py` - missing smoothing step

**Problem:**
- Joint positions jump between frames due to detection noise
- No filtering or smoothing applied
- Results in jittery, unstable skeleton

**Fix (add to pose_extractor.py):**
```python
def _smooth_pose_sequence(pose_seq: np.ndarray, window: int = 5) -> np.ndarray:
    """Apply moving average smoothing to reduce jitter."""
    from scipy.ndimage import uniform_filter1d
    smoothed = uniform_filter1d(pose_seq, size=window, axis=0, mode='nearest')
    return smoothed

# After collecting all frames:
pose2d = np.array(pose2d_frames)
pose2d = _smooth_pose_sequence(pose2d, window=5)  # Smooth before lifting to 3D
```

---

### Issue 7: render_annotated_video() Not Using 2D Coords
**Location:** `skeleton_overlay.py` line 126-200

**Problem:**
- `render_annotated_video()` doesn't accept `pose_seq_2d` parameter
- Uses 3D lifted coordinates which have denormalization drift
- `render_coaching_video()` already has this fix (line 554)

**Current Signature:**
```python
def render_annotated_video(
    input_video_path: str,
    output_video_path: str,
    pose_seq: np.ndarray,           # (T, 17, 3)
    biomechanics: dict,
    report: dict,
    feedback: dict,
    elite_reference: np.ndarray | None = None,
) -> dict:
```

**Should Be:**
```python
def render_annotated_video(
    input_video_path: str,
    output_video_path: str,
    pose_seq: np.ndarray,           # (T, 17, 3) - for biomechanics
    biomechanics: dict,
    report: dict,
    feedback: dict,
    elite_reference: np.ndarray | None = None,
    pose_seq_2d: np.ndarray | None = None,  # (T, 17, 2) - raw pixel coords
) -> dict:
```

**Fix:**
```python
# Line 175 - use 2D coords if available
draw_seq = pose_seq_2d if pose_seq_2d is not None else pose_seq

# Line 185 - draw with 2D coords
if frame_idx < len(draw_seq):
    kp = draw_seq[frame_idx]
    # ... rest of drawing code
```

---

## 🔧 COMPLETE FIX IMPLEMENTATION

### Step 1: Fix Coordinate Filtering
**File:** `data_collection/skeleton_overlay.py`

Replace lines 62-63:
```python
# OLD (BROKEN)
if any(c <= 0 for c in p1) or any(c <= 0 for c in p2):
    continue

# NEW (FIXED)
if (p1[0] == 0 and p1[1] == 0) or (p2[0] == 0 and p2[1] == 0):
    continue
```

Replace lines 68-69:
```python
# OLD (BROKEN)
if x <= 0 and y <= 0:
    continue

# NEW (FIXED)
if x == 0 and y == 0:
    continue
```

### Step 2: Add Joint Outlines
**File:** `data_collection/skeleton_overlay.py`

Replace line 70:
```python
# OLD
cv2.circle(overlay, (x, y), JOINT_RADIUS, color, -1)

# NEW
# Black outline for contrast
cv2.circle(overlay, (x, y), JOINT_RADIUS + 2, BLACK, -1)
# Colored joint
cv2.circle(overlay, (x, y), JOINT_RADIUS, color, -1)
# White center dot for visibility
if JOINT_RADIUS >= 4:
    cv2.circle(overlay, (x, y), max(1, JOINT_RADIUS - 3), WHITE, -1)
```

### Step 3: Lower Confidence Threshold
**File:** `data_collection/pose_extractor.py`

Change line 18:
```python
# OLD
CONFIDENCE_THRESHOLD = 0.8

# NEW
CONFIDENCE_THRESHOLD = 0.5  # More permissive for better coverage
```

### Step 4: Add 2D Coordinate Support
**File:** `data_collection/skeleton_overlay.py`

Update `render_annotated_video()` signature (line 126):
```python
def render_annotated_video(
    input_video_path: str,
    output_video_path: str,
    pose_seq: np.ndarray,
    biomechanics: dict,
    report: dict,
    feedback: dict,
    elite_reference: np.ndarray | None = None,
    pose_seq_2d: np.ndarray | None = None,  # ADD THIS
) -> dict:
```

Add after line 175:
```python
# Use 2D pixel coords if available (more accurate than 3D denormalized)
draw_seq = pose_seq_2d if pose_seq_2d is not None else pose_seq
```

Update line 185:
```python
# OLD
if frame_idx < len(pose_seq):
    kp = pose_seq[frame_idx]

# NEW
if frame_idx < len(draw_seq):
    kp = draw_seq[frame_idx]
```

---

## 📊 EXPECTED RESULTS AFTER FIX

### Before Fix:
- ❌ Joints missing or flickering
- ❌ Skeleton jumps between people
- ❌ Hard to see joints on busy backgrounds
- ❌ Choppy, jittery movement

### After Fix:
- ✅ All detected joints visible
- ✅ Stable tracking of single person
- ✅ Clear, high-contrast joints with outlines
- ✅ Smooth, stable skeleton movement
- ✅ Accurate positioning on athlete's body

---

## 🧪 TESTING CHECKLIST

After applying fixes:
- [ ] Upload spike video - verify all joints visible
- [ ] Check joint outlines are visible on dark/light backgrounds
- [ ] Verify skeleton doesn't jump between people
- [ ] Confirm smooth movement (no jitter)
- [ ] Test with partially occluded athlete
- [ ] Verify red/green color coding works
- [ ] Check bones connect joints properly
- [ ] Confirm video plays smoothly in browser

---

## 🎯 PRIORITY ORDER

1. **CRITICAL** - Fix coordinate filtering (Step 1)
2. **HIGH** - Add joint outlines (Step 2)  
3. **HIGH** - Lower confidence threshold (Step 3)
4. **MEDIUM** - Add 2D coordinate support (Step 4)
5. **LOW** - Add temporal smoothing (future enhancement)

---

**Estimated Fix Time:** 15-20 minutes  
**Testing Time:** 10 minutes  
**Total:** ~30 minutes to complete fix
