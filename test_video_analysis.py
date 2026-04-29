#!/usr/bin/env python3
"""
Quick diagnostic test for video analysis
Tests each component to find where the failure is
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "data_collection"))

def test_yolo():
    """Test if YOLO model loads"""
    print("1. Testing YOLO model loading...")
    try:
        from pose_extractor import _get_yolo
        yolo = _get_yolo()
        print("   ✅ YOLO model loaded successfully")
        return True
    except Exception as e:
        print(f"   ❌ YOLO failed: {e}")
        return False

def test_video_quality(video_path):
    """Test video quality check"""
    print(f"\n2. Testing video quality check on: {video_path}")
    try:
        from video_quality import check_video_quality
        quality = check_video_quality(video_path, run_person_check=False)
        print(f"   Quality OK: {quality.ok}")
        print(f"   Issues: {quality.issues}")
        print(f"   Recommendations: {quality.recommendations}")
        if quality.ok:
            print("   ✅ Video quality passed")
        else:
            print("   ⚠️  Video quality issues found")
        return quality
    except Exception as e:
        print(f"   ❌ Quality check failed: {e}")
        import traceback
        traceback.print_exc()
        return None

def test_action_detection(video_path):
    """Test action detection"""
    print(f"\n3. Testing action detection...")
    try:
        from action_detector import detect_actions
        result = detect_actions(video_path)
        events = result.get("events", [])
        print(f"   Events detected: {len(events)}")
        print(f"   Action counts: {result.get('action_counts', {})}")
        if events:
            print("   ✅ Actions detected")
            for event in events[:3]:  # Show first 3
                print(f"      - {event['action']} at frame {event['frame']} (conf: {event.get('confidence', 0):.2f})")
        else:
            print("   ⚠️  No actions detected by VolleyVision")
        return result
    except Exception as e:
        print(f"   ❌ Action detection failed: {e}")
        import traceback
        traceback.print_exc()
        return None

def test_kinematic_scan(video_path):
    """Test kinematic fallback scanner"""
    print(f"\n4. Testing kinematic fallback scanner...")
    try:
        import cv2
        cap = cv2.VideoCapture(video_path)
        fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        cap.release()
        
        from smart_analyser import _kinematic_scan
        action_scan, events = _kinematic_scan(video_path, fps, total_frames)
        
        print(f"   Events detected: {len(events)}")
        print(f"   Action counts: {action_scan.get('action_counts', {})}")
        print(f"   Dominant action: {action_scan.get('dominant_action')}")
        
        if events:
            print("   ✅ Kinematic scanner found actions")
            for event in events[:3]:
                print(f"      - {event['action']} at frame {event['frame']} (conf: {event.get('confidence', 0):.2f})")
        else:
            print("   ❌ Kinematic scanner found nothing")
        
        return action_scan, events
    except Exception as e:
        print(f"   ❌ Kinematic scan failed: {e}")
        import traceback
        traceback.print_exc()
        return None, []

def test_pose_extraction(video_path, technique="spike"):
    """Test pose extraction on a short clip"""
    print(f"\n5. Testing pose extraction (first 3 seconds)...")
    try:
        import cv2
        import tempfile
        
        # Extract first 3 seconds
        cap = cv2.VideoCapture(video_path)
        fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
        frames_to_extract = int(fps * 3)
        
        temp_clip = tempfile.mktemp(suffix=".mp4")
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out = cv2.VideoWriter(temp_clip, fourcc, fps, 
                             (int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
                              int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))))
        
        for i in range(frames_to_extract):
            ret, frame = cap.read()
            if not ret:
                break
            out.write(frame)
        
        cap.release()
        out.release()
        
        # Try pose extraction
        from pose_extractor import extract_pose
        result = extract_pose(temp_clip, technique, skip_quality_check=True)
        
        print(f"   Frames analyzed: {len(result['pose_sequence_3d'])}")
        print(f"   Average confidence: {result['average_confidence']:.2%}")
        
        if len(result['pose_sequence_3d']) > 0:
            print("   ✅ Pose extraction working")
        else:
            print("   ❌ No poses extracted")
        
        os.remove(temp_clip)
        return result
    except Exception as e:
        print(f"   ❌ Pose extraction failed: {e}")
        import traceback
        traceback.print_exc()
        return None

def main():
    print("="*60)
    print("SportsAI Video Analysis Diagnostic")
    print("="*60)
    
    # Check if video path provided
    if len(sys.argv) < 2:
        print("\n❌ No video path provided")
        print("\nUsage: python test_video_analysis.py <path_to_video>")
        print("\nExample:")
        print("  python test_video_analysis.py data/raw_videos/spike.mp4")
        return
    
    video_path = sys.argv[1]
    
    if not os.path.exists(video_path):
        print(f"\n❌ Video not found: {video_path}")
        return
    
    print(f"\nVideo: {video_path}")
    print(f"Size: {os.path.getsize(video_path) / (1024*1024):.2f} MB")
    
    # Run tests
    yolo_ok = test_yolo()
    if not yolo_ok:
        print("\n⛔ YOLO model failed to load - cannot continue")
        return
    
    quality = test_video_quality(video_path)
    action_result = test_action_detection(video_path)
    kinematic_result, kinematic_events = test_kinematic_scan(video_path)
    
    # If no actions detected, try pose extraction anyway
    if not action_result or not action_result.get("events"):
        if not kinematic_events:
            print("\n⚠️  No actions detected by either method")
            print("   Trying direct pose extraction...")
            pose_result = test_pose_extraction(video_path)
    
    print("\n" + "="*60)
    print("DIAGNOSTIC SUMMARY")
    print("="*60)
    
    if quality and not quality.ok:
        print("❌ Video quality issues detected")
        print(f"   Issues: {', '.join(quality.issues)}")
        print(f"   Recommendations: {', '.join(quality.recommendations)}")
    
    if not action_result or not action_result.get("events"):
        if not kinematic_events:
            print("❌ No techniques detected by any method")
            print("\nPossible causes:")
            print("  1. Video is too short (need at least 2-3 seconds)")
            print("  2. Athlete not clearly visible")
            print("  3. No clear volleyball technique being performed")
            print("  4. Camera angle too extreme")
            print("  5. Heavy occlusion or poor lighting")
        else:
            print("✅ Kinematic fallback detected actions")
            print(f"   Found: {', '.join(kinematic_result.get('action_counts', {}).keys())}")
    else:
        print("✅ Actions detected successfully")
        print(f"   Found: {', '.join(action_result.get('action_counts', {}).keys())}")
    
    print("\n" + "="*60)

if __name__ == "__main__":
    main()
