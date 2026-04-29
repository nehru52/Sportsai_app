# SportsAI - Current Issues Summary

**Date:** April 18, 2026  
**Status:** Active Development

---

## 🔴 CRITICAL ISSUE: Skeleton Joint Dots Not Displaying Correctly

### Problem Description
The skeleton overlay on annotated videos is not rendering joints properly. User reported: "skeleton joint dots still doesn't work perfectly"

### Current Status
- **Partially Fixed**: Made improvements to joint rendering (increased radius, added outlines, error highlighting)
- **Still Broken**: Dots still not displaying correctly according to user feedback
- **Backend**: Auto-reloaded with changes but issue persists

### What We've Tried
1. ✅ Increased joint radius from 5px to 6px
2. ✅ Increased bone thickness from 2px to 3px  
3. ✅ Added black outline around joints for contrast
4. ✅ Added extra red ring around error joints
5. ❌ Issue still not resolved

### Possible Root Causes

#### 1. **Low Confidence Threshold**
- **Location**: `data_collection/pose_extractor.py` line 18
- **Current Value**: `CONFIDENCE_THRESHOLD = 0.8`
- **Issue**: May be rejecting too many valid poses, causing missing joints
- **Fix**: Lower to 0.5-0.6 to accept more detections

#### 2. **Person Tracking Issues**
- **Location**: `pose_extractor.py` `_select_person()` function
- **Issue**: May be switching between different people mid-video
- **Symptoms**: Joints jumping around or disappearing
- **Fix**: Improve person locking mechanism (currently locks after 3 frames)

#### 3. **2D vs 3D Coordinate Mismatch**
- **Location**: `skeleton_overlay.py` rendering functions
- **Issue**: Using 3D lifted coordinates instead of raw 2D pixel coordinates
- **Current**: `pose_seq` (3D) used for drawing
- **Should Use**: `pose_seq_2d` (raw YOLO pixel coords) for accurate overlay
- **Note**: `render_coaching_video()` already has this fix, but other renderers don't

#### 4. **Joint Visibility Checks**
- **Location**: `skeleton_overlay.py` line 42-43
- **Code**: `if x <= 0 and y <= 0: continue`
- **Issue**: Skips joints at (0,0) but may also skip valid low-coordinate joints
- **Fix**: Check confidence instead of coordinates

#### 5. **Temporal Instability**
- **Issue**: No smoothing between frames causes jittery joints
- **Fix**: Add Kalman filter or moving average smoothing to joint positions

#### 6. **YOLO Detection Accuracy**
- **Model**: YOLO11x-pose
- **Issue**: May not detect all joints in every frame (occlusion, motion blur)
- **Fix**: Add interpolation for missing joints between frames

### Recommended Fix Priority

1. **IMMEDIATE** - Use 2D pixel coordinates for drawing (not 3D)
   - Update `render_annotated_video()` to use `pose_seq_2d` parameter
   - Update `render_side_by_side()` to use `pose_seq_2d` for athlete overlay
   
2. **HIGH** - Lower confidence threshold
   - Change `CONFIDENCE_THRESHOLD` from 0.8 to 0.6
   
3. **MEDIUM** - Add temporal smoothing
   - Implement moving average filter on joint positions
   
4. **LOW** - Improve person tracking
   - Increase lock frames from 3 to 5
   - Add bounding box overlap check

### Files to Modify
- `data_collection/skeleton_overlay.py` - Use 2D coords for drawing
- `data_collection/pose_extractor.py` - Lower confidence threshold
- `api.py` - Pass `pose_seq_2d` to rendering functions

---

## 🟡 MINOR ISSUES

### 1. Video Codec Compatibility
**Status:** ✅ FIXED (using H.264 now)
- Changed from `mp4v` to H.264 codec
- Videos now play in browser without download
- Fallback to mp4v if H.264 unavailable

### 2. Progress Animation Timing
**Status:** ✅ FIXED
- Was using hardcoded 55s animation
- Now completes immediately when API returns
- Added `completeAllSteps()` function

### 3. Public Sharing Setup
**Status:** ✅ WORKING
- Using ngrok instead of localtunnel
- Frontend: https://breezy-hotels-make.loca.lt
- Backend: https://2a54-82-11-179-110.ngrok-free.app
- Security IP: 82.11.179.110

---

## 🟢 COMPLETED FEATURES

### Design System
- ✅ SportsAI color palette applied
- ✅ Typography system (Barlow Condensed, DM Sans, JetBrains Mono)
- ✅ Spacing (4px grid), border radius, shadows
- ✅ Animations (score count-up, XP bars, button press, glow effects)

### Interactive Features
- ✅ Home dashboard with 6 zones
- ✅ AI Coach chat interface
- ✅ Floating action button (FAB)
- ✅ Smooth animations throughout

### Video Analysis
- ✅ Upload and analyze videos
- ✅ Technique selection (spike, serve, block, dig)
- ✅ Progress tracking with steps
- ✅ Results display with metrics
- ✅ Coaching feedback with drills

### Backend
- ✅ YOLO11x-pose detection
- ✅ 3D pose lifting
- ✅ Biomechanics calculation
- ✅ Technique-specific coaching
- ✅ H.264 video encoding

---

## 📋 NEXT STEPS

### Immediate Actions (Today)
1. Test current video analysis to identify exact skeleton issue
2. Implement 2D coordinate fix in skeleton_overlay.py
3. Lower confidence threshold to 0.6
4. Test with user's video to verify fix

### Short Term (This Week)
1. Add temporal smoothing to joint positions
2. Improve person tracking stability
3. Add joint interpolation for missing detections
4. Optimize rendering performance

### Long Term (Future)
1. Fine-tune YOLO model on volleyball-specific data
2. Add multi-person tracking for team analysis
3. Implement real-time analysis
4. Add mobile app support

---

## 🔧 TECHNICAL DEBT

### Code Quality
- Some functions in `skeleton_overlay.py` are too long (>100 lines)
- Duplicate code between rendering functions
- Missing type hints in some functions
- Limited error handling in video processing

### Performance
- Video processing is slow for long videos (>2 minutes)
- No caching of pose detections
- Redundant API calls for JSON + video
- No batch processing support

### Testing
- No automated tests
- No unit tests for biomechanics calculations
- No integration tests for API endpoints
- Manual testing only

---

## 📊 SYSTEM STATUS

### Servers Running
- ✅ Frontend: Port 3000 (terminal 9)
- ✅ Backend: Port 8001 (terminal 12)
- ✅ Ngrok Frontend: Terminal 15
- ✅ Ngrok Backend: Terminal 16

### Dependencies
- ✅ Python 3.x
- ✅ YOLO11x-pose model
- ✅ ffmpeg (H.264 codec)
- ✅ OpenCV
- ✅ NumPy
- ✅ FastAPI

### Public URLs
- Frontend: https://breezy-hotels-make.loca.lt/index_launcher.html
- Backend: https://2a54-82-11-179-110.ngrok-free.app

---

## 💡 USER FEEDBACK

### Recent Comments
1. "skeleton joint dots still doesn't work perfectly" - **NEEDS FIX**
2. "the video works now" - ✅ RESOLVED
3. "make sure to build the app and add features in such a way that its highly interactive and well built with some appealing looks" - ✅ COMPLETED

### User Expectations
- Skeleton joints must be clearly visible and accurate
- Video must play inline in browser
- App should be highly interactive with appealing design
- Analysis should be fast and accurate

---

## 🎯 SUCCESS CRITERIA

### For Skeleton Joint Fix
- [ ] All 17 COCO keypoints visible when detected
- [ ] Joints stay stable (no jittering)
- [ ] Joints track correct person throughout video
- [ ] Red highlighting works for error joints
- [ ] Green highlighting works for good joints
- [ ] Bones connect joints smoothly
- [ ] User confirms "skeleton dots work perfectly"

### For Overall Project
- [x] Video plays in browser
- [x] Design system applied
- [x] Interactive features built
- [ ] Skeleton overlay works perfectly
- [ ] Public sharing works reliably
- [ ] Analysis is accurate and fast

---

**Last Updated:** April 18, 2026  
**Priority:** Fix skeleton joint rendering ASAP
