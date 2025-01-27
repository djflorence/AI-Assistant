"""Advanced vision models for AI Assistant."""
import os
import torch
import numpy as np
from typing import Dict, List, Any, Optional, Tuple
import cv2
from pathlib import Path
from dataclasses import dataclass
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configure MediaPipe logging
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'  # Suppress TensorFlow logging
logging.getLogger('mediapipe').setLevel(logging.ERROR)

# Configure transformers logging
import transformers
transformers.logging.set_verbosity_error()
transformers.logging.disable_progress_bar()

@dataclass
class SegmentationResult:
    """Segmentation result."""
    masks: List[Dict[str, Any]]
    colorized: Optional[np.ndarray] = None

@dataclass
class DepthResult:
    """Depth estimation result."""
    depth_map: np.ndarray
    colorized: Optional[np.ndarray] = None
    min_depth: float = 0.0
    max_depth: float = 1.0

@dataclass
class TrackingResult:
    """Object tracking result."""
    object_id: int
    label: str
    bbox: Tuple[float, float, float, float]
    confidence: float
    trajectory: List[Tuple[float, float]]

class VisionModels:
    """Advanced vision models."""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize vision models.
        
        Args:
            config: Configuration dictionary
        """
        logger.info("Initializing VisionModels...")
        self.config = config
        self.vision_config = config['services']['vision']
        
        # Model storage
        self.models_dir = os.path.join('runtime', 'vision', 'models')
        os.makedirs(self.models_dir, exist_ok=True)
        logger.info(f"Models directory: {self.models_dir}")
        
        # Device
        self.device = 'cuda' if torch.cuda.is_available() else 'cpu'
        logger.info(f"Using device: {self.device}")
        
        # Initialize models
        logger.info("Starting model initialization...")
        self._initialize_sam()
        logger.info("SAM initialization complete")
        self._initialize_depth_estimator()
        logger.info("Depth estimator initialization complete")
        self._initialize_object_tracker()
        logger.info("Object tracker initialization complete")
        logger.info("All models initialized")
    
    def _initialize_sam(self):
        """Initialize SAM model."""
        logger.info("Initializing SAM model...")
        try:
            sam_checkpoint = os.path.join(self.models_dir, "sam_vit_h_4b8939.pth")
            logger.info(f"Looking for SAM checkpoint at: {sam_checkpoint}")
            
            if not os.path.exists(sam_checkpoint):
                logger.info("SAM model not found, skipping initialization")
                self.sam_predictor = None
                return
            
            logger.info("Loading SAM model...")
            from segment_anything import sam_model_registry, SamPredictor
            model_type = "vit_h"
            sam = sam_model_registry[model_type](checkpoint=sam_checkpoint)
            sam.to(device=self.device)
            self.sam_predictor = SamPredictor(sam)
            logger.info("SAM model loaded successfully")
            
        except Exception as e:
            logger.error(f"Error initializing SAM: {e}")
            self.sam_predictor = None
    
    def _initialize_depth_estimator(self):
        """Initialize depth estimation model."""
        logger.info("Initializing depth estimator...")
        try:
            # Skip for testing
            logger.info("Skipping depth estimator initialization for testing")
            self.depth_estimator = None
            return
            
            # Import here to avoid slow startup
            from transformers import pipeline
            logger.info("Creating depth estimation pipeline...")
            self.depth_estimator = pipeline(
                "depth-estimation",
                model="Intel/dpt-large",
                device=self.device,
                torch_dtype=torch.float16,
                timeout=0
            )
            logger.info("Depth estimator initialized successfully")
        except Exception as e:
            logger.error(f"Error initializing depth estimator: {e}")
            self.depth_estimator = None
    
    def _initialize_object_tracker(self):
        """Initialize object tracker."""
        logger.info("Initializing object tracker...")
        try:
            self.object_tracker = {}  # Initialize tracking state
            logger.info("Object tracker initialized successfully")
        except Exception as e:
            logger.error(f"Error initializing object tracker: {e}")
            self.object_tracker = None
    
    def segment_image(self, image: np.ndarray,
                     points: Optional[List[List[int]]] = None) -> SegmentationResult:
        """Segment image using SAM.
        
        Args:
            image: Input image (BGR)
            points: Optional list of points to segment around
            
        Returns:
            Segmentation result
        """
        if self.sam_predictor is None:
            return SegmentationResult(masks=[])
        
        try:
            # Set image
            self.sam_predictor.set_image(image)
            
            # Generate masks
            if points is not None:
                input_points = np.array(points)
                masks, scores, logits = self.sam_predictor.predict(
                    point_coords=input_points,
                    point_labels=np.ones(len(points)),
                    multimask_output=True
                )
            else:
                masks, scores, logits = self.sam_predictor.predict(
                    point_coords=None,
                    point_labels=None,
                    multimask_output=True
                )
            
            # Process results
            results = []
            for mask, score in zip(masks, scores):
                results.append({
                    'mask': mask,
                    'score': float(score)
                })
            
            # Colorize masks
            colorized = None
            if results:
                colorized = np.zeros_like(image)
                for idx, result in enumerate(results):
                    color = np.random.randint(0, 255, size=3)
                    colorized[result['mask']] = color
            
            return SegmentationResult(
                masks=results,
                colorized=colorized
            )
            
        except Exception as e:
            logger.error(f"Error in segmentation: {e}")
            return SegmentationResult(masks=[])
    
    def estimate_depth(self, image: np.ndarray) -> DepthResult:
        """Estimate depth using DPT.
        
        Args:
            image: Input image (BGR)
            
        Returns:
            Depth estimation result
        """
        if self.depth_estimator is None:
            return DepthResult(depth_map=np.zeros_like(image[:,:,0]))
        
        try:
            # Convert to RGB
            image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            
            # Get depth map
            depth = self.depth_estimator(image_rgb)['depth']
            depth_map = depth.squeeze().numpy()
            
            # Normalize depth map
            depth_min = depth_map.min()
            depth_max = depth_map.max()
            depth_norm = (depth_map - depth_min) / (depth_max - depth_min)
            
            # Colorize depth map
            depth_colorized = cv2.applyColorMap(
                (depth_norm * 255).astype(np.uint8),
                cv2.COLORMAP_INFERNO
            )
            
            return DepthResult(
                depth_map=depth_map,
                colorized=depth_colorized,
                min_depth=float(depth_min),
                max_depth=float(depth_max)
            )
            
        except Exception as e:
            logger.error(f"Error in depth estimation: {e}")
            return DepthResult(depth_map=np.zeros_like(image[:,:,0]))
    
    def track_objects(self, detections: List[Dict[str, Any]], 
                     frame: np.ndarray) -> List[TrackingResult]:
        """Track objects using simple IOU tracking.
        
        Args:
            detections: List of object detections
            frame: Current video frame
            
        Returns:
            List of tracking results
        """
        if self.object_tracker is None:
            return []
        
        try:
            results = []
            
            # Update tracking
            tracked_objects = {}
            
            for det in detections:
                bbox = det['bbox']
                label = det['label']
                conf = det['confidence']
                
                # Find best match
                best_iou = 0
                best_id = None
                
                for obj_id, obj in self.object_tracker.items():
                    if obj['label'] != label:
                        continue
                        
                    iou = self._compute_iou(bbox, obj['bbox'])
                    if iou > best_iou:
                        best_iou = iou
                        best_id = obj_id
                
                if best_iou > 0.5:
                    # Update existing track
                    obj_id = best_id
                    self.object_tracker[obj_id]['bbox'] = bbox
                    self.object_tracker[obj_id]['trajectory'].append(
                        (bbox[0], bbox[1])
                    )
                else:
                    # Create new track
                    obj_id = len(self.object_tracker)
                    self.object_tracker[obj_id] = {
                        'label': label,
                        'bbox': bbox,
                        'trajectory': [(bbox[0], bbox[1])]
                    }
                
                tracked_objects[obj_id] = True
                
                results.append(TrackingResult(
                    object_id=obj_id,
                    label=label,
                    bbox=bbox,
                    confidence=conf,
                    trajectory=self.object_tracker[obj_id]['trajectory']
                ))
            
            # Remove stale tracks
            for obj_id in list(self.object_tracker.keys()):
                if obj_id not in tracked_objects:
                    del self.object_tracker[obj_id]
            
            return results
            
        except Exception as e:
            logger.error(f"Error in object tracking: {e}")
            return []
    
    def _compute_iou(self, bbox1: Tuple[float, float, float, float],
                    bbox2: Tuple[float, float, float, float]) -> float:
        """Compute IOU between two bounding boxes."""
        x1 = max(bbox1[0], bbox2[0])
        y1 = max(bbox1[1], bbox2[1])
        x2 = min(bbox1[2], bbox2[2])
        y2 = min(bbox1[3], bbox2[3])
        
        if x2 < x1 or y2 < y1:
            return 0.0
        
        intersection = (x2 - x1) * (y2 - y1)
        
        area1 = (bbox1[2] - bbox1[0]) * (bbox1[3] - bbox1[1])
        area2 = (bbox2[2] - bbox2[0]) * (bbox2[3] - bbox2[1])
        union = area1 + area2 - intersection
        
        return intersection / union if union > 0 else 0.0
    
    def cleanup(self):
        """Clean up resources."""
        if hasattr(self, 'sam_predictor'):
            del self.sam_predictor
        if hasattr(self, 'depth_estimator'):
            del self.depth_estimator
        if hasattr(self, 'object_tracker'):
            del self.object_tracker
