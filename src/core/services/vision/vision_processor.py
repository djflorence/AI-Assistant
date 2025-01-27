"""Vision processor for AI Assistant."""
import os
import torch
import numpy as np
from typing import Dict, List, Any, Optional, Tuple
import cv2
from pathlib import Path
from dataclasses import dataclass
import mediapipe as mp
import face_recognition

from ultralytics import YOLO

@dataclass
class DetectionResult:
    """Object detection result."""
    label: str
    confidence: float
    bbox: Tuple[float, float, float, float]

@dataclass
class FaceResult:
    """Face detection result."""
    bbox: Tuple[float, float, float, float]
    landmarks: Dict[str, Tuple[float, float]]
    encoding: Optional[np.ndarray] = None

@dataclass
class PoseResult:
    """Pose estimation result."""
    landmarks: Dict[str, Tuple[float, float, float]]
    connections: List[Tuple[str, str]]

class VisionProcessor:
    """Vision processor for AI Assistant."""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize vision processor.
        
        Args:
            config: Configuration dictionary
        """
        self.config = config
        self.vision_config = config['services']['vision']
        
        # Model storage
        self.models_dir = os.path.join('runtime', 'vision', 'models')
        os.makedirs(self.models_dir, exist_ok=True)
        
        # Device
        self.device = 'cuda' if torch.cuda.is_available() else 'cpu'
        
        # Initialize components
        self._initialize_object_detection()
        self._initialize_face_detection()
        self._initialize_pose_estimation()
    
    def _initialize_object_detection(self):
        """Initialize object detection."""
        # Load YOLOv8 model
        model_path = os.path.join(self.models_dir, 'yolov8n.pt')
        if not os.path.exists(model_path):
            # Download model
            self.object_detector = YOLO('yolov8n.pt')
            self.object_detector.export(format='onnx')
        else:
            self.object_detector = YOLO(model_path)
        
        # Move to device
        self.object_detector.to(self.device)
    
    def _initialize_face_detection(self):
        """Initialize face detection."""
        self.face_detector = face_recognition
    
    def _initialize_pose_estimation(self):
        """Initialize pose estimation."""
        self.pose_detector = mp.solutions.pose.Pose(
            static_image_mode=True,
            model_complexity=2,
            enable_segmentation=True,
            min_detection_confidence=0.5
        )
    
    def detect_objects(self, image: np.ndarray) -> List[DetectionResult]:
        """Detect objects in image.
        
        Args:
            image: Input image (BGR)
            
        Returns:
            List of detection results
        """
        # Run inference
        results = self.object_detector(image)
        
        # Process results
        detections = []
        for r in results:
            boxes = r.boxes
            for box in boxes:
                # Get box coordinates
                x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                
                # Get class and confidence
                cls = int(box.cls[0].item())
                conf = float(box.conf[0].item())
                label = results.names[cls]
                
                detections.append(DetectionResult(
                    label=label,
                    confidence=conf,
                    bbox=(float(x1), float(y1), float(x2), float(y2))
                ))
        
        return detections
    
    def detect_faces(self, image: np.ndarray) -> List[FaceResult]:
        """Detect faces in image.
        
        Args:
            image: Input image (BGR)
            
        Returns:
            List of face results
        """
        # Convert to RGB
        image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        
        # Detect faces
        face_locations = self.face_detector.face_locations(image_rgb)
        face_landmarks = self.face_detector.face_landmarks(image_rgb, face_locations)
        face_encodings = self.face_detector.face_encodings(image_rgb, face_locations)
        
        # Process results
        faces = []
        for location, landmarks, encoding in zip(
            face_locations, face_landmarks, face_encodings
        ):
            # Convert location to bbox
            top, right, bottom, left = location
            bbox = (float(left), float(top), float(right), float(bottom))
            
            # Convert landmarks to dict
            landmarks_dict = {}
            for feature, points in landmarks.items():
                for i, point in enumerate(points):
                    landmarks_dict[f"{feature}_{i}"] = point
            
            faces.append(FaceResult(
                bbox=bbox,
                landmarks=landmarks_dict,
                encoding=encoding
            ))
        
        return faces
    
    def estimate_pose(self, image: np.ndarray) -> Optional[PoseResult]:
        """Estimate pose in image.
        
        Args:
            image: Input image (BGR)
            
        Returns:
            Pose result if detected, None otherwise
        """
        # Convert to RGB
        image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        
        # Run pose detection
        results = self.pose_detector.process(image_rgb)
        
        if not results.pose_landmarks:
            return None
        
        # Convert landmarks to dict
        landmarks = {}
        for idx, landmark in enumerate(results.pose_landmarks.landmark):
            landmarks[f"landmark_{idx}"] = (
                float(landmark.x),
                float(landmark.y),
                float(landmark.z)
            )
        
        # Get connections
        connections = []
        pose_connections = mp.solutions.pose.POSE_CONNECTIONS
        for start_idx, end_idx in pose_connections:
            start_point = f"landmark_{start_idx}"
            end_point = f"landmark_{end_idx}"
            connections.append((start_point, end_point))
        
        return PoseResult(
            landmarks=landmarks,
            connections=connections
        )
    
    def cleanup(self):
        """Clean up resources."""
        if hasattr(self, 'pose_detector'):
            self.pose_detector.close()
