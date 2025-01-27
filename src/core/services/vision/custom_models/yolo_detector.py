"""Custom YOLO detector implementation."""
import torch
import numpy as np
from typing import Dict, List, Any, Optional, Tuple
import cv2
from pathlib import Path
from ultralytics import YOLO

from src.core.services.vision.model_manager import ModelInterface

class YOLODetector(ModelInterface):
    """Custom YOLO detector implementation."""
    
    def __init__(self):
        """Initialize YOLO detector."""
        self.model = None
        self.device = 'cuda' if torch.cuda.is_available() else 'cpu'
        self.metadata = {
            'task': 'object_detection',
            'architecture': 'yolov8',
            'supported_formats': ['.pt', '.onnx']
        }
    
    def load_model(self, model_path: str, config: Dict[str, Any]) -> Any:
        """Load YOLO model.
        
        Args:
            model_path: Path to model file
            config: Model configuration
            
        Returns:
            Loaded model
        """
        # Load model with ultralytics
        self.model = YOLO(model_path)
        
        # Configure model
        self.conf_threshold = config.get('conf_threshold', 0.25)
        self.iou_threshold = config.get('iou_threshold', 0.45)
        self.max_detections = config.get('max_detections', 300)
        
        return self.model
    
    def preprocess(self, input_data: np.ndarray) -> torch.Tensor:
        """Preprocess input image.
        
        Args:
            input_data: Input image (BGR)
            
        Returns:
            Preprocessed tensor
        """
        # Convert to RGB
        image_rgb = cv2.cvtColor(input_data, cv2.COLOR_BGR2RGB)
        
        # Normalize and convert to tensor
        image = torch.from_numpy(image_rgb).float()
        image = image.permute(2, 0, 1)  # HWC to CHW
        image = image / 255.0  # Normalize
        
        # Add batch dimension
        if image.ndim == 3:
            image = image.unsqueeze(0)
        
        return image.to(self.device)
    
    def predict(self, input_data: torch.Tensor) -> List[Dict[str, Any]]:
        """Run prediction on preprocessed data.
        
        Args:
            input_data: Preprocessed input tensor
            
        Returns:
            List of detections
        """
        # Run inference
        results = self.model(
            input_data,
            conf=self.conf_threshold,
            iou=self.iou_threshold,
            max_det=self.max_detections
        )
        
        return results
    
    def postprocess(self, output_data: Any) -> List[Dict[str, Any]]:
        """Postprocess model output.
        
        Args:
            output_data: Model output
            
        Returns:
            List of processed detections
        """
        detections = []
        
        # Process each detection
        for result in output_data:
            boxes = result.boxes
            
            for i in range(len(boxes)):
                box = boxes[i]
                
                # Get box coordinates
                x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                
                # Get class and confidence
                class_id = int(box.cls)
                confidence = float(box.conf)
                
                detections.append({
                    'bbox': [x1, y1, x2, y2],
                    'class_id': class_id,
                    'class_name': result.names[class_id],
                    'confidence': confidence
                })
        
        return detections
