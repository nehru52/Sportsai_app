"""
Simple in-memory job queue for async video processing.
For production, use Redis + Celery or similar.
"""
import threading
import uuid
from typing import Dict, Any
from datetime import datetime

# In-memory job storage
jobs: Dict[str, Dict[str, Any]] = {}
job_lock = threading.Lock()


def create_job(video_path: str, technique: str, athlete_id: str = None) -> str:
    """Create a new job and return job ID."""
    job_id = str(uuid.uuid4())
    
    with job_lock:
        jobs[job_id] = {
            "id": job_id,
            "status": "pending",
            "video_path": video_path,
            "technique": technique,
            "athlete_id": athlete_id,
            "created_at": datetime.now().isoformat(),
            "progress": 0,
            "result": None,
            "error": None,
        }
    
    return job_id


def get_job(job_id: str) -> Dict[str, Any]:
    """Get job status and result."""
    with job_lock:
        return jobs.get(job_id, {"status": "not_found"})


def update_job(job_id: str, **kwargs):
    """Update job fields."""
    with job_lock:
        if job_id in jobs:
            jobs[job_id].update(kwargs)


def process_job_async(job_id: str):
    """Process job in background thread."""
    from smart_analyser import analyse_video_auto
    import os
    
    job = get_job(job_id)
    if job["status"] == "not_found":
        return
    
    update_job(job_id, status="processing", progress=10)
    
    try:
        # Run analysis
        result = analyse_video_auto(
            job["video_path"],
            athlete_id=job["athlete_id"]
        )
        
        update_job(
            job_id,
            status="completed",
            progress=100,
            result=result,
            completed_at=datetime.now().isoformat()
        )
        
    except Exception as e:
        update_job(
            job_id,
            status="failed",
            error=str(e),
            completed_at=datetime.now().isoformat()
        )
    
    finally:
        # Clean up temp file
        try:
            if os.path.exists(job["video_path"]):
                os.remove(job["video_path"])
        except:
            pass


def start_job(job_id: str):
    """Start processing job in background thread."""
    thread = threading.Thread(target=process_job_async, args=(job_id,))
    thread.daemon = True
    thread.start()
