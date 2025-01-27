"""Test vision service functionality."""
import os
import sys
import numpy as np
import cv2
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Add project root to path
project_root = str(Path(__file__).parent.parent)
if project_root not in sys.path:
    sys.path.append(project_root)

from src.core.event_bus import EventBus
from src.core.services.vision.vision_service import VisionService

def test_vision_service():
    """Test vision service."""
    print("\nTesting Vision Service...")
    
    # Initialize configuration
    logger.info("Creating configuration...")
    config = {
        'services': {
            'vision': {
                'models_dir': 'runtime/vision/models',
                'storage_dir': 'runtime/vision/storage'
            }
        }
    }
    
    # Create event bus and service
    logger.info("Creating event bus...")
    event_bus = EventBus()
    
    logger.info("Creating vision service...")
    vision_service = VisionService(event_bus, config)
    
    try:
        # Initialize service
        logger.info("Initializing vision service...")
        vision_service.initialize()
        logger.info("Vision service initialized successfully")
        
        print("✓ Vision service tests passed!")
        
    except Exception as e:
        logger.error(f"Error during testing: {e}")
        print(f"✗ Vision service tests failed: {e}")
        raise
        
    finally:
        # Clean up
        logger.info("Cleaning up...")
        vision_service.cleanup()

if __name__ == '__main__':
    test_vision_service()
