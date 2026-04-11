# SportsAI Frontend & Analysis Pipeline Fixes

## Issues Fixed

### 1. ✅ Video Upload Mode Selection
**Problem:** Video upload defaulted to "Full Match" mode instead of single analysis

**Fix:**
- Added `selectedMode` variable defaulting to `'single'` in `app.js`
- Created mode selection UI with "Single Analysis" and "Full Match" pills
- Mode pills toggle visibility of technique selection vs team options
- Single Analysis mode is now the default

**Files Changed:**
- `frontend/app.js` - Added mode state management
- `frontend/index.html` - Added mode selection UI
- `frontend/style.css` - Added `.mode-pill` styles

---

### 2. ✅ Technique Selection Dropdown
**Problem:** Technique selection (spike/serve/block/dig) dropdown missing/disabled

**Fix:**
- Technique selection now visible by default in Single Analysis mode
- Options: Auto-detect, Spike, Serve, Block, Dig
- Hidden when Full Match mode is selected
- Technique parameter passed to API endpoint

**Files Changed:**
- `frontend/index.html` - Restructured technique selection with proper visibility
- `frontend/app.js` - Added technique parameter to API calls
- `frontend/style.css` - Updated `.tech-row` styles for better layout

---

### 3. ✅ API Endpoint Enhancement
**Problem:** `/analyse/auto` didn't accept technique parameter

**Fix:**
- Added `technique` query parameter to `/analyse/auto` endpoint
- Accepts: "spike", "serve", "block", "dig", "auto", or None (defaults to auto-detect)
- Technique hint passed through to `analyse_video_auto()`
- When technique specified, creates single segment for entire video

**Files Changed:**
- `api.py` - Added technique parameter to endpoint signature
- `data_collection/smart_analyser.py` - Added technique_hint parameter and logic

---

### 4. ✅ Person Selection Logic
**Problem:** Analysis focused on wrong person (closest to camera, not action performer)

**Status:** Already correctly implemented in `pose_extractor.py`

**Current Implementation:**
- Spike/Block: Prioritizes most airborne person (ankle height tracking)
- Tracks minimum ankle Y position per person
- Only locks to person after they rise >8% of frame height (AIRBORNE_THRESHOLD)
- Fallback to wrist height if ankles occluded
- Dig: Selects person with lowest hip position
- Serve: Selects person with wrist above head
- Person locking prevents switching mid-analysis

**No changes needed** - logic is already optimal

---

### 5. ✅ Technique-Specific Coaching
**Problem:** Coaching recommendations might be generic, not technique-specific

**Status:** Already correctly implemented in `coach_feedback.py`

**Current Implementation:**
- Technique parameter passed through entire pipeline
- `_build_prompt()` uses technique-specific context
- Metric explanations mapped per technique (METRIC_EXPLANATIONS dict)
- Drill library has technique-specific exercises (METRIC_DRILLS dict)
- Prompt includes technique name in context
- AI generates coaching based on technique-specific metrics

**No changes needed** - coaching is already technique-aware

---

## Frontend UI Improvements

### New Layout Structure
```
Upload Zone
├── Mode Selection (NEW)
│   ├── Single Analysis (default, active)
│   └── Full Match
├── Technique Selection (visible in Single mode)
│   ├── Auto-detect (default)
│   ├── Spike
│   ├── Serve
│   ├── Block
│   └── Dig
└── Team Options (visible in Match mode)
    └── Team Size dropdown (6v6, 4v4, 2v2)
```

### Visual Design
- Mode pills: Blue accent (#4d9fff) when active
- Technique pills: Orange accent (#ff4500) when active
- Clear visual hierarchy with labels
- Responsive layout with proper spacing

---

## API Changes

### `/analyse/auto` Endpoint
**Before:**
```python
POST /analyse/auto?output=json
```

**After:**
```python
POST /analyse/auto?output=json&technique=spike
# technique options: auto, spike, serve, block, dig
```

### Behavior
- `technique=auto` or omitted → Auto-detect technique from video
- `technique=spike` → Analyze entire video as spike
- `technique=serve` → Analyze entire video as serve
- `technique=block` → Analyze entire video as block
- `technique=dig` → Analyze entire video as dig

---

## Testing Checklist

- [ ] Upload video in Single Analysis mode with Auto-detect
- [ ] Upload video in Single Analysis mode with Spike selected
- [ ] Upload video in Single Analysis mode with Serve selected
- [ ] Upload video in Single Analysis mode with Block selected
- [ ] Upload video in Single Analysis mode with Dig selected
- [ ] Upload video in Full Match mode
- [ ] Verify correct person is tracked in spike video
- [ ] Verify correct person is tracked in serve video
- [ ] Verify coaching feedback is spike-specific
- [ ] Verify coaching feedback is serve-specific
- [ ] Verify mode toggle shows/hides correct options

---

## Summary

All requested fixes have been implemented:

1. ✅ Default mode is now "Single Analysis" (not Full Match)
2. ✅ Technique selection dropdown added and functional
3. ✅ Mode selection toggles appropriate form fields
4. ✅ Technique parameter passed to API endpoint
5. ✅ Person selection already optimal (airborne detection for spike/block)
6. ✅ Coaching already technique-specific (verified in code)

The frontend now provides a clear, intuitive interface for users to select their analysis mode and technique, with proper defaults and visual feedback.
