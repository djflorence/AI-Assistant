"""Model cache manager for Vosk models."""
import os
import json
import shutil
import threading
from typing import Dict, Optional, Any
from datetime import datetime, timedelta
import time
from vosk import Model
import weakref

class ModelCache:
    """Manages caching of loaded Vosk models."""
    
    def __init__(self, max_models: int = 2, cache_duration: int = 3600):
        """Initialize the model cache.
        
        Args:
            max_models: Maximum number of models to keep in memory
            cache_duration: Duration to keep models in cache (seconds)
        """
        self.max_models = max_models
        self.cache_duration = cache_duration
        
        # Cache storage: model_key -> (model, last_access_time)
        self._cache: Dict[str, tuple[Model, float]] = {}
        self._cache_lock = threading.Lock()
        
        # Start cache cleanup thread
        self._cleanup_thread = threading.Thread(
            target=self._cleanup_loop,
            daemon=True
        )
        self._cleanup_thread.start()
    
    def get_model(self, model_path: str, model_key: str) -> Optional[Model]:
        """Get a model from cache or load it.
        
        Args:
            model_path: Path to the model
            model_key: Unique key for the model (e.g., 'small_en')
            
        Returns:
            Loaded model or None if failed
        """
        with self._cache_lock:
            # Check if model is in cache
            if model_key in self._cache:
                model, _ = self._cache[model_key]
                self._update_access_time(model_key)
                return model
            
            # Load model
            try:
                model = Model(model_path)
                
                # Add to cache, potentially removing oldest model
                self._add_to_cache(model_key, model)
                
                return model
                
            except Exception as e:
                print(f"Error loading model {model_key}: {e}")
                return None
    
    def clear_cache(self):
        """Clear all models from cache."""
        with self._cache_lock:
            self._cache.clear()
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics.
        
        Returns:
            Dictionary of cache statistics
        """
        with self._cache_lock:
            return {
                'models_cached': len(self._cache),
                'max_models': self.max_models,
                'models': {
                    key: {
                        'last_access': datetime.fromtimestamp(access_time).isoformat()
                    }
                    for key, (_, access_time) in self._cache.items()
                }
            }
    
    def _add_to_cache(self, model_key: str, model: Model):
        """Add model to cache, removing oldest if necessary.
        
        Args:
            model_key: Model key
            model: Model instance
        """
        # Remove oldest model if cache is full
        if len(self._cache) >= self.max_models:
            oldest_key = min(
                self._cache.keys(),
                key=lambda k: self._cache[k][1]
            )
            del self._cache[oldest_key]
        
        # Add new model
        self._cache[model_key] = (model, time.time())
    
    def _update_access_time(self, model_key: str):
        """Update last access time for a model.
        
        Args:
            model_key: Model key
        """
        if model_key in self._cache:
            model, _ = self._cache[model_key]
            self._cache[model_key] = (model, time.time())
    
    def _cleanup_loop(self):
        """Periodically clean up expired models."""
        while True:
            time.sleep(60)  # Check every minute
            self._cleanup_expired()
    
    def _cleanup_expired(self):
        """Remove expired models from cache."""
        current_time = time.time()
        with self._cache_lock:
            expired = [
                key for key, (_, access_time) in self._cache.items()
                if current_time - access_time > self.cache_duration
            ]
            for key in expired:
                del self._cache[key]
