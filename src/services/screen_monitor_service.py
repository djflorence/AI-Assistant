"""Service for monitoring screen content and providing context-aware responses."""

import time
import threading
import queue
import logging
from datetime import datetime
import pyautogui
import numpy as np
from PIL import Image
import io
import os

class ScreenMonitorService:
    def __init__(self, vision_service, chat_interface):
        """Initialize the screen monitor service."""
        self.vision_service = vision_service
        self.chat_interface = chat_interface
        self.is_monitoring = False
        self.screenshot_queue = queue.Queue()
        self.last_screenshot_time = 0
        self.screenshot_interval = 5  # seconds
        self.monitoring_thread = None
        self.processing_thread = None
        
        # Create screenshots directory if it doesn't exist
        self.screenshots_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'screenshots')
        os.makedirs(self.screenshots_dir, exist_ok=True)
    
    def start_monitoring(self):
        """Start the screen monitoring threads."""
        if not self.is_monitoring:
            self.is_monitoring = True
            self.monitoring_thread = threading.Thread(target=self._monitor_screen, daemon=True)
            self.processing_thread = threading.Thread(target=self.process_screenshots, daemon=True)
            self.monitoring_thread.start()
            self.processing_thread.start()
            logging.info("Screen monitoring started")
    
    def stop_monitoring(self):
        """Stop the screen monitoring threads."""
        self.is_monitoring = False
        if self.monitoring_thread:
            self.monitoring_thread.join(timeout=1.0)
        if self.processing_thread:
            self.processing_thread.join(timeout=1.0)
        logging.info("Screen monitoring stopped")
    
    def _monitor_screen(self):
        """Continuously capture screenshots at regular intervals."""
        while self.is_monitoring:
            try:
                current_time = time.time()
                if current_time - self.last_screenshot_time >= self.screenshot_interval:
                    # Take screenshot
                    screenshot = pyautogui.screenshot()
                    
                    # Convert to bytes
                    img_byte_arr = io.BytesIO()
                    screenshot.save(img_byte_arr, format='PNG')
                    img_byte_arr = img_byte_arr.getvalue()
                    
                    # Save with timestamp
                    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                    filename = f'screenshot_{timestamp}.png'
                    filepath = os.path.join(self.screenshots_dir, filename)
                    screenshot.save(filepath)
                    
                    # Add to processing queue
                    self.screenshot_queue.put((filepath, img_byte_arr))
                    self.last_screenshot_time = current_time
                    
                time.sleep(0.1)  # Small sleep to prevent CPU overuse
                
            except Exception as e:
                logging.error(f"Error in screen monitoring: {str(e)}")
                time.sleep(1)  # Sleep longer on error
    
    def process_screenshots(self):
        """Process screenshots from the queue."""
        while self.is_monitoring:
            try:
                # Get screenshot from queue with timeout
                try:
                    filepath, img_bytes = self.screenshot_queue.get(timeout=1.0)
                except queue.Empty:
                    continue
                
                # Analyze the screenshot
                result = self.vision_service.analyze_image(filepath)
                
                if result["success"]:
                    # Extract text if present
                    if result.get("extracted_text"):
                        text = result["extracted_text"].strip()
                        if text:
                            logging.info(f"Text found in screenshot: {text[:100]}...")
                    
                    # Get general description
                    if result.get("description"):
                        logging.info(f"Screenshot description: {result['description'][:100]}...")
                    
                    # Clean up old screenshots
                    self._cleanup_old_screenshots()
                    
                else:
                    logging.error(f"Error analyzing screenshot: {result.get('error', 'Unknown error')}")
                
            except Exception as e:
                logging.error(f"Error processing screenshot: {str(e)}")
                time.sleep(1)  # Sleep on error
    
    def _cleanup_old_screenshots(self):
        """Clean up screenshots older than 1 hour."""
        try:
            current_time = time.time()
            for filename in os.listdir(self.screenshots_dir):
                filepath = os.path.join(self.screenshots_dir, filename)
                if os.path.getmtime(filepath) < current_time - 3600:  # 1 hour
                    os.remove(filepath)
        except Exception as e:
            logging.error(f"Error cleaning up screenshots: {str(e)}")
    
    def get_current_context(self):
        """Get the current screen context."""
        try:
            # Take a new screenshot
            screenshot = pyautogui.screenshot()
            
            # Save with timestamp
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f'context_{timestamp}.png'
            filepath = os.path.join(self.screenshots_dir, filename)
            screenshot.save(filepath)
            
            # Analyze the screenshot
            result = self.vision_service.analyze_image(filepath)
            
            if result["success"]:
                context = {
                    "description": result.get("description", ""),
                    "text": result.get("extracted_text", ""),
                    "timestamp": timestamp
                }
                return context
            else:
                logging.error(f"Error getting context: {result.get('error', 'Unknown error')}")
                return None
                
        except Exception as e:
            logging.error(f"Error getting current context: {str(e)}")
            return None
