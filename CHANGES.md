# Changes and Improvements

## Improvement 1: Homography Perspective Correction
- **Created:** `utils/homography_corrector.py` - Handles mapping court corners to a canonical 640x360 view.
- **Modified:** `data_collection/pose_extractor.py` - Integrated court detection and homography correction into the processing loop.
- **Modified:** `finetune_yolo.py` - Added initial perspective augmentations.

## Improvement 2: Kalman-Predicted Bounding Box Crop Expander
- **Created:** `utils/kalman_crop_expander.py` - Implements `AthleteTrack` (Kalman Filter) and `KalmanCropExpander` for stable cropping and jump-aware padding.
- **Modified:** `data_collection/pose_extractor.py` - Integrated the expander to stabilize crops and handle jumping athletes (using 55% padding during jumps).

## Improvement 3: ByteTrack Multi-Player Tracking with Role Classifier
- **Created:** `utils/role_classifier.py` - Classifies athlete roles ('hitter', 'setter', 'libero', 'blocker') based on velocity and positioning.
- **Modified:** `data_collection/pose_extractor.py` - Replaced single-frame NMS with Ultralytics ByteTrack for multi-player tracking.

## Improvement 4: Confidence-Gated Keypoint Smoothing for MotionAGFormer
- **Modified:** `data_collection/pose_extractor.py` - Implemented Exponential Moving Average (EMA) smoothing for low-confidence keypoints (conf < 0.5).
- **Modified:** `finetune_lifter.py` - Updated loss functions to include Smoothness Loss and Bone Consistency Loss with weights (MPJPE=0.3, Smoothness=0.4, Bone=0.3).

## Improvement 5: YOLO Fine-tuning Augmentation Upgrades
- **Modified:** `finetune_yolo.py` - Upgraded the `albumentations` pipeline with MotionBlur, RandomGamma, GaussNoise, and ImageCompression to simulate realistic gym conditions.

## Fix Pass 1
- **utils/homography_corrector.py**: Added `self.H` attribute, `remap_keypoints` method, and reprojection error guard (>15px).
- **utils/role_classifier.py**: Added guard for short track history (<5 frames) and default 'court_zone' handling.
- **utils/recruiter_output.py**: Created new file to build recruiter-focused JSON outputs with FIVB scoring.
- **data_collection/pose_extractor.py**: 
    - Added `get_court_zone`, `save_ema_state`, and `load_ema_state` helpers.
    - Integrated inverse homography remapping for keypoints.
    - Integrated `RecruiterOutputBuilder` for persistent player performance tracking.
    - Added EMA state persistence between video processing sessions.

## Fix Pass 2
- **utils/recruiter_output.py**: 
    - Modified `update_player()` to accept `event_flags`.
    - Implemented `jump_height_normalised` scoring (body-height ratio thresholds: 0.25, 0.40).
    - Added `jump_event_count` and `spike_event_count` gates (min 3 events) for FIVB scoring and recruiter flags.
    - Added `scoring_notes`, `normalised_scoring`, and event data fields to JSON schema.
- **data_collection/pose_extractor.py**:
    - Added `time` import and updated `load_ema_state` with 7-day TTL and 500-track hard cap.
    - Implemented `standing_height` tracking (frames with vy < 2.0).
    - Integrated `jump_height_normalised` computation using running mean of standing height.
    - Added `is_jumping` and `is_spiking` heuristic event triggers.
    - Updated all `update_player()` call sites with new signature and biomechanics payload.

## Phase 5 — Match Analysis Module
- **utils/rally_detector.py**: Created class `RallyDetector` for automated rally start/end and spike counting.
- **utils/heatmap_generator.py**: Created class `HeatmapGenerator` for grid-based athlete court coverage analysis.
- **utils/performance_drift.py**: Created class `PerformanceDriftTracker` to monitor fatigue and biomechanical trends across match sets.
- **utils/match_timeline.py**: Created class `MatchTimelineBuilder` for generating chronological match summaries.
- **data_collection/pose_extractor.py**:
    - Integrated all match analysis modules into the main telescopic pipeline loop.
    - Added post-processing step to attach drift reports and heatmaps to recruiter data.
    - Automated saving of match-wide event timelines.

## Phase 6 — Recruiter Comparison Module
- **utils/player_aggregator.py**: Created `PlayerAggregator` for multi-clip data merging with weighted means and event accumulation.
- **utils/head_to_head.py**: Created `HeadToHeadComparator` for pairwise athlete analysis and recommendation heuristics.
- **utils/report_generator.py**: Created `ReportGenerator` for high-quality, browser-printable HTML recruiter reports (single athlete, vs, squad).
- **run_recruiter.py**: Built CLI entry point for ranking, comparing, and reporting on athlete performance.
- **Directories**: Initialised `data/reports/` for professional HTML output.

## Phase 7 — Frontend Integration
- **api.py**: Added REST endpoints for aggregated player data, match summaries, spatial heatmaps, and head-to-head comparisons.
- **frontend/players.html**: Created a searchable athlete roster with role filters and performance scorecards.
- **frontend/match.html**: Built a match dashboard with event timelines and player fatigue/trend tracking.
- **frontend/compare.html**: Implemented a side-by-side athlete comparison interface with highlighted advantages.
- **frontend/js/heatmap.js**: Developed a canvas-based spatial distribution visualiser with court overlay.
