"""
Court segmentation using VolleyVision's Roboflow model.
Project: court-segmented, version 1 (97.2% mIoU).

Returns court polygon corners and a binary mask.
"""
import base64
import os
import cv2
import numpy as np

ROBOFLOW_API_KEY = "eBIHCLjRwhOkuFSPSnQ4"
ROBOFLOW_PROJECT = "court-segmented"
ROBOFLOW_VERSION = 1

_rf_model = None


def _get_model():
    global _rf_model
    if _rf_model is None:
        from roboflow import Roboflow
        rf = Roboflow(api_key=ROBOFLOW_API_KEY)
        _rf_model = rf.workspace().project(ROBOFLOW_PROJECT).version(ROBOFLOW_VERSION).model
    return _rf_model


def _decode_mask(segmentation_mask: str, width: int, height: int) -> np.ndarray:
    decoded = base64.b64decode(segmentation_mask)
    arr = np.frombuffer(decoded, dtype=np.uint8)
    mask = cv2.imdecode(arr, cv2.IMREAD_GRAYSCALE)
    return cv2.resize(mask, (width, height))


def _mask_to_polygon(mask: np.ndarray) -> np.ndarray | None:
    """Extract the largest contour and approximate as polygon."""
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return None
    largest = max(contours, key=cv2.contourArea)
    epsilon = 0.01 * cv2.arcLength(largest, True)
    poly = cv2.approxPolyDP(largest, epsilon, True)
    return poly.reshape(-1, 2).tolist()


def detect_court_in_frame(frame: np.ndarray) -> dict:
    """
    Run court segmentation on a single BGR frame.

    Returns:
        {
          "polygon": [[x,y], ...] | None,
          "mask_area_ratio": float,   # fraction of frame covered by court
          "success": bool,
        }
    """
    model = _get_model()

    # Save frame to temp file (Roboflow SDK requires a file path)
    tmp_path = "_tmp_court_frame.jpg"
    cv2.imwrite(tmp_path, frame)

    try:
        output = model.predict(tmp_path).json()
        predictions = output.get("predictions", [])
        if not predictions:
            return {"polygon": None, "mask_area_ratio": 0.0, "success": False}

        pred = predictions[0]
        img_w = pred["image"]["width"]
        img_h = pred["image"]["height"]
        mask = _decode_mask(pred["segmentation_mask"], img_w, img_h)
        polygon = _mask_to_polygon(mask)
        area_ratio = float(np.sum(mask > 0)) / (img_w * img_h)

        return {
            "polygon": polygon,
            "mask_area_ratio": round(area_ratio, 4),
            "success": True,
        }
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


def get_homography_matrix(video_corners: list) -> np.ndarray:
    """
    Compute homography matrix from video coordinates to standard 18m x 9m court.
    
    video_corners: list of [x, y] coordinates of the 4 court corners.
    Order: Top-Left, Top-Right, Bottom-Right, Bottom-Left.
    
    Returns 3x3 homography matrix.
    """
    # Standard volleyball court dimensions (meters)
    # We use a 2D top-down view where length is 18m and width is 9m (horizontal).
    # We'll map to a coordinate system where (0,0) is top-left of the court.
    dst_pts = np.array([
        [0, 0],   # Top-Left
        [18, 0],  # Top-Right
        [18, 9],  # Bottom-Right
        [0, 9]    # Bottom-Left
    ], dtype=np.float32)
    
    src_pts = np.array(video_corners, dtype=np.float32)
    
    H, _ = cv2.findHomography(src_pts, dst_pts)
    return H


def transform_points(points: np.ndarray, H: np.ndarray) -> np.ndarray:
    """
    Apply homography transformation to a set of points.
    
    points: np.ndarray of shape (N, 2)
    H: 3x3 homography matrix
    
    Returns transformed points of shape (N, 2) in meters.
    """
    if points.size == 0:
        return points
    
    # Reshape to (N, 1, 2) for cv2.perspectiveTransform
    pts_reshaped = points.reshape(-1, 1, 2).astype(np.float32)
    transformed = cv2.perspectiveTransform(pts_reshaped, H)
    
    return transformed.reshape(-1, 2)


def order_corners(polygon: list) -> list:
    """
    Order polygon points into Top-Left, Top-Right, Bottom-Right, Bottom-Left.
    """
    pts = np.array(polygon)
    
    # Sum of coordinates: TL will have min sum, BR will have max sum
    s = pts.sum(axis=1)
    tl = pts[np.argmin(s)]
    br = pts[np.argmax(s)]
    
    # Difference of coordinates: TR will have max diff (x-y), BL will have min diff (x-y)
    diff = np.diff(pts, axis=1) # y-x
    # Actually diff = y-x. 
    # TR: (w, 0) -> y-x = -w (min)
    # BL: (0, h) -> y-x = h (max)
    tr = pts[np.argmin(diff)]
    bl = pts[np.argmax(diff)]
    
    return [tl.tolist(), tr.tolist(), br.tolist(), bl.tolist()]


def detect_court_in_video(video_path: str, sample_every_n: int = 30) -> dict:
    """
    Sample frames from a video and return the most stable court polygon.

    Args:
        video_path:     path to video file
        sample_every_n: analyse every Nth frame (default 30 = ~1/sec at 30fps)

    Returns:
        {
          "polygon": [[x,y], ...] | None,   # best detected court corners
          "frames_sampled": int,
          "frames_detected": int,
          "avg_mask_area_ratio": float,
        }
    """
    import cv2

    cap = cv2.VideoCapture(video_path)
    frame_num = 0
    results = []

    while True:
        ret, frame = cap.read()
        if not ret:
            break
        frame_num += 1
        if frame_num % sample_every_n != 0:
            continue
        r = detect_court_in_frame(frame)
        if r["success"]:
            results.append(r)

    cap.release()

    if not results:
        return {
            "polygon": None,
            "frames_sampled": frame_num // sample_every_n,
            "frames_detected": 0,
            "avg_mask_area_ratio": 0.0,
        }

    # Pick the result with the largest court area (most complete view)
    best = max(results, key=lambda r: r["mask_area_ratio"])
    avg_ratio = float(np.mean([r["mask_area_ratio"] for r in results]))

    return {
        "polygon": best["polygon"],
        "frames_sampled": frame_num // sample_every_n,
        "frames_detected": len(results),
        "avg_mask_area_ratio": round(avg_ratio, 4),
    }
