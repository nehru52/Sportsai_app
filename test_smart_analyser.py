
import os
import sys
import json

# Add data_collection to path
sys.path.insert(0, os.path.join(os.getcwd(), "data_collection"))

from smart_analyser import analyse_video_auto

def test_fallback():
    # Use the closest matching video found in sample/
    video_path = "sample/YTDown.com_Shorts_5-5-Spiker-with-10ft-vertical-reach_Media_wPRMQ5GhbXM_001_720p.mp4"
    
    if not os.path.exists(video_path):
        print(f"ERROR: Video file not found at {video_path}")
        return

    print(f"Starting analysis for: {video_path}")
    try:
        result = analyse_video_auto(video_path)
        
        print("\n--- FINAL JSON OUTPUT (Summary) ---")
        print(json.dumps(result.get("summary", {}), indent=2))
        
        if result.get("segments"):
            print("\n--- DETECTED TECHNIQUES ---")
            for i, seg in enumerate(result["segments"]):
                print(f"Segment {i+1}: {seg['technique']} ({seg['start_time']} - {seg['end_time']})")
        else:
            print("\nNo segments detected.")
            
    except Exception as e:
        print(f"An error occurred during analysis: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_fallback()
