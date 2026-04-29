import os
import json
import numpy as np
from datetime import datetime

# Custom JSON encoder for numpy types
class NumpyEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, (np.integer, np.int32, np.int64)):
            return int(obj)
        elif isinstance(obj, (np.floating, np.float32, np.float64)):
            return float(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        elif isinstance(obj, np.bool_):
            return bool(obj)
        return super().default(obj)

from url_loader import load_urls
from youtube_downloader import download_video
from pose_extractor import extract_pose

BASE_DIR = "C:/sportsai-backend"
CSV_PATH = os.path.join(BASE_DIR, "data/input/volleyball_urls.csv")
POSE_OUTPUT_DIR = os.path.join(BASE_DIR, "data/pose_data/volleyball")
METADATA_PATH = os.path.join(POSE_OUTPUT_DIR, "metadata.json")


def load_metadata() -> dict:
    if os.path.exists(METADATA_PATH):
        with open(METADATA_PATH) as f:
            return json.load(f)
    return {"processed": [], "failed": [], "last_updated": None}


def save_metadata(meta: dict):
    meta["last_updated"] = datetime.now().isoformat()
    with open(METADATA_PATH, "w") as f:
        json.dump(meta, f, indent=2, cls=NumpyEncoder)


def process_batch(csv_path: str = CSV_PATH):
    rows = load_urls(csv_path)

    # Deduplicate — first occurrence of each URL wins, rest are skipped
    seen_urls = {}
    deduped = []
    for row in rows:
        url = row["url"].strip()
        if url not in seen_urls:
            seen_urls[url] = True
            deduped.append(row)
        else:
            print(f"[DUPLICATE] Skipping repeated URL: {url}")
    rows = deduped

    total = len(rows)
    metadata = load_metadata()
    processed_urls = {r["url"] for r in metadata["processed"]}

    for i, row in enumerate(rows, start=1):
        url = row["url"]
        technique = row["technique"]
        skill_level = row["skill_level"]
        channel = row["source_channel"]

        if url in processed_urls:
            print(f"[SKIP] {i}/{total}: already processed - {url}")
            continue

        safe_name = f"vb_{technique}_{skill_level}_{i}"
        print(f"[{i}/{total}] {technique} [{skill_level}] from {channel}")

        try:
            dl = download_video(url, safe_name)
            print(f"  Downloaded: {dl['resolution']}, {dl['duration']}s")
            result = extract_pose(dl["file_path"], technique)
            frames = len(result["pose_sequence_3d"])
            conf = result["average_confidence"]
            print(f"  Extracted: {frames} frames, conf={conf:.2f}")

            out_dir = os.path.join(POSE_OUTPUT_DIR, technique)
            os.makedirs(out_dir, exist_ok=True)
            np.save(os.path.join(out_dir, f"{safe_name}_pose3d.npy"), result["pose_sequence_3d"])
            with open(os.path.join(out_dir, f"{safe_name}_biomechanics.json"), "w") as f:
                json.dump(result["biomechanics"], f, indent=2, cls=NumpyEncoder)

            metadata["processed"].append({
                "url": url,
                "technique": technique,
                "skill_level": skill_level,
                "source_channel": channel,
                "frames": frames,
                "confidence": conf,
                "pose_file": f"{safe_name}_pose3d.npy",
                "biomechanics_file": f"{safe_name}_biomechanics.json",
                "timestamp": datetime.now().isoformat(),
            })

            os.remove(dl["file_path"])
            print(f"  [DONE]")

        except KeyboardInterrupt:
            print("\n[STOPPED] Batch interrupted by user. Progress saved.")
            break
        except Exception as e:
            print(f"  [ERROR] {e}")
            metadata["failed"].append({
                "url": url,
                "error": str(e),
                "timestamp": datetime.now().isoformat(),
            })

        save_metadata(metadata)

    print(f"\n[COMPLETE] {len(metadata['processed'])} processed, {len(metadata['failed'])} failed")


if __name__ == "__main__":
    import sys
    csv = sys.argv[1] if len(sys.argv) > 1 else CSV_PATH
    process_batch(csv)
