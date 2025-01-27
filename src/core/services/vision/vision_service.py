"""Vision service for AI Assistant."""
import os
import torch
import numpy as np
from typing import Dict, List, Any, Optional, Tuple, Union, BinaryIO, Callable
import cv2
from pathlib import Path
from dataclasses import dataclass
import base64
import io
from PIL import Image
from datetime import datetime
import threading
import logging

# Configure logging
logging.basicConfig(level=logging.ERROR)

from src.core.interfaces.service import Service
from src.core.event_bus import EventBus, VisionResult
from src.core.services.vision.vision_processor import VisionProcessor
from src.core.services.vision.advanced_models import (
    VisionModels,
    SegmentationResult,
    DepthResult,
    TrackingResult
)
from src.core.services.vision.model_manager import ModelManager

class VisionService(Service):
    """Vision service for AI Assistant."""
    
    def __init__(self, event_bus: EventBus, config: Dict[str, Any]):
        """Initialize vision service.
        
        Args:
            event_bus: Event bus instance
            config: Configuration dictionary
        """
        super().__init__()
        
        self.config = config
        self.event_bus = event_bus
        self.vision_config = config['services']['vision']
        
        # Model storage
        self.models_dir = os.path.join('runtime', 'vision', 'models')
        os.makedirs(self.models_dir, exist_ok=True)
        
        # Device
        self.device = 'cuda' if torch.cuda.is_available() else 'cpu'
        
        # Initialize components
        self.model_manager = ModelManager(config)
        self.processor = VisionProcessor(config)
        self.advanced_models = VisionModels(config)
        
        # Initialize camera manager
        self.camera_manager = None
        self.active_camera = None
        self.frame_callbacks: List[Callable[[np.ndarray], None]] = []
        self.camera_lock = threading.Lock()
    
    def initialize(self) -> None:
        """Initialize the service."""
        # Create necessary directories
        os.makedirs(os.path.join('runtime', 'vision'), exist_ok=True)
        os.makedirs(os.path.join('runtime', 'vision', 'models'), exist_ok=True)
        os.makedirs(os.path.join('runtime', 'vision', 'storage'), exist_ok=True)
    
    def segment_image(self, image: np.ndarray,
                     points: Optional[List[List[int]]] = None) -> SegmentationResult:
        """Segment image using SAM.
        
        Args:
            image: Input image (BGR)
            points: Optional list of points to segment around
            
        Returns:
            Segmentation result
        """
        return self.advanced_models.segment_image(image, points)
    
    def estimate_depth(self, image: np.ndarray) -> DepthResult:
        """Estimate depth using DPT.
        
        Args:
            image: Input image (BGR)
            
        Returns:
            Depth estimation result
        """
        return self.advanced_models.estimate_depth(image)
    
    def track_objects(self, detections: List[Dict[str, Any]], 
                     frame: np.ndarray) -> List[TrackingResult]:
        """Track objects using ByteTrack.
        
        Args:
            detections: List of object detections
            frame: Current video frame
            
        Returns:
            List of tracking results
        """
        return self.advanced_models.track_objects(detections, frame)
    
    def process_frame(self, frame: np.ndarray) -> Dict[str, Any]:
        """Process a single frame.
        
        Args:
            frame: Input frame (BGR)
            
        Returns:
            Dictionary of results
        """
        results = {}
        
        # Run segmentation if available
        if hasattr(self.advanced_models, 'sam_predictor') and self.advanced_models.sam_predictor is not None:
            seg_result = self.segment_image(frame)
            results['segmentation'] = seg_result
        else:
            results['segmentation'] = None
        
        # Run depth estimation if available
        if hasattr(self.advanced_models, 'depth_estimator') and self.advanced_models.depth_estimator is not None:
            depth_result = self.estimate_depth(frame)
            results['depth'] = depth_result
        else:
            results['depth'] = None
        
        return results
    
    def process_image(self, image_data: Union[str, BinaryIO, np.ndarray]) -> VisionResult:
        """Process an image.
        
        Args:
            image_data: Input image data (base64, file, or numpy array)
            
        Returns:
            Vision result
        """
        # Convert input to numpy array
        if isinstance(image_data, str):
            # Decode base64
            image_bytes = base64.b64decode(image_data)
            image = cv2.imdecode(
                np.frombuffer(image_bytes, np.uint8),
                cv2.IMREAD_COLOR
            )
        elif isinstance(image_data, (io.IOBase, BinaryIO)):
            # Read from file
            image_bytes = image_data.read()
            image = cv2.imdecode(
                np.frombuffer(image_bytes, np.uint8),
                cv2.IMREAD_COLOR
            )
        else:
            # Already numpy array
            image = image_data
        
        # Process frame
        results = self.process_frame(image)
        
        # Create vision result
        return VisionResult(
            timestamp=datetime.now(),
            segmentation=results['segmentation'],
            depth=results['depth']
        )
    
    def start_camera(self, camera_id: int = 0):
        """Start camera capture.
        
        Args:
            camera_id: Camera device ID
        """
        with self.camera_lock:
            if self.camera_manager is None:
                # Initialize camera
                self.camera_manager = cv2.VideoCapture(camera_id)
                if not self.camera_manager.isOpened():
                    raise RuntimeError(f"Failed to open camera {camera_id}")
                
                # Start capture thread
                self.active_camera = camera_id
                threading.Thread(
                    target=self._camera_thread,
                    daemon=True
                ).start()
    
    def stop_camera(self):
        """Stop camera capture."""
        with self.camera_lock:
            if self.camera_manager is not None:
                self.camera_manager.release()
                self.camera_manager = None
                self.active_camera = None
    
    def add_frame_callback(self, callback: Callable[[np.ndarray], None]):
        """Add frame callback.
        
        Args:
            callback: Callback function
        """
        self.frame_callbacks.append(callback)
    
    def remove_frame_callback(self, callback: Callable[[np.ndarray], None]):
        """Remove frame callback.
        
        Args:
            callback: Callback function
        """
        if callback in self.frame_callbacks:
            self.frame_callbacks.remove(callback)
    
    def _camera_thread(self):
        """Camera capture thread."""
        while True:
            with self.camera_lock:
                if self.camera_manager is None:
                    break
                
                # Read frame
                ret, frame = self.camera_manager.read()
                if not ret:
                    break
                
                # Process frame
                try:
                    results = self.process_frame(frame)
                    
                    # Call callbacks
                    for callback in self.frame_callbacks:
                        try:
                            callback(frame)
                        except Exception as e:
                            print(f"Error in frame callback: {e}")
                    
                    # Emit event
                    self.event_bus.emit(
                        'vision_frame',
                        VisionResult(
                            timestamp=datetime.now(),
                            segmentation=results['segmentation'],
                            depth=results['depth']
                        )
                    )
                except Exception as e:
                    print(f"Error processing frame: {e}")
    
    def cleanup(self):
        """Clean up resources."""
        self.stop_camera()
        if hasattr(self, 'advanced_models'):
            self.advanced_models.cleanup()
        if hasattr(self, 'model_manager'):
            self.model_manager.cleanup()
