import cv2
import numpy as np
import logging

class HomographyCorrector:
    """
    Corrects perspective distortion by mapping detected court corners 
    to a canonical 640x360 rectangle.
    """
    def __init__(self, target_w=640, target_h=360):
        self.target_w = target_w
        self.target_h = target_h
        self.target_pts = np.array([
            [0, 0],
            [target_w - 1, 0],
            [target_w - 1, target_h - 1],
            [0, target_h - 1]
        ], dtype=np.float32)
        self.M = None # Legacy reference
        self.H = None # Active homography matrix
        self.logger = logging.getLogger(__name__)

    def fit(self, src_corners):
        """
        Compute homography matrix H from 4 source corners.
        Includes reprojection error check.
        """
        if src_corners is None or len(src_corners) < 4:
            self.logger.warning("Fewer than 4 court corners detected. Skipping homography fit.")
            self.H = None
            self.M = None
            return False
        
        src_pts = np.array(src_corners, dtype=np.float32)
        H, _ = cv2.findHomography(src_pts, self.target_pts)
        
        # Improvement 3: Reprojection error guard
        projected = cv2.perspectiveTransform(src_pts.reshape(-1, 1, 2), H).reshape(-1, 2)
        error = np.mean(np.linalg.norm(projected - self.target_pts, axis=1))
        
        if error > 15.0:
            self.logger.warning(f"Homography reprojection error {error:.1f}px exceeds threshold — skipping warp for this frame")
            self.H = None
            self.M = None
            return False

        self.H = H
        self.M = H # Maintain backward compatibility with M
        return True

    def transform(self, frame):
        """
        Apply perspective warp to the frame if H was successfully computed.
        """
        if self.H is None:
            return frame
        
        return cv2.warpPerspective(frame, self.H, (self.target_w, self.target_h))

    def remap_keypoints(self, keypoints: np.ndarray) -> np.ndarray:
        """
        Improvement 1: Remap keypoints from warped space back to original frame space.
        Input shape: (N, 2)
        """
        if self.H is None or keypoints.size == 0:
            return keypoints
            
        H_inv = np.linalg.inv(self.H)
        kps_reshaped = keypoints.reshape(-1, 1, 2).astype(np.float32)
        remapped = cv2.perspectiveTransform(kps_reshaped, H_inv)
        return remapped.reshape(-1, 2)
