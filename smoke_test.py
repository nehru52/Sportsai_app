import numpy as np
import cv2
import os
import sys

# Add root to path for imports
sys.path.append(os.getcwd())

from utils.homography_corrector import HomographyCorrector
from utils.kalman_crop_expander import KalmanCropExpander

def smoke_test():
    print("Running Smoke Test...")
    
    # 1. Test HomographyCorrector
    print("Testing HomographyCorrector...")
    dummy_frame = np.zeros((1080, 1920, 3), dtype=np.uint8)
    corrector = HomographyCorrector()
    dummy_corners = [[100, 100], [1800, 150], [1850, 900], [50, 850]]
    corrector.fit(dummy_corners)
    transformed = corrector.transform(dummy_frame)
    print(f"  Homography transform shape: {transformed.shape} (Expected (360, 640, 3))")
    assert transformed.shape == (360, 640, 3)
    
    # 2. Test KalmanCropExpander
    print("Testing KalmanCropExpander...")
    expander = KalmanCropExpander(frame_w=640, frame_h=360)
    dummy_detections = {1: np.array([100, 50, 200, 250])}
    crops = expander.process_frame(dummy_detections)
    print(f"  Crop result for TID 1: {crops[1]}")
    assert 1 in crops
    assert len(crops[1]) == 4
    
    # 3. Test Match Analysis Module
    print("Testing Match Analysis Module...")
    from utils.rally_detector import RallyDetector
    from utils.heatmap_generator import HeatmapGenerator
    from utils.performance_drift import PerformanceDriftTracker
    from utils.match_timeline import MatchTimelineBuilder
    
    rd = RallyDetector(fps=30.0)
    hg = HeatmapGenerator(frame_w=1920, frame_h=1080)
    pdt = PerformanceDriftTracker()
    mtb = MatchTimelineBuilder(video_id="smoke_test", fps=30.0)
    
    # Dummy update cycle
    t_roles = {1: 'setter', 2: 'hitter'}
    t_states = {
        1: {'vy': 3.0, 'court_zone': 'back', 'bbox': [100, 100, 200, 200]},
        2: {'vy': 6.0, 'court_zone': 'mid', 'bbox': [500, 500, 600, 600]}
    }
    res = rd.process_frame(1, t_roles, t_states)
    hg.update(1, 150, 150)
    pdt.update(2, 1, {'jump_height_normalised': 0.45, 'vy': 6.0})
    mtb.update(1, res, t_roles, {})
    
    print("  Rally Detector active:", res['rally_active'])
    print("  Heatmap peak zone:", hg.to_dict(1)['peak_zone'])
    
    # 4. Test Recruiter Comparison Module
    print("Testing Recruiter Comparison Module...")
    from utils.player_aggregator import PlayerAggregator
    from utils.head_to_head import HeadToHeadComparator
    from utils.report_generator import ReportGenerator
    
    agg = PlayerAggregator()
    # Create a dummy JSON for testing
    dummy_json = {
        "video_id": "test",
        "players": {
            "201": {
                "role": "hitter",
                "frames_analysed": 100,
                "biomechanics": {"arm_cock_angle": 170, "jump_height_normalised": 0.4},
                "fivb_score": 80,
                "jump_event_count": 10,
                "spike_event_count": 8
            }
        }
    }
    
    import json
    with open('data/recruiter_outputs/dummy_smoke_recruiter.json', 'w') as f:
        json.dump(dummy_json, f)
        
    agg.ingest_recruiter_json('data/recruiter_outputs/dummy_smoke_recruiter.json')
    ranked = agg.rank_players(top_n=1)
    
    print(f"  Ranked player 1 ID: {ranked[0]['track_id']}")
    assert ranked[0]['track_id'] == "201"
    
    comp = HeadToHeadComparator(agg)
    rep = ReportGenerator(agg, comp)
    print("  Comparator and Report Generator instantiated.")
    
    print("Smoke Test PASSED!")

if __name__ == "__main__":
    smoke_test()
