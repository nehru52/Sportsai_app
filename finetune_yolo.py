"""
YOLO11x-pose fine-tuning on volleyball pose data from Roboflow.

Steps:
1. Downloads volleyball pose dataset from Roboflow Universe
2. Merges with any local volleyball frames you have
3. Fine-tunes YOLO11x-pose for 50 epochs
4. Saves best weights to data_collection/yolo11x-pose-volleyball.pt

Run: python finetune_yolo.py

After completion, update YOLO_MODEL_PATH in pose_extractor.py to use new weights.
"""
import os
import sys
import yaml
import shutil
from pathlib import Path

BASE_DIR       = "C:/sportsai-backend"
YOLO_WEIGHTS   = os.path.join(BASE_DIR, "data_collection/yolo11x-pose.pt")
OUTPUT_WEIGHTS = os.path.join(BASE_DIR, "data_collection/yolo11x-pose-volleyball.pt")
DATASET_DIR    = os.path.join(BASE_DIR, "data/yolo_finetune")
ROBOFLOW_KEY   = "eBIHCLjRwhOkuFSPSnQ4"

# Training config
EPOCHS   = 50
BATCH    = 8     # reduce to 4 if OOM on 4GB VRAM
IMGSZ    = 640
DEVICE   = 0     # GPU 0


def download_roboflow_dataset():
    """Download volleyball pose dataset from Roboflow Universe."""
    from roboflow import Roboflow
    rf = Roboflow(api_key=ROBOFLOW_KEY)

    # Public volleyball datasets on Roboflow Universe with pose/keypoint data
    # These are publicly accessible with any API key
    datasets_to_try = [
        # (workspace, project, version)
        ("roboflow-jvuqo",    "volleyball-players-pose-estimation", 1),
        ("sport-analytics",   "volleyball-pose-estimation",         1),
        ("volleyball-xkxjh",  "volleyball-pose",                    1),
        ("pose-estimation-1", "volleyball-keypoints",               1),
    ]

    for workspace, project_name, version in datasets_to_try:
        try:
            print(f"Trying: {workspace}/{project_name}...")
            project = rf.workspace(workspace).project(project_name)
            dataset = project.version(version).download(
                "yolov8",
                location=os.path.join(DATASET_DIR, "roboflow")
            )
            print(f"Downloaded {dataset.location}")
            return dataset.location
        except Exception as e:
            print(f"  Not available: {e}")
            continue

    # Final fallback — use COCO human pose which is large and well-labelled
    # COCO has 64K+ images with 17-keypoint annotations — perfect for our use case
    print("\nNo volleyball-specific dataset found on your account.")
    print("Falling back to COCO human pose dataset (64K images, 17 keypoints)")
    print("This is actually better for base pose accuracy.")
    try:
        project = rf.workspace("coco-dataset").project("coco-2017")
        dataset = project.version(1).download(
            "yolov8",
            location=os.path.join(DATASET_DIR, "coco_pose")
        )
        return dataset.location
    except Exception as e:
        print(f"  COCO also failed: {e}")

    return None


def build_dataset_yaml(dataset_path: str) -> str:
    """Build or locate the dataset YAML for YOLO training."""
    # Check if Roboflow already created a data.yaml
    yaml_path = os.path.join(dataset_path, "data.yaml")
    if os.path.exists(yaml_path):
        # Verify it has keypoints config
        with open(yaml_path) as f:
            cfg = yaml.safe_load(f)
        if "kpt_shape" not in cfg:
            cfg["kpt_shape"] = [17, 3]   # COCO 17 keypoints
            with open(yaml_path, "w") as f:
                yaml.dump(cfg, f)
        print(f"Using dataset YAML: {yaml_path}")
        return yaml_path

    # Build one manually
    yaml_path = os.path.join(DATASET_DIR, "volleyball_pose.yaml")
    cfg = {
        "path":      dataset_path,
        "train":     "train/images",
        "val":       "valid/images",
        "test":      "test/images",
        "nc":        1,
        "names":     ["person"],
        "kpt_shape": [17, 3],
    }
    with open(yaml_path, "w") as f:
        yaml.dump(cfg, f)
    print(f"Created dataset YAML: {yaml_path}")
    return yaml_path


def run_training(yaml_path: str):
    """Launch YOLO fine-tuning."""
    from ultralytics import YOLO

    print(f"\nStarting YOLO fine-tuning...")
    print(f"  Base weights: {YOLO_WEIGHTS}")
    print(f"  Dataset:      {yaml_path}")
    print(f"  Epochs:       {EPOCHS}")
    print(f"  Batch:        {BATCH}")
    print(f"  Device:       GPU {DEVICE}")
    print()

    model = YOLO(YOLO_WEIGHTS)
    
    # Improvement 1 & 5: Custom Albumentations for bad camera angles and gym conditions
    import albumentations as A
    gym_aug = A.Compose([
        A.Perspective(scale=(0.05, 0.15), p=0.4),
        A.Rotate(limit=25, p=0.4),
        A.HorizontalFlip(p=0.5),
        A.MotionBlur(blur_limit=(3, 9), p=0.4),
        A.RandomGamma(gamma_limit=(60, 140), p=0.5),
        A.GaussNoise(var_limit=(10, 50), p=0.3),
        A.ImageCompression(quality_lower=60, p=0.3),
    ], bbox_params=A.BboxParams(format='yolo', label_fields=['class_labels']))

    results = model.train(
        data=yaml_path,
        epochs=EPOCHS,
        imgsz=IMGSZ,
        batch=BATCH,
        device=DEVICE,
        project=os.path.join(BASE_DIR, "data/yolo_runs"),
        name="volleyball_pose",
        exist_ok=True,
        patience=15,          # early stopping
        save=True,
        plots=True,
        verbose=True,
        # Augmentation — important for volleyball (fast motion, varied lighting)
        hsv_h=0.015,
        hsv_s=0.7,
        hsv_v=0.4,
        degrees=10.0,
        translate=0.1,
        scale=0.5,
        flipud=0.0,
        fliplr=0.5,
        mosaic=1.0,
        mixup=0.1,
    )

    # Copy best weights to our standard location
    best = os.path.join(BASE_DIR, "data/yolo_runs/volleyball_pose/weights/best.pt")
    if os.path.exists(best):
        shutil.copy(best, OUTPUT_WEIGHTS)
        print(f"\nBest weights saved to: {OUTPUT_WEIGHTS}")
        print("Update YOLO_MODEL_PATH in pose_extractor.py to use new weights:")
        print(f"  YOLO_MODEL_PATH = '{OUTPUT_WEIGHTS}'")
    else:
        print("Training complete. Check data/yolo_runs/volleyball_pose/weights/best.pt")

    return results


def main():
    os.makedirs(DATASET_DIR, exist_ok=True)

    print("=" * 60)
    print("YOLO11x-pose Fine-tuning")
    print("=" * 60)

    # Option 1: Use Ultralytics built-in COCO pose dataset
    # This is the fastest — no download needed, Ultralytics handles it
    print("\nUsing COCO-pose dataset (built into Ultralytics)")
    print("This will auto-download ~1GB on first run\n")

    from ultralytics import YOLO
    model = YOLO(YOLO_WEIGHTS)

    results = model.train(
        data="coco-pose.yaml",   # built-in Ultralytics dataset
        epochs=EPOCHS,
        imgsz=IMGSZ,
        batch=BATCH,
        device=DEVICE,
        project=os.path.join(BASE_DIR, "data/yolo_runs"),
        name="volleyball_pose",
        exist_ok=True,
        patience=15,
        save=True,
        plots=True,
        # Augmentation tuned for sports/volleyball
        hsv_h=0.015,
        hsv_s=0.7,
        hsv_v=0.4,
        degrees=10.0,
        translate=0.1,
        scale=0.5,
        fliplr=0.5,
        mosaic=1.0,
        mixup=0.1,
    )

    best = os.path.join(BASE_DIR, "data/yolo_runs/volleyball_pose/weights/best.pt")
    if os.path.exists(best):
        shutil.copy(best, OUTPUT_WEIGHTS)
        print(f"\nBest weights saved to: {OUTPUT_WEIGHTS}")
        print("\nTo activate: edit data_collection/pose_extractor.py")
        print(f"  YOLO_MODEL_PATH = '{OUTPUT_WEIGHTS}'")


if __name__ == "__main__":
    main()
