"""
Diagnostic script to check why a video fails analysis.
Helps identify issues with pose detection, video quality, etc.
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'data_collection'))

import cv2
import numpy as np
from pose_extractor import _get_yolo, CONFIDENCE_THRESHOLD, _DEVICE
from video_quality import check_video_quality
from action_localiser import localise_technique

def diagnose_video(video_path: str, technique: str = "spike"):
    """Run comprehensive diagnostics on a video."""
    
    print("="*70)
    print("VIDEO DIAGNOSTICS")
    print("="*70)
    print(f"Video: {video_path}")
    print(f"Technique: {technique}")
    print()
    
    # 1. Basic video info
    print("1. BASIC VIDEO INFO")
    print("-"*70)
    cap = cv2.VideoCapture(video_path)
    fps = cap.get(cv2.CAP_PROP_FPS)
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    duration = total_frames / fps if fps > 0 else 0
    cap.release()
    
    print(f"Resolution: {width}x{height}")
    print(f"FPS: {fps:.2f}")
    print(f"Total Frames: {total_frames}")
    print(f"Duration: {duration:.2f} seconds")
    print()
    
    # 2. Video quality check
    print("2. VIDEO QUALITY CHECK")
    print("-"*70)
    try:
        quality = check_video_quality(video_path, run_person_check=False)
        print(f"Quality OK: {quality.ok}")
        if quality.issues:
            print(f"Issues: {', '.join(quality.issues)}")
        if quality.recommendations:
            print(f"Recommendations: {', '.join(quality.recommendations)}")
    except Exception as e:
        print(f"Quality check failed: {e}")
    print()
    
    # 3. Action localisation
    print("3. ACTION LOCALISATION")
    print("-"*70)
    try:
        localisation = localise_technique(video_path, technique)
        print(f"Method: {localisation['method']}")
        print(f"Confidence: {localisation['confidence']:.2%}")
        print(f"Clip frames: {localisation['clip_frames']}")
        print(f"Clip duration: {localisation.get('clip_duration_sec', 0):.2f}s")
    except Exception as e:
        print(f"Localisation failed: {e}")
    print()
    
    # 4. Pose detection test
    print("4. POSE DETECTION TEST")
    print("-"*70)
    print(f"Confidence threshold: {CONFIDENCE_THRESHOLD}")
    print(f"Device: {_DEVICE}")
    
    yolo = _get_yolo()
    cap = cv2.VideoCapture(video_path)
    
    frames_with_person = 0
    frames_with_high_conf = 0
    frames_processed = 0
    max_people_in_frame = 0
    confidences = []
    
    # Sample every 5th frame for speed
    frame_idx = 0
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        
        if frame_idx % 5 == 0:
            frames_processed += 1
            results = yolo(frame, verbose=False, device=_DEVICE)
            
            if results and results[0].keypoints is not None:
                kps = results[0].keypoints
                if kps.conf is not None and len(kps.conf) > 0:
                    frames_with_person += 1
                    max_people_in_frame = max(max_people_in_frame, len(kps.conf))
                    
                    # Check confidence
                    for i in range(len(kps.conf)):
                        conf = float(kps.conf[i].mean())
                        confidences.append(conf)
                        if conf >= CONFIDENCE_THRESHOLD:
                            frames_with_high_conf += 1
                            break  # Only count frame once
        
        frame_idx += 1
    
    cap.release()
    
    print(f"Frames sampled: {frames_processed}")
    print(f"Frames with person detected: {frames_with_person} ({frames_with_person/frames_processed*100:.1f}%)")
    print(f"Frames with confidence ≥{CONFIDENCE_THRESHOLD}: {frames_with_high_conf} ({frames_with_high_conf/frames_processed*100:.1f}%)")
    print(f"Max people in frame: {max_people_in_frame}")
    
    if confidences:
        print(f"Average confidence: {np.mean(confidences):.2%}")
        print(f"Min confidence: {np.min(confidences):.2%}")
        print(f"Max confidence: {np.max(confidences):.2%}")
        print(f"Median confidence: {np.median(confidences):.2%}")
    else:
        print("No poses detected!")
    print()
    
    # 5. Diagnosis
    print("5. DIAGNOSIS")
    print("-"*70)
    
    issues = []
    recommendations = []
    
    if duration < 2:
        issues.append("Video is very short (<2 seconds)")
        recommendations.append("Record longer clips (3-5 seconds minimum)")
    
    if frames_with_person < frames_processed * 0.5:
        issues.append("Person not detected in most frames")
        recommendations.append("Ensure athlete is clearly visible and in frame")
    
    if frames_with_high_conf < 5:
        issues.append(f"Too few frames with confidence ≥{CONFIDENCE_THRESHOLD}")
        recommendations.append(f"Lower confidence threshold to {CONFIDENCE_THRESHOLD - 0.1:.1f}")
        recommendations.append("Improve video quality (lighting, resolution, stability)")
    
    if max_people_in_frame > 3:
        issues.append("Many people in frame (may confuse athlete detection)")
        recommendations.append("Record with fewer people in frame")
        recommendations.append("Use closer camera angle")
    
    if confidences and np.mean(confidences) < 0.6:
        issues.append("Low average confidence")
        recommendations.append("Improve lighting")
        recommendations.append("Move camera closer")
        recommendations.append("Use higher resolution")
    
    if width < 1280 or height < 720:
        issues.append("Low resolution")
        recommendations.append("Record at 720p or higher")
    
    if issues:
        print("ISSUES FOUND:")
        for i, issue in enumerate(issues, 1):
            print(f"  {i}. {issue}")
        print()
        print("RECOMMENDATIONS:")
        for i, rec in enumerate(recommendations, 1):
            print(f"  {i}. {rec}")
    else:
        print("✅ No major issues found!")
        print("The video should work with the analysis pipeline.")
    
    print()
    print("="*70)
    print("DIAGNOSIS COMPLETE")
    print("="*70)


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Diagnose video analysis issues")
    parser.add_argument("video", help="Path to video file")
    parser.add_argument("--technique", default="spike", 
                       choices=["spike", "serve", "block", "dig"],
                       help="Technique to analyze")
    
    args = parser.parse_args()
    
    if not os.path.exists(args.video):
        print(f"Error: Video file not found: {args.video}")
        sys.exit(1)
    
    diagnose_video(args.video, args.technique)
