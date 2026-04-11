import sys, os, json, numpy as np
sys.path.insert(0, "C:/sportsai-backend/data_collection")
from pose_extractor import _extract_biomechanics

BASE_DIR = "C:/sportsai-backend"
POSE_DIR = os.path.join(BASE_DIR, "data/pose_data/volleyball")
meta     = json.load(open(os.path.join(POSE_DIR, "metadata.json")))

updated, errors = 0, 0
for r in meta["processed"]:
    tech = r["technique"]
    path = os.path.join(POSE_DIR, tech, r["pose_file"])
    bio  = os.path.join(POSE_DIR, tech, r["biomechanics_file"])
    if not os.path.exists(path): continue
    try:
        seq = np.load(path).astype(np.float32)
        with open(bio, "w") as f:
            json.dump(_extract_biomechanics(seq, tech, 30.0), f, indent=2)
        updated += 1
    except Exception as e:
        errors += 1; print(f"ERROR {r['pose_file']}: {e}")

print(f"Done. Updated: {updated}, Errors: {errors}")
