import time
import os
import sys
from r2_storage import download_video, upload_output
import redis

# Connect to Redis (queue service)
# Connect to Redis (queue service) - HARDCODED FOR TESTING
REDIS_URL = "rediss://default:gQAAAAAAAX6eAAIncDIyOWNhN2MzOWUxNDk0MmVhYjAzZTIzN2RkNGM5ZDg1Y3AyOTc5NTA@pro-lemur-97950.upstash.io:6379"
r = redis.Redis.from_url(
    REDIS_URL, 
    ssl_cert_reqs=None,
    socket_keepalive=True,
    socket_connect_timeout=30,
    retry_on_timeout=True,
    decode_responses=True
)
def process_video(filename):
    """Your AI processing logic - customize this"""
    local_path = f"/tmp/{filename}"
    output_path = f"/tmp/processed_{filename}"
    
    try:
        # 1. Download from R2
        print(f"[WORKER] Downloading {filename} from R2...")
        download_video(filename, local_path)
        
        # 2. TODO: Add your AI processing here
        # - VideoMAE analysis
        # - ViTPose keypoint extraction  
        # - Biomechanical calculations
        print(f"[WORKER] Processing {filename} with AI engine...")
        
        # Placeholder: Copy file as "processed" (replace with real logic)
        import shutil
        shutil.copy(local_path, output_path)
        
        # 3. Upload result back to R2
        output_key = f"results/{filename}"
        print(f"[WORKER] Uploading result to {output_key}...")
        upload_output(output_path, output_key)
        
        # 4. Mark job complete in Redis
        job_id = filename.replace('.mp4', '').replace('.mov', '')
        r.set(f"job:{job_id}:status", "complete")
        r.set(f"job:{job_id}:output", output_key)
        
        print(f"[WORKER] ✅ Completed {filename}")
        
    except Exception as e:
        print(f"[WORKER] ❌ Error processing {filename}: {e}")
        # Mark failed
        job_id = filename.replace('.mp4', '').replace('.mov', '')
        r.set(f"job:{job_id}:status", "failed")
        r.set(f"job:{job_id}:error", str(e))
    
    finally:
        # Cleanup temp files
        if os.path.exists(local_path):
            os.remove(local_path)
        if os.path.exists(output_path):
            os.remove(output_path)

print("[WORKER] 🚀 SportsAI Worker started")
print(f"[WORKER] Connected to Redis at {REDIS_URL}")

while True:
    try:
        # Check for new jobs in queue
        job = r.brpop("video_queue", timeout=5)
        
        if job:
            # job is (queue_name, filename)
            filename = job[1].decode()
            print(f"[WORKER] New job received: {filename}")
            process_video(filename)
        else:
            # No jobs, just keep polling
            pass
            
    except Exception as e:
        print(f"[WORKER] ❌ Queue error: {e}")
        time.sleep(5)