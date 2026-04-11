# Skeleton Joint Visibility Fixes

## Problem Identified
The skeleton joint dots were not displaying correctly in annotated videos due to several issues:

1. **High confidence threshold**: `CONFIDENCE_THRESHOLD = 0.7` was too strict, causing many frames to be skipped
2. **No per-joint confidence filtering**: Joints with low confidence were being drawn with invalid coordinates
3. **Weak coordinate validation**: Only checked for `x <= 0 and y <= 0`, missing edge cases
4. **Missing confidence data flow**: Joint confidence scores weren't being passed through the rendering pipeline

## Changes Made

### 1. pose_extractor.py
- **Lowered overall confidence threshold**: `0.7` → `0.5` to capture more frames
- **Added per-joint confidence threshold**: New constant `PER_JOINT_CONFIDENCE_THRESHOLD = 0.4`
- **Updated return data**: Now includes `joint_confidences` array in the returned dictionary

### 2. skeleton_overlay.py - _draw_skeleton()
- **Added joint_confidences parameter**: Function now accepts per-joint confidence scores
- **Implemented valid joint detection**: 
  - Checks coordinates are within frame bounds (not just > 0)
  - Validates per-joint confidence >= 0.35 (MIN_JOINT_CONF)
  - Only draws joints that pass both checks
- **Improved bone drawing**: Only draws bones between valid joints
- **Better visibility**: Existing improvements (radius 6, thickness 3, black outline, red ring for errors) retained

### 3. skeleton_overlay.py - render functions
Updated all three render functions to accept and pass joint confidence data:
- `render_annotated_video()`: Added `joint_confidences` parameter
- `render_coaching_video()`: Added `joint_confidences` parameter  
- `render_side_by_side()`: Added `joint_confidences` parameter

All functions now pass confidence data to `_draw_skeleton()` calls.

### 4. api.py
- **Updated _extract_pose_for_render()**: Now returns `joint_confidences` in result dictionary
- **Updated render call**: Passes `joint_confidences` to `render_coaching_video()`

## Technical Details

### Confidence Thresholds
- **Frame-level**: 0.5 (50% overall confidence to include frame)
- **Joint-level**: 0.35-0.4 (35-40% confidence to draw individual joint)

### Coordinate Validation
Joints must satisfy ALL conditions to be drawn:
- `x > 5` and `y > 5` (not at edge/zero)
- `x < frame_width - 5` and `y < frame_height - 5` (within bounds)
- `confidence >= 0.35` (if confidence data available)

### Data Flow
```
Video → YOLO Detection → Per-joint confidence scores
                              ↓
                    extract_pose() returns joint_confidences
                              ↓
                    API passes to render functions
                              ↓
                    _draw_skeleton() filters by confidence
                              ↓
                    Only valid joints drawn on video
```

## Expected Results
- More frames will have skeleton overlays (lower threshold)
- Only high-confidence joints will be visible (better quality)
- No more "floating" or misplaced joint dots
- Clearer skeleton visualization with proper error highlighting

## Testing
To test the fixes:
1. Restart the backend server (changes are in Python files)
2. Upload a new video for analysis
3. Check the annotated video output
4. Skeleton joints should now be clearly visible and accurately positioned
5. Low-confidence joints will be automatically hidden

## Files Modified
- `data_collection/pose_extractor.py`
- `data_collection/skeleton_overlay.py`
- `api.py`
