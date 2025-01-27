"""Model manager for vision service."""
import os
import torch
import numpy as np
from typing import Dict, List, Any, Optional, Tuple, Type
from abc import ABC, abstractmethod
import cv2
from pathlib import Path

class ModelInterface(ABC):
    """Interface for vision models."""
    
    @abstractmethod
    def load_model(self, model_path: str, config: Dict[str, Any]) -> Any:
        """Load model from file.
        
        Args:
            model_path: Path to model file
            config: Model configuration
            
        Returns:
            Loaded model
        """
        pass
    
    @abstractmethod
    def preprocess(self, input_data: np.ndarray) -> torch.Tensor:
        """Preprocess input data.
        
        Args:
            input_data: Input data
            
        Returns:
            Preprocessed data
        """
        pass
    
    @abstractmethod
    def predict(self, input_data: torch.Tensor) -> Any:
        """Run prediction on preprocessed data.
        
        Args:
            input_data: Preprocessed input data
            
        Returns:
            Model predictions
        """
        pass
    
    @abstractmethod
    def postprocess(self, output_data: Any) -> Any:
        """Postprocess model output.
        
        Args:
            output_data: Model output
            
        Returns:
            Processed output
        """
        pass

class ModelManager:
    """Manages vision models."""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize model manager.
        
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
        
        # Initialize model registry
        self.model_registry: Dict[str, Type[ModelInterface]] = {}
        
        # Initialize loaded models
        self.loaded_models: Dict[str, Tuple[ModelInterface, Dict[str, Any]]] = {}
    
    def register_model(self, model_name: str, model_class: Type[ModelInterface]):
        """Register a model class.
        
        Args:
            model_name: Name of the model
            model_class: Model class
        """
        self.model_registry[model_name] = model_class
    
    def load_model(self, model_name: str, model_path: str,
                  config: Dict[str, Any]) -> Tuple[Any, Dict[str, Any]]:
        """Load a model.
        
        Args:
            model_name: Name of the model
            model_path: Path to model file
            config: Model configuration
            
        Returns:
            Tuple of (model, metadata)
        """
        # Check if model is already loaded
        if model_name in self.loaded_models:
            return self.loaded_models[model_name]
        
        # Get model class
        if model_name not in self.model_registry:
            raise ValueError(f"Model {model_name} not registered")
        model_class = self.model_registry[model_name]
        
        # Create model instance
        model = model_class()
        
        # Load model
        loaded_model = model.load_model(model_path, config)
        
        # Store model
        self.loaded_models[model_name] = (model, model.metadata)
        
        return model, model.metadata
    
    def unload_model(self, model_name: str):
        """Unload a model.
        
        Args:
            model_name: Name of the model
        """
        if model_name in self.loaded_models:
            del self.loaded_models[model_name]
    
    def get_model(self, model_name: str) -> Optional[Tuple[ModelInterface, Dict[str, Any]]]:
        """Get a loaded model.
        
        Args:
            model_name: Name of the model
            
        Returns:
            Tuple of (model, metadata) if loaded, None otherwise
        """
        return self.loaded_models.get(model_name)
    
    def cleanup(self):
        """Clean up resources."""
        # Unload all models
        for model_name in list(self.loaded_models.keys()):
            self.unload_model(model_name)
        
        # Clear registries
        self.model_registry.clear()
        self.loaded_models.clear()
