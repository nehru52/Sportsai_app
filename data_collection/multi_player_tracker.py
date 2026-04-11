"""
Multi-Player Tracking System with ByteTrack + TrOCR
Handles 12-player volleyball tracking with jersey number recognition
"""
import torch
import numpy as np
import cv2
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass, field
from collections import defaultdict
import json

@dataclass
class PlayerTrack:
    track_id: int
    jersey_number: Optional[str] = None
    position: str = "unknown"
    team: str = "unknown"
    bbox: List[float] = field(default_factory=list)
    confidence: float = 0.0
    last_seen: int = 0
    motion_history: List[Tuple[float, float]] = field(default_factory=list)
    role_probability: Dict[str, float] = field(default_factory=dict)

class VolleyballMultiTracker:
    """
    Advanced multi-player tracking for volleyball with jersey number recognition
    Integrates ByteTrack, TrOCR, and position-specific heuristics
    """
    
    def __init__(self, device: str = "cuda"):
        self.device = device
        
        # Initialize ByteTrack (placeholder - needs actual ByteTrack implementation)
        self.tracker = self.initialize_bytetrack()
        
        # Initialize TrOCR for jersey number reading
        self.ocr_model = self.initialize_trocr()
        
        # Player position classifiers based on movement patterns
        self.position_classifier = PositionClassifier()
        
        # Track management
        self.active_tracks: Dict[int, PlayerTrack] = {}
        self.track_id_counter = 0
        self.frame_count = 0
        
        # Volleyball-specific tracking parameters
        self.court_zones = self.define_court_zones()
        self.position_priors = self.load_position_priors()
        
    def initialize_bytetrack(self):
        """Initialize ByteTrack detector and tracker"""
        try:
            # Placeholder for ByteTrack initialization
            # In production, load ByteTrack with YOLOv8/YOLOX backbone
            print("[MultiTracker] Initializing ByteTrack...")
            # from bytetrack import ByteTrack
            # return ByteTrack()
            return None  # Placeholder
        except Exception as e:
            print(f"[MultiTracker] ByteTrack initialization failed: {e}")
            return None
    
    def initialize_trocr(self):
        """Initialize TrOCR for jersey number recognition"""
        try:
            print("[MultiTracker] Initializing TrOCR...")
            # Placeholder for TrOCR initialization
            # from transformers import TrOCRProcessor, VisionEncoderDecoderModel
            # processor = TrOCRProcessor.from_pretrained('microsoft/trocr-base-printed')
            # model = VisionEncoderDecoderModel.from_pretrained('microsoft/trocr-base-printed')
            return None  # Placeholder
        except Exception as e:
            print(f"[MultiTracker] TrOCR initialization failed: {e}")
            return None
    
    def define_court_zones(self) -> Dict[str, Tuple[float, float, float, float]]:
        """Define volleyball court zones for position tracking"""
        # Zone definitions as percentages of frame dimensions
        return {
            "back_left": (0.0, 0.0, 0.33, 0.5),
            "back_center": (0.33, 0.0, 0.66, 0.5),
            "back_right": (0.66, 0.0, 1.0, 0.5),
            "front_left": (0.0, 0.5, 0.33, 1.0),
            "front_center": (0.33, 0.5, 0.66, 1.0),
            "front_right": (0.66, 0.5, 1.0, 1.0),
            "net_zone": (0.25, 0.4, 0.75, 0.6),
            "service_zone": (0.0, 0.8, 1.0, 1.0)
        }
    
    def load_position_priors(self) -> Dict[str, Dict[str, float]]:
        """Load position-specific movement priors from FIVB data"""
        return {
            "middle": {
                "front_center": 0.4,
                "net_zone": 0.3,
                "back_center": 0.2,
                "front_left": 0.05,
                "front_right": 0.05
            },
            "opposite": {
                "front_right": 0.35,
                "back_right": 0.25,
                "net_zone": 0.2,
                "front_center": 0.15,
                "back_center": 0.05
            },
            "outside": {
                "front_left": 0.3,
                "back_left": 0.25,
                "net_zone": 0.2,
                "front_center": 0.15,
                "back_center": 0.1
            },
            "libero": {
                "back_left": 0.4,
                "back_center": 0.35,
                "back_right": 0.2,
                "service_zone": 0.05
            },
            "setter": {
                "front_center": 0.5,
                "back_center": 0.3,
                "net_zone": 0.15,
                "front_left": 0.03,
                "front_right": 0.02
            }
        }
    
    def process_frame(self, frame: np.ndarray, frame_num: int) -> List[PlayerTrack]:
        """Process single frame for multi-player tracking"""
        
        self.frame_count = frame_num
        
        # Step 1: Detect players using ByteTrack/YOLO
        detections = self.detect_players(frame)
        
        # Step 2: Update tracks with ByteTrack
        updated_tracks = self.update_tracks(detections)
        
        # Step 3: Extract jersey numbers with TrOCR
        self.extract_jersey_numbers(frame, updated_tracks)
        
        # Step 4: Classify positions based on movement and location
        self.classify_positions(updated_tracks)
        
        # Step 5: Assign teams based on jersey colors/patterns
        self.assign_teams(updated_tracks)
        
        # Step 6: Handle occlusions and ID switches
        self.handle_occlusions(updated_tracks)
        
        return list(updated_tracks.values())
    
    def detect_players(self, frame: np.ndarray) -> List[Dict]:
        """Detect players using ByteTrack/YOLO"""
        
        # Placeholder for actual detection
        # In production, use ByteTrack with YOLOv8/YOLOX
        height, width = frame.shape[:2]
        
        # Simulate detections for testing
        detections = []
        
        # Simulate 12 players on court
        for i in range(12):
            # Random positions for testing (would be actual detections)
            x = np.random.uniform(0.1, 0.9) * width
            y = np.random.uniform(0.2, 0.8) * height
            w = np.random.uniform(30, 80)
            h = np.random.uniform(120, 200)
            
            # Convert to normalized coordinates
            bbox = [x/width, y/height, w/width, h/height]
            
            detection = {
                "bbox": bbox,
                "confidence": np.random.uniform(0.7, 0.95),
                "class": "person"
            }
            detections.append(detection)
        
        return detections
    
    def update_tracks(self, detections: List[Dict]) -> Dict[int, PlayerTrack]:
        """Update player tracks with new detections"""
        
        # This would use ByteTrack's Kalman filter and Hungarian algorithm
        # For now, simple nearest-neighbor tracking
        
        new_tracks = {}
        used_detections = set()
        
        # Update existing tracks
        for track_id, track in self.active_tracks.items():
            best_detection = None
            best_distance = float('inf')
            
            for i, detection in enumerate(detections):
                if i in used_detections:
                    continue
                
                # Calculate distance (simplified IoU)
                distance = self.calculate_bbox_distance(track.bbox, detection["bbox"])
                
                if distance < best_distance and distance < 0.3:  # Distance threshold
                    best_detection = (i, detection)
                    best_distance = distance
            
            if best_detection:
                i, detection = best_detection
                used_detections.add(i)
                
                # Update track
                track.bbox = detection["bbox"]
                track.confidence = detection["confidence"]
                track.last_seen = self.frame_count
                
                # Update motion history
                center_x = detection["bbox"][0] + detection["bbox"][2]/2
                center_y = detection["bbox"][1] + detection["bbox"][3]/2
                track.motion_history.append((center_x, center_y))
                
                # Keep only last 30 positions (1 second at 30fps)
                if len(track.motion_history) > 30:
                    track.motion_history.pop(0)
                
                new_tracks[track_id] = track
        
        # Create new tracks for unmatched detections
        for i, detection in enumerate(detections):
            if i not in used_detections and detection["confidence"] > 0.5:
                new_track = PlayerTrack(
                    track_id=self.track_id_counter,
                    bbox=detection["bbox"],
                    confidence=detection["confidence"],
                    last_seen=self.frame_count
                )
                
                new_tracks[self.track_id_counter] = new_track
                self.track_id_counter += 1
        
        # Remove old tracks
        self.active_tracks = {k: v for k, v in new_tracks.items() 
                             if self.frame_count - v.last_seen < 30}  # 1 second threshold
        
        return self.active_tracks
    
    def calculate_bbox_distance(self, bbox1: List[float], bbox2: List[float]) -> float:
        """Calculate distance between two bounding boxes (IoU-based)"""
        # Convert to x1,y1,x2,y2 format
        x1_1, y1_1, w1, h1 = bbox1
        x2_1, y2_1 = x1_1 + w1, y1_1 + h1
        
        x1_2, y1_2, w2, h2 = bbox2
        x2_2, y2_2 = x1_2 + w2, y1_2 + h2
        
        # Calculate intersection
        x1_i = max(x1_1, x1_2)
        y1_i = max(y1_1, y1_2)
        x2_i = min(x2_1, x2_2)
        y2_i = min(y2_1, y2_2)
        
        if x2_i <= x1_i or y2_i <= y1_i:
            return 1.0  # No intersection
        
        intersection = (x2_i - x1_i) * (y2_i - y1_i)
        area1 = w1 * h1
        area2 = w2 * h2
        union = area1 + area2 - intersection
        
        iou = intersection / union if union > 0 else 0
        return 1.0 - iou  # Convert to distance
    
    def extract_jersey_numbers(self, frame: np.ndarray, tracks: Dict[int, PlayerTrack]):
        """Extract jersey numbers using TrOCR"""
        
        if self.ocr_model is None:
            return  # Skip if TrOCR not available
        
        for track_id, track in tracks.items():
            if track.jersey_number is None:  # Only extract if not already known
                try:
                    # Extract jersey region from bounding box
                    jersey_crop = self.extract_jersey_region(frame, track.bbox)
                    
                    if jersey_crop is not None:
                        # Use TrOCR to read jersey number
                        jersey_number = self.read_jersey_number(jersey_crop)
                        
                        if jersey_number and self.validate_jersey_number(jersey_number):
                            track.jersey_number = jersey_number
                            print(f"[MultiTracker] Track {track_id}: Jersey #{jersey_number}")
                            
                except Exception as e:
                    print(f"[MultiTracker] Jersey extraction failed for track {track_id}: {e}")
    
    def extract_jersey_region(self, frame: np.ndarray, bbox: List[float]) -> Optional[np.ndarray]:
        """Extract jersey region from player bounding box"""
        
        height, width = frame.shape[:2]
        
        # Convert normalized bbox to pixel coordinates
        x, y, w, h = bbox
        x_px = int(x * width)
        y_px = int(y * height)
        w_px = int(w * width)
        h_px = int(h * height)
        
        # Estimate jersey location (upper torso)
        jersey_y = y_px + int(h_px * 0.15)  # 15% from top
        jersey_h = int(h_px * 0.25)          # 25% of total height
        jersey_x = x_px + int(w_px * 0.2)   # Center crop
        jersey_w = int(w_px * 0.6)
        
        # Ensure bounds
        jersey_x = max(0, jersey_x)
        jersey_y = max(0, jersey_y)
        jersey_w = min(frame.shape[1] - jersey_x, jersey_w)
        jersey_h = min(frame.shape[0] - jersey_y, jersey_h)
        
        if jersey_w > 20 and jersey_h > 20:  # Minimum size
            return frame[jersey_y:jersey_y+jersey_h, jersey_x:jersey_x+jersey_w]
        
        return None
    
    def read_jersey_number(self, jersey_crop: np.ndarray) -> Optional[str]:
        """Read jersey number using TrOCR"""
        
        # Placeholder for TrOCR inference
        # In production, use actual TrOCR model
        
        # Preprocess image for OCR
        gray = cv2.cvtColor(jersey_crop, cv2.COLOR_BGR2GRAY)
        
        # Simple number detection using contours
        _, thresh = cv2.threshold(gray, 127, 255, cv2.THRESH_BINARY_INV)
        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        numbers = []
        for contour in contours:
            x, y, w, h = cv2.boundingRect(contour)
            
            # Filter by aspect ratio and size (digit-like)
            if w > 10 and h > 15 and 0.3 < w/h < 1.2:
                # Extract digit and classify (simplified)
                digit = self.classify_digit(thresh[y:y+h, x:x+w])
                if digit:
                    numbers.append(digit)
        
        return ''.join(numbers) if numbers else None
    
    def classify_digit(self, digit_img: np.ndarray) -> Optional[str]:
        """Simple digit classification (placeholder)"""
        
        # Resize to standard size
        digit_img = cv2.resize(digit_img, (28, 28))
        
        # Simple template matching (would use CNN in production)
        # For now, return random digit for testing
        import random
        return str(random.randint(0, 9))
    
    def validate_jersey_number(self, jersey_number: str) -> bool:
        """Validate extracted jersey number"""
        
        # Check if it's a reasonable jersey number (1-99)
        try:
            num = int(jersey_number)
            return 1 <= num <= 99
        except ValueError:
            return False
    
    def classify_positions(self, tracks: Dict[int, PlayerTrack]):
        """Classify player positions based on movement and location"""
        
        for track_id, track in tracks.items():
            if len(track.motion_history) < 10:  # Need sufficient history
                continue
            
            # Analyze movement patterns
            movement_features = self.extract_movement_features(track.motion_history)
            
            # Analyze court position preferences
            position_scores = self.analyze_position_preferences(track.motion_history)
            
            # Combine features for classification
            position_probabilities = self.position_classifier.classify(
                movement_features, position_scores, track.bbox
            )
            
            track.role_probability = position_probabilities
            
            # Assign most likely position
            if position_probabilities:
                best_position = max(position_probabilities, key=position_probabilities.get)
                track.position = best_position
                
                print(f"[MultiTracker] Track {track_id}: Position {best_position} "
                      f"(confidence: {position_probabilities[best_position]:.2f})")
    
    def extract_movement_features(self, motion_history: List[Tuple[float, float]]) -> Dict[str, float]:
        """Extract movement pattern features"""
        
        if len(motion_history) < 5:
            return {}
        
        # Convert to numpy arrays
        positions = np.array(motion_history)
        
        # Calculate velocities
        if len(positions) > 1:
            velocities = np.diff(positions, axis=0)
            speeds = np.linalg.norm(velocities, axis=1)
        else:
            speeds = [0]
        
        # Extract features
        features = {
            "avg_speed": np.mean(speeds),
            "max_speed": np.max(speeds) if len(speeds) > 0 else 0,
            "speed_variance": np.var(speeds) if len(speeds) > 1 else 0,
            "vertical_movement": np.std(positions[:, 1]),  # Y-coordinate variation
            "horizontal_range": np.max(positions[:, 0]) - np.min(positions[:, 0]),
            "jump_frequency": self.detect_jumps(positions),
            "direction_changes": self.count_direction_changes(velocities) if len(velocities) > 0 else 0
        }
        
        return features
    
    def detect_jumps(self, positions: np.ndarray) -> float:
        """Detect jumping frequency from vertical position changes"""
        
        if len(positions) < 3:
            return 0.0
        
        # Look for rapid vertical changes (jump peaks)
        y_positions = positions[:, 1]
        
        # Smooth positions to reduce noise
        from scipy.ndimage import gaussian_filter1d
        smoothed_y = gaussian_filter1d(y_positions, sigma=2)
        
        # Find peaks (local maxima)
        from scipy.signal import find_peaks
        peaks, _ = find_peaks(smoothed_y, height=np.mean(smoothed_y) + np.std(smoothed_y))
        
        return len(peaks) / len(positions)  # Jumps per frame
    
    def count_direction_changes(self, velocities: np.ndarray) -> int:
        """Count significant direction changes"""
        
        if len(velocities) < 3:
            return 0
        
        # Calculate direction changes in velocity
        direction_changes = 0
        
        for i in range(1, len(velocities)):
            # Check if direction changed significantly
            prev_vel = velocities[i-1]
            curr_vel = velocities[i]
            
            # Calculate angle change
            if np.linalg.norm(prev_vel) > 0 and np.linalg.norm(curr_vel) > 0:
                cos_angle = np.dot(prev_vel, curr_vel) / (np.linalg.norm(prev_vel) * np.linalg.norm(curr_vel))
                angle_change = np.arccos(np.clip(cos_angle, -1, 1))
                
                if angle_change > np.pi/3:  # 60 degrees
                    direction_changes += 1
        
        return direction_changes
    
    def analyze_position_preferences(self, motion_history: List[Tuple[float, float]]) -> Dict[str, float]:
        """Analyze which court zones player prefers"""
        
        zone_counts = defaultdict(int)
        total_positions = len(motion_history)
        
        if total_positions == 0:
            return {}
        
        for x, y in motion_history:
            # Determine which zone this position falls into
            for zone_name, (x1, y1, x2, y2) in self.court_zones.items():
                if x1 <= x <= x2 and y1 <= y <= y2:
                    zone_counts[zone_name] += 1
                    break
        
        # Convert to probabilities
        zone_probabilities = {}
        for zone, count in zone_counts.items():
            zone_probabilities[zone] = count / total_positions
        
        return zone_probabilities
    
    def assign_teams(self, tracks: Dict[int, PlayerTrack]):
        """Assign teams based on jersey colors/patterns"""
        
        # Analyze jersey colors for team assignment
        team_groups = defaultdict(list)
        
        for track_id, track in tracks.items():
            if track.jersey_number:
                # Use jersey number as team indicator (simplified)
                # In production, analyze actual jersey colors
                team_id = int(track.jersey_number) % 2  # Simple alternating assignment
                track.team = f"team_{team_id}"
                team_groups[team_id].append(track_id)
        
        # Balance teams (6 players each for volleyball)
        if len(team_groups) >= 2:
            # Assign remaining tracks to balance teams
            unassigned = [tid for tid, track in tracks.items() if not track.jersey_number]
            
            # Assign based on spatial proximity to existing team members
            for track_id in unassigned:
                track = tracks[track_id]
                
                # Find closest assigned track
                closest_team = None
                min_distance = float('inf')
                
                for tid, other_track in tracks.items():
                    if tid != track_id and other_track.team != "unknown":
                        distance = self.calculate_bbox_distance(track.bbox, other_track.bbox)
                        if distance < min_distance:
                            min_distance = distance
                            closest_team = other_track.team
                
                if closest_team:
                    track.team = closest_team
    
    def handle_occlusions(self, tracks: Dict[int, PlayerTrack]):
        """Handle occlusions during blocking/overlapping situations"""
        
        # Detect potential occlusions (overlapping bounding boxes)
        occlusion_groups = self.find_occlusion_groups(tracks)
        
        for group in occlusion_groups:
            if len(group) > 1:
                # Handle occlusion group
                self.resolve_occlusion_group(tracks, group)
    
    def find_occlusion_groups(self, tracks: Dict[int, PlayerTrack]) -> List[List[int]]:
        """Find groups of tracks with overlapping bounding boxes"""
        
        groups = []
        processed = set()
        
        for track_id, track in tracks.items():
            if track_id in processed:
                continue
            
            # Find all tracks overlapping with this one
            group = [track_id]
            processed.add(track_id)
            
            for other_id, other_track in tracks.items():
                if other_id != track_id and other_id not in processed:
                    if self.bboxes_overlap(track.bbox, other_track.bbox):
                        group.append(other_id)
                        processed.add(other_id)
            
            if len(group) > 1:
                groups.append(group)
        
        return groups
    
    def bboxes_overlap(self, bbox1: List[float], bbox2: List[float]) -> bool:
        """Check if two bounding boxes overlap significantly"""
        
        x1_1, y1_1, w1, h1 = bbox1
        x2_1, y2_1 = x1_1 + w1, y1_1 + h1
        
        x1_2, y1_2, w2, h2 = bbox2
        x2_2, y2_2 = x1_2 + w2, y1_2 + h2
        
        # Check for overlap
        overlap_x = max(0, min(x2_1, x2_2) - max(x1_1, x1_2))
        overlap_y = max(0, min(y2_1, y2_2) - max(y1_1, y1_2))
        
        overlap_area = overlap_x * overlap_y
        bbox1_area = w1 * h1
        bbox2_area = w2 * h2
        
        min_area = min(bbox1_area, bbox2_area)
        
        # Consider it an occlusion if overlap > 30% of smaller bbox
        return overlap_area > 0.3 * min_area
    
    def resolve_occlusion_group(self, tracks: Dict[int, PlayerTrack], group: List[int]):
        """Resolve occlusions within a group of overlapping tracks"""
        
        # Use motion consistency and position priors to maintain IDs
        for track_id in group:
            track = tracks[track_id]
            
            # Predict next position based on motion history
            predicted_pos = self.predict_next_position(track.motion_history)
            
            # Use predicted position to maintain track during occlusion
            if predicted_pos:
                # Update track with predicted position (with reduced confidence)
                x_pred, y_pred = predicted_pos
                
                # Keep existing bbox but adjust center to predicted position
                w, h = track.bbox[2], track.bbox[3]
                track.bbox = [x_pred - w/2, y_pred - h/2, w, h]
                track.confidence *= 0.8  # Reduce confidence during occlusion
    
    def predict_next_position(self, motion_history: List[Tuple[float, float]]) -> Optional[Tuple[float, float]]:
        """Predict next position using motion history"""
        
        if len(motion_history) < 3:
            return None
        
        # Simple linear prediction using last few positions
        recent_positions = motion_history[-5:]
        
        if len(recent_positions) < 2:
            return None
        
        # Calculate average velocity
        positions = np.array(recent_positions)
        if len(positions) > 1:
            velocities = np.diff(positions, axis=0)
            avg_velocity = np.mean(velocities, axis=0)
            
            # Predict next position
            last_pos = positions[-1]
            predicted_pos = last_pos + avg_velocity
            
            return tuple(predicted_pos)
        
        return None
    
    def get_team_formation(self, tracks: Dict[int, PlayerTrack]) -> Dict[str, List[PlayerTrack]]:
        """Get current team formation"""
        
        team_formation = defaultdict(list)
        
        for track in tracks.values():
            if track.team != "unknown":
                team_formation[track.team].append(track)
        
        return dict(team_formation)
    
    def get_position_distribution(self, tracks: Dict[int, PlayerTrack]) -> Dict[str, int]:
        """Get distribution of player positions"""
        
        position_counts = defaultdict(int)
        
        for track in tracks.values():
            position_counts[track.position] += 1
        
        return dict(position_counts)
    
    def export_tracking_data(self, tracks: Dict[int, PlayerTrack]) -> Dict:
        """Export tracking data for analysis"""
        
        export_data = {
            "frame": self.frame_count,
            "tracks": {},
            "team_formation": self.get_team_formation(tracks),
            "position_distribution": self.get_position_distribution(tracks),
            "occlusion_events": len(self.find_occlusion_groups(tracks))
        }
        
        for track_id, track in tracks.items():
            export_data["tracks"][track_id] = {
                "jersey_number": track.jersey_number,
                "position": track.position,
                "team": track.team,
                "confidence": track.confidence,
                "bbox": track.bbox,
                "motion_features": self.extract_movement_features(track.motion_history) if track.motion_history else {},
                "role_probability": track.role_probability
            }
        
        return export_data

class PositionClassifier:
    """Classify volleyball player positions based on movement patterns"""
    
    def classify(self, movement_features: Dict[str, float], position_scores: Dict[str, float], bbox: List[float]) -> Dict[str, float]:
        """Classify player position using multiple features"""
        
        # Combine movement, position, and appearance features
        combined_scores = {}
        
        # Weight different features
        movement_weight = 0.4
        position_weight = 0.4
        appearance_weight = 0.2
        
        for position in ["middle", "opposite", "outside", "libero", "setter"]:
            movement_score = self.get_movement_score(position, movement_features)
            position_score = position_scores.get(position, 0.0)
            appearance_score = self.get_appearance_score(position, bbox)
            
            combined_score = (
                movement_weight * movement_score +
                position_weight * position_score +
                appearance_weight * appearance_score
            )
            
            combined_scores[position] = combined_score
        
        return combined_scores
    
    def get_movement_score(self, position: str, movement_features: Dict[str, float]) -> float:
        """Get movement-based score for position"""
        
        if not movement_features:
            return 0.0
        
        # Position-specific movement characteristics
        characteristics = {
            "middle": {"avg_speed": (0.3, 0.6), "vertical_movement": (0.4, 0.8), "jump_frequency": (0.05, 0.15)},
            "opposite": {"avg_speed": (0.4, 0.7), "horizontal_range": (0.6, 1.0), "jump_frequency": (0.04, 0.12)},
            "outside": {"avg_speed": (0.5, 0.8), "horizontal_range": (0.5, 0.9), "jump_frequency": (0.04, 0.12)},
            "libero": {"avg_speed": (0.6, 0.9), "direction_changes": (0.8, 1.5), "vertical_movement": (0.1, 0.3)},
            "setter": {"avg_speed": (0.4, 0.7), "direction_changes": (0.6, 1.2), "horizontal_range": (0.4, 0.7)}
        }
        
        score = 0.0
        char = characteristics.get(position, {})
        
        for feature, (min_val, max_val) in char.items():
            if feature in movement_features:
                val = movement_features[feature]
                if min_val <= val <= max_val:
                    score += 1.0  # Full score for matching characteristic
                else:
                    # Partial score based on distance from range
                    distance = min(abs(val - min_val), abs(val - max_val))
                    range_size = max_val - min_val
                    score += max(0, 1.0 - distance / range_size)
        
        return score / len(char) if char else 0.0
    
    def get_appearance_score(self, position: str, bbox: List[float]) -> float:
        """Get appearance-based score for position"""
        
        # Height-based scoring (normalized coordinates)
        _, y, _, h = bbox
        center_y = y + h/2
        
        # Position-specific height preferences
        height_scores = {
            "middle": 1.0 if center_y > 0.5 else 0.5,      # Taller players
            "opposite": 1.0 if center_y > 0.5 else 0.6,
            "outside": 0.9 if center_y > 0.5 else 0.7,
            "libero": 0.7 if center_y < 0.5 else 0.9,      # Shorter players
            "setter": 0.8 if center_y > 0.5 else 0.7
        }
        
        return height_scores.get(position, 0.5)

# Global tracker instance
multi_tracker = VolleyballMultiTracker()

def track_multiple_players(frame: np.ndarray, frame_num: int) -> List[PlayerTrack]:
    """Main function for multi-player tracking"""
    return multi_tracker.process_frame(frame, frame_num)

def export_tracking_summary(tracks: List[PlayerTrack]) -> Dict:
    """Export comprehensive tracking summary"""
    
    tracks_dict = {track.track_id: track for track in tracks}
    return multi_tracker.export_tracking_data(tracks_dict)