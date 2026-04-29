"""
Test script for Telescopic Pipeline implementation.

Tests all three fixes:
1. Spatial cropping (distance problem)
2. Explosive vertical velocity (athlete lock)
3. Adaptive sampling (sampling rate trap)

Usage:
    python test_telescopic_pipeline.py --video path/to/video.mp4 --technique spike
"""
import argparse
import sys
import os
import json

# Add data_collection to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'data_collection'))

def test_spatial_cropping(video_path: str, technique: str):
    """Test that spatial cropping improves pose confidence."""
    from pose_extractor import extract_pose
    
    print("\n" + "="*70)
    print("TEST 1: SPATIAL CROPPING (Distance Problem Fix)")
    print("="*70)
    
    try:
        result = extract_pose(video_path, technique, skip_quality_check=True)
        
        confidence = result['average_confidence']
        frames = len(result['pose_sequence_2d'])
        
        print(f"✅ Pose extraction successful")
        print(f"   - Average confidence: {confidence:.1%}")
        print(f"   - Frames processed: {frames}")
        print(f"   - Localisation method: {result['localisation']['method']}")
        
        if confidence >= 0.85:
            print(f"   ✅ PASS: Confidence ≥85% (spatial cropping working)")
        elif confidence >= 0.75:
            print(f"   ⚠️  WARN: Confidence 75-85% (marginal improvement)")
        else:
            print(f"   ❌ FAIL: Confidence <75% (spatial cropping may not be working)")
        
        return result
        
    except Exception as e:
        print(f"❌ FAIL: {e}")
        return None


def test_athlete_lock(video_path: str, technique: str):
    """Test that explosive Vy correctly identifies the athlete."""
    from smart_analyser import analyse_video_auto
    
    print("\n" + "="*70)
    print("TEST 2: EXPLOSIVE VERTICAL VELOCITY (Athlete Lock Fix)")
    print("="*70)
    
    try:
        result = analyse_video_auto(video_path, athlete_id="test_user")
        
        if not result['segments']:
            print(f"❌ FAIL: No segments detected (athlete lock may have failed)")
            return None
        
        detected_techniques = [s['technique'] for s in result['segments']]
        print(f"✅ Athlete lock successful")
        print(f"   - Techniques detected: {detected_techniques}")
        print(f"   - Segments found: {len(result['segments'])}")
        
        # Check if the requested technique was found
        if technique in detected_techniques:
            print(f"   ✅ PASS: Correct technique '{technique}' detected")
        else:
            print(f"   ⚠️  WARN: Technique '{technique}' not found (may be wrong video)")
        
        return result
        
    except Exception as e:
        print(f"❌ FAIL: {e}")
        return None


def test_adaptive_sampling(video_path: str):
    """Test that adaptive sampling captures high-velocity moments."""
    from smart_analyser import _kinematic_scan
    import cv2
    
    print("\n" + "="*70)
    print("TEST 3: ADAPTIVE SAMPLING (Sampling Rate Trap Fix)")
    print("="*70)
    
    try:
        cap = cv2.VideoCapture(video_path)
        fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        cap.release()
        
        action_scan, events = _kinematic_scan(video_path, fps, total_frames)
        
        print(f"✅ Adaptive sampling successful")
        print(f"   - Source: {action_scan.get('source', 'unknown')}")
        print(f"   - Events detected: {len(events)}")
        print(f"   - Action counts: {action_scan.get('action_counts', {})}")
        
        if 'adaptive' in action_scan.get('source', ''):
            print(f"   ✅ PASS: Adaptive sampling active")
        else:
            print(f"   ⚠️  WARN: May be using fixed sampling")
        
        if events:
            print(f"   ✅ PASS: Events detected (no aliasing)")
        else:
            print(f"   ❌ FAIL: No events detected (may have missed impact)")
        
        return action_scan
        
    except Exception as e:
        print(f"❌ FAIL: {e}")
        return None


def run_full_test(video_path: str, technique: str):
    """Run all three tests and generate report."""
    print("\n" + "="*70)
    print("TELESCOPIC PIPELINE TEST SUITE")
    print("="*70)
    print(f"Video: {video_path}")
    print(f"Technique: {technique}")
    
    # Test 1: Spatial Cropping
    pose_result = test_spatial_cropping(video_path, technique)
    
    # Test 2: Athlete Lock
    analysis_result = test_athlete_lock(video_path, technique)
    
    # Test 3: Adaptive Sampling
    sampling_result = test_adaptive_sampling(video_path)
    
    # Generate summary
    print("\n" + "="*70)
    print("TEST SUMMARY")
    print("="*70)
    
    tests_passed = 0
    tests_total = 3
    
    if pose_result and pose_result['average_confidence'] >= 0.85:
        print("✅ Spatial Cropping: PASS")
        tests_passed += 1
    else:
        print("❌ Spatial Cropping: FAIL")
    
    if analysis_result and analysis_result['segments']:
        print("✅ Athlete Lock: PASS")
        tests_passed += 1
    else:
        print("❌ Athlete Lock: FAIL")
    
    if sampling_result and sampling_result.get('events'):
        print("✅ Adaptive Sampling: PASS")
        tests_passed += 1
    else:
        print("❌ Adaptive Sampling: FAIL")
    
    print(f"\nOverall: {tests_passed}/{tests_total} tests passed")
    
    if tests_passed == tests_total:
        print("\n🎉 SUCCESS: Telescopic pipeline fully operational!")
        print("   'Bad results' → 'Elite analysis' transformation complete.")
    elif tests_passed >= 2:
        print("\n⚠️  PARTIAL: Most features working, some issues remain.")
    else:
        print("\n❌ FAILURE: Major issues detected, review implementation.")
    
    return tests_passed == tests_total


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Test Telescopic Pipeline")
    parser.add_argument("--video", required=True, help="Path to test video")
    parser.add_argument("--technique", default="spike", 
                       choices=["spike", "serve", "block", "dig"],
                       help="Technique to test")
    
    args = parser.parse_args()
    
    if not os.path.exists(args.video):
        print(f"❌ Error: Video file not found: {args.video}")
        sys.exit(1)
    
    success = run_full_test(args.video, args.technique)
    sys.exit(0 if success else 1)
