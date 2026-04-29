#!/usr/bin/env python3
"""
Test the user's specific video through the full analysis pipeline
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "data_collection"))

from smart_analyser import analyse_video_auto
import json

video_path = r"C:\Users\nehru\Downloads\YTDown.com_Shorts_volleyball-training-Spike_Media_xnX6X0PCD1o_001_720p.mp4"

print("="*60)
print("Testing User's Video Through Full Pipeline")
print("="*60)
print(f"\nVideo: {video_path}")
print(f"Size: {os.path.getsize(video_path) / (1024*1024):.2f} MB")

print("\n🚀 Running full analysis...")
print("-"*60)

try:
    result = analyse_video_auto(video_path, athlete_id="test_user")
    
    print("\n" + "="*60)
    print("ANALYSIS RESULT")
    print("="*60)
    
    # Print summary
    if result.get("bad_video_advice"):
        print(f"\n❌ Bad Video: {result['bad_video_advice']}")
    else:
        print(f"\n✅ Video Quality: OK")
    
    # Print timeline
    timeline = result.get("timeline", [])
    print(f"\n📋 Timeline: {len(timeline)} segments detected")
    for seg in timeline:
        print(f"   - {seg['technique']}: {seg['start_time']} to {seg['end_time']} (conf: {seg.get('detection_confidence', 0):.2f})")
    
    # Print segments with analysis
    segments = result.get("segments", [])
    print(f"\n🔬 Segments Analyzed: {len(segments)}")
    for i, seg in enumerate(segments, 1):
        print(f"\n   Segment {i}: {seg['technique']}")
        if seg.get("analysis"):
            print(f"      Verdict: {seg['analysis']['verdict']}")
            print(f"      Score: {seg['analysis']['score']}")
            print(f"      Confidence: {seg['analysis']['confidence']:.2%}")
        elif seg.get("skip_reason"):
            print(f"      Skipped: {seg['skip_reason']}")
        else:
            print(f"      ⚠️ No analysis data")
    
    # Print summary
    summary = result.get("summary", {})
    if summary:
        print(f"\n📊 Summary:")
        print(f"   Overall Verdict: {summary.get('overall_verdict', 'N/A')}")
        print(f"   Techniques Detected: {summary.get('techniques_detected', [])}")
        print(f"   Techniques Analysed: {summary.get('techniques_analysed', [])}")
        print(f"   Top Strength: {summary.get('top_strength', 'N/A')}")
        print(f"   Top Priority: {summary.get('top_priority', 'N/A')}")
        print(f"   Metrics: {summary.get('metrics_good', 0)}/{summary.get('metrics_total', 0)} good")
    
    # Save full result
    with open("test_user_video_result.json", "w") as f:
        json.dump(result, f, indent=2, default=str)
    print(f"\n💾 Full result saved to: test_user_video_result.json")
    
    print("\n" + "="*60)
    
    # Determine if it worked
    if result.get("bad_video_advice"):
        print("❌ FAILED: Video quality issues")
    elif not segments:
        print("❌ FAILED: No segments detected")
    elif not any(s.get("analysis") for s in segments):
        print("❌ FAILED: Segments detected but no analysis completed")
    else:
        print("✅ SUCCESS: Analysis completed!")
    
except Exception as e:
    print(f"\n❌ ERROR: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "="*60)
