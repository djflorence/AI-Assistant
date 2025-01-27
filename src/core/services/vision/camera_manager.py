"""Camera management for real-time video processing."""
import cv2
import numpy as np
from typing import Dict, List, Any, Optional, Tuple, Callable
import threading
import queue
import time
from dataclasses import dataclass
from datetime import datetime

@dataclass
class CameraConfig:
    """Camera configuration."""
    device_id: int = 0
    width: int = 1280
    height: int = 720
    fps: int = 30
    buffer_size: int = 10
    auto_focus: bool = True
    auto_exposure: bool = True

@dataclass
class CameraFrame:
    """Camera frame with metadata."""
    frame: np.ndarray
    timestamp: datetime
    frame_number: int
    camera_id: int

class CameraManager:
    """Manages camera devices and real-time processing."""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize camera manager.
        
        Args:
            config: Configuration dictionary
        """
        self.config = config
        self.vision_config = config['services']['vision']
        
        # Camera state
        self.cameras: Dict[int, cv2.VideoCapture] = {}
        self.camera_configs: Dict[int, CameraConfig] = {}
        self.frame_queues: Dict[int, queue.Queue] = {}
        self.processing_queues: Dict[int, queue.Queue] = {}
        self.camera_threads: Dict[int, threading.Thread] = {}
        self.processing_threads: Dict[int, threading.Thread] = {}
        
        # Synchronization
        self.running = False
        self.lock = threading.Lock()
        
        # Frame processing
        self.frame_processors: Dict[int, List[Callable]] = {}
        self.frame_callbacks: Dict[int, List[Callable]] = {}
        
        # Performance monitoring
        self.fps_stats: Dict[int, List[float]] = {}
        self.last_frames: Dict[int, datetime] = {}
    
    def add_camera(self, camera_id: int, config: Optional[CameraConfig] = None) -> bool:
        """Add a camera device.
        
        Args:
            camera_id: Camera device ID
            config: Optional camera configuration
            
        Returns:
            True if camera added successfully
        """
        with self.lock:
            if camera_id in self.cameras:
                return False
            
            try:
                # Initialize camera
                cap = cv2.VideoCapture(camera_id)
                if not cap.isOpened():
                    return False
                
                # Apply configuration
                camera_config = config or CameraConfig()
                cap.set(cv2.CAP_PROP_FRAME_WIDTH, camera_config.width)
                cap.set(cv2.CAP_PROP_FRAME_HEIGHT, camera_config.height)
                cap.set(cv2.CAP_PROP_FPS, camera_config.fps)
                
                if camera_config.auto_focus:
                    cap.set(cv2.CAP_PROP_AUTOFOCUS, 1)
                if camera_config.auto_exposure:
                    cap.set(cv2.CAP_PROP_AUTO_EXPOSURE, 1)
                
                # Initialize queues and stats
                self.cameras[camera_id] = cap
                self.camera_configs[camera_id] = camera_config
                self.frame_queues[camera_id] = queue.Queue(maxsize=camera_config.buffer_size)
                self.processing_queues[camera_id] = queue.Queue()
                self.fps_stats[camera_id] = []
                self.frame_processors[camera_id] = []
                self.frame_callbacks[camera_id] = []
                
                return True
                
            except Exception as e:
                print(f"Error adding camera {camera_id}: {e}")
                return False
    
    def remove_camera(self, camera_id: int):
        """Remove a camera device.
        
        Args:
            camera_id: Camera device ID
        """
        with self.lock:
            if camera_id in self.cameras:
                # Stop camera thread
                if camera_id in self.camera_threads:
                    self.stop_camera(camera_id)
                
                # Release camera
                self.cameras[camera_id].release()
                
                # Clean up resources
                del self.cameras[camera_id]
                del self.camera_configs[camera_id]
                del self.frame_queues[camera_id]
                del self.processing_queues[camera_id]
                del self.fps_stats[camera_id]
                del self.frame_processors[camera_id]
                del self.frame_callbacks[camera_id]
    
    def start_camera(self, camera_id: int) -> bool:
        """Start camera capture and processing.
        
        Args:
            camera_id: Camera device ID
            
        Returns:
            True if camera started successfully
        """
        with self.lock:
            if camera_id not in self.cameras:
                return False
            
            if camera_id in self.camera_threads:
                return True
            
            try:
                # Start capture thread
                self.camera_threads[camera_id] = threading.Thread(
                    target=self._capture_loop,
                    args=(camera_id,)
                )
                self.camera_threads[camera_id].daemon = True
                self.camera_threads[camera_id].start()
                
                # Start processing thread
                self.processing_threads[camera_id] = threading.Thread(
                    target=self._processing_loop,
                    args=(camera_id,)
                )
                self.processing_threads[camera_id].daemon = True
                self.processing_threads[camera_id].start()
                
                return True
                
            except Exception as e:
                print(f"Error starting camera {camera_id}: {e}")
                return False
    
    def stop_camera(self, camera_id: int):
        """Stop camera capture and processing.
        
        Args:
            camera_id: Camera device ID
        """
        with self.lock:
            if camera_id in self.camera_threads:
                # Clear queues
                with self.frame_queues[camera_id].mutex:
                    self.frame_queues[camera_id].queue.clear()
                with self.processing_queues[camera_id].mutex:
                    self.processing_queues[camera_id].queue.clear()
                
                # Stop threads
                if camera_id in self.camera_threads:
                    self.camera_threads[camera_id].join()
                    del self.camera_threads[camera_id]
                
                if camera_id in self.processing_threads:
                    self.processing_threads[camera_id].join()
                    del self.processing_threads[camera_id]
    
    def add_frame_processor(self, camera_id: int, processor: Callable):
        """Add frame processor function.
        
        Args:
            camera_id: Camera device ID
            processor: Processor function
        """
        with self.lock:
            if camera_id in self.frame_processors:
                self.frame_processors[camera_id].append(processor)
    
    def add_frame_callback(self, camera_id: int, callback: Callable):
        """Add frame callback function.
        
        Args:
            camera_id: Camera device ID
            callback: Callback function
        """
        with self.lock:
            if camera_id in self.frame_callbacks:
                self.frame_callbacks[camera_id].append(callback)
    
    def get_latest_frame(self, camera_id: int) -> Optional[CameraFrame]:
        """Get latest frame from camera.
        
        Args:
            camera_id: Camera device ID
            
        Returns:
            Latest camera frame or None
        """
        if camera_id in self.frame_queues:
            try:
                return self.frame_queues[camera_id].get_nowait()
            except queue.Empty:
                return None
        return None
    
    def get_fps(self, camera_id: int) -> float:
        """Get current FPS for camera.
        
        Args:
            camera_id: Camera device ID
            
        Returns:
            Current FPS
        """
        if camera_id in self.fps_stats and self.fps_stats[camera_id]:
            return np.mean(self.fps_stats[camera_id])
        return 0.0
    
    def _capture_loop(self, camera_id: int):
        """Camera capture loop.
        
        Args:
            camera_id: Camera device ID
        """
        cap = self.cameras[camera_id]
        frame_count = 0
        
        while True:
            try:
                ret, frame = cap.read()
                if not ret:
                    break
                
                # Create frame object
                camera_frame = CameraFrame(
                    frame=frame,
                    timestamp=datetime.now(),
                    frame_number=frame_count,
                    camera_id=camera_id
                )
                
                # Update FPS stats
                if camera_id in self.last_frames:
                    fps = 1.0 / (
                        camera_frame.timestamp - self.last_frames[camera_id]
                    ).total_seconds()
                    self.fps_stats[camera_id].append(fps)
                    if len(self.fps_stats[camera_id]) > 30:
                        self.fps_stats[camera_id].pop(0)
                
                self.last_frames[camera_id] = camera_frame.timestamp
                
                # Add to queues
                if not self.frame_queues[camera_id].full():
                    self.frame_queues[camera_id].put(camera_frame)
                if not self.processing_queues[camera_id].full():
                    self.processing_queues[camera_id].put(camera_frame)
                
                frame_count += 1
                
            except Exception as e:
                print(f"Error in capture loop for camera {camera_id}: {e}")
                break
    
    def _processing_loop(self, camera_id: int):
        """Frame processing loop.
        
        Args:
            camera_id: Camera device ID
        """
        while True:
            try:
                # Get frame for processing
                camera_frame = self.processing_queues[camera_id].get()
                
                # Apply processors
                processed_frame = camera_frame
                for processor in self.frame_processors[camera_id]:
                    processed_frame = processor(processed_frame)
                
                # Call callbacks
                for callback in self.frame_callbacks[camera_id]:
                    callback(processed_frame)
                
            except Exception as e:
                print(f"Error in processing loop for camera {camera_id}: {e}")
                break
    
    def cleanup(self):
        """Clean up resources."""
        with self.lock:
            # Stop all cameras
            for camera_id in list(self.cameras.keys()):
                self.remove_camera(camera_id)
            
            # Clear all collections
            self.cameras.clear()
            self.camera_configs.clear()
            self.frame_queues.clear()
            self.processing_queues.clear()
            self.camera_threads.clear()
            self.processing_threads.clear()
            self.fps_stats.clear()
            self.frame_processors.clear()
            self.frame_callbacks.clear()
