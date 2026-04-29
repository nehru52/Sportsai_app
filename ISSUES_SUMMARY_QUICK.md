# SportsAI - Issues Summary (Quick Reference)

## 🔴 MAIN ISSUE: Skeleton Joints Not Displaying Correctly

### The Problem
User reports: "skeleton joint dots still doesn't work perfectly"

### Root Causes Found

1. **CRITICAL BUG - Wrong Coordinate Check**
   - **File:** `skeleton_overlay.py` lines 62-63, 68-69
   - **Bug:** `if any(c <= 0 for c in p1)` skips valid joints near edges
   - **Example:** Joint at (5, 100) is skipped because 5 <= 0 fails the check
   - **Fix:** Change to `if (p1[0] == 0 and p1[1] == 0)`

2. **Confidence Threshold Too High**
   - **File:** `pose_extractor.py` line 18
   - **Current:** `CONFIDENCE_THRESHOLD = 0.8` (too strict)
   - **Fix:** Change to `0.5` or `0.6`

3. **No Joint Outlines**
   - **File:** `skeleton_overlay.py` line 70
   - **Issue:** Joints hard to see on busy backgrounds
   - **Fix:** Add black outline + white center dot

4. **Missing 2D Coordinate Support**
   - **File:** `skeleton_overlay.py` `render_annotated_video()`
   - **Issue:** Uses 3D coords (inaccurate) instead of 2D pixel coords
   - **Fix:** Add `pose_seq_2d` parameter like `render_coaching_video()` has

---

## 🔧 QUICK FIXES (In Priority Order)

### Fix #1: Coordinate Filtering (5 min)
**File:** `data_collection/skeleton_overlay.py`

**Line 62-63:** Change from:
```python
if any(c <= 0 for c in p1) or any(c <= 0 for c in p2):
```
To:
```python
if (p1[0] == 0 and p1[1] == 0) or (p2[0] == 0 and p2[1] == 0):
```

**Line 68-69:** Change from:
```python
if x <= 0 and y <= 0:
```
To:
```python
if x == 0 and y == 0:
```

### Fix #2: Joint Outlines (3 min)
**File:** `data_collection/skeleton_overlay.py`

**Line 70:** Replace:
```python
cv2.circle(overlay, (x, y), JOINT_RADIUS, color, -1)
```
With:
```python
cv2.circle(overlay, (x, y), JOINT_RADIUS + 2, BLACK, -1)  # Outline
cv2.circle(overlay, (x, y), JOINT_RADIUS, color, -1)      # Joint
cv2.circle(overlay, (x, y), max(1, JOINT_RADIUS - 3), WHITE, -1)  # Center
```

### Fix #3: Confidence Threshold (1 min)
**File:** `data_collection/pose_extractor.py`

**Line 18:** Change from:
```python
CONFIDENCE_THRESHOLD = 0.8
```
To:
```python
CONFIDENCE_THRESHOLD = 0.5
```

### Fix #4: Use 2D Coordinates (5 min)
**File:** `data_collection/skeleton_overlay.py`

**Line 126:** Add parameter:
```python
def render_annotated_video(
    ...
    elite_reference: np.ndarray | None = None,
    pose_seq_2d: np.ndarray | None = None,  # ADD THIS LINE
) -> dict:
```

**After line 175:** Add:
```python
draw_seq = pose_seq_2d if pose_seq_2d is not None else pose_seq
```

**Line 185:** Change from:
```python
if frame_idx < len(pose_seq):
    kp = pose_seq[frame_idx]
```
To:
```python
if frame_idx < len(draw_seq):
    kp = draw_seq[frame_idx]
```

---

## ✅ COMPLETED ITEMS

- ✅ Video codec fixed (H.264)
- ✅ Video plays in browser
- ✅ Progress animation fixed
- ✅ Design system applied
- ✅ Interactive features built
- ✅ Public sharing setup (ngrok)
- ✅ Backend running on port 8001
- ✅ Frontend running on port 3000

---

## 🎯 TESTING AFTER FIX

1. Restart backend: `Ctrl+C` in terminal 12, then re-run API
2. Upload test video with spike technique
3. Check that:
   - All 17 joints visible (when detected)
   - Joints have black outlines
   - Skeleton doesn't flicker
   - Joints stay on correct person
   - Red/green colors work

---

## 📁 FILES TO MODIFY

1. `data_collection/skeleton_overlay.py` - 3 changes (lines 62, 68, 70, 126, 175, 185)
2. `data_collection/pose_extractor.py` - 1 change (line 18)

**Total Changes:** 4 fixes across 2 files  
**Estimated Time:** 15 minutes  
**Difficulty:** Easy (simple value changes)

---

## 🚀 DEPLOYMENT STATUS

### Servers
- ✅ Frontend: http://localhost:3000 (terminal 9)
- ✅ Backend: http://localhost:8001 (terminal 12)
- ✅ Public: https://breezy-hotels-make.loca.lt

### Next Steps
1. Apply the 4 fixes above
2. Restart backend server
3. Test with user's video
4. Get user confirmation: "skeleton dots work perfectly"

---

**Last Updated:** April 18, 2026  
**Status:** Ready to fix - all issues identified
