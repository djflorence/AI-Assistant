"""Vosk model downloader and manager."""
import os
import requests
import zipfile
import json
from typing import Dict, Optional, List
from tqdm import tqdm

class VoskModelDownloader:
    """Handles downloading and managing Vosk models."""
    
    # Available models and their URLs
    MODELS = {
        'small': {
            'en': {
                'url': 'https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip',
                'size': '40M',
                'description': 'Lightweight English model, good for simple commands'
            },
            'fr': {
                'url': 'https://alphacephei.com/vosk/models/vosk-model-small-fr-0.22.zip',
                'size': '39M',
                'description': 'Lightweight French model'
            }
        },
        'medium': {
            'en': {
                'url': 'https://alphacephei.com/vosk/models/vosk-model-en-us-0.22.zip',
                'size': '1.8G',
                'description': 'Accurate general-purpose English model'
            }
        }
    }
    
    def __init__(self, base_path: str = None):
        """Initialize the downloader.
        
        Args:
            base_path: Base path for model storage
        """
        self.base_path = base_path or os.path.join('runtime', 'voice', 'model')
        os.makedirs(self.base_path, exist_ok=True)
        
        # Create model info file
        self.info_file = os.path.join(self.base_path, 'model_info.json')
        if not os.path.exists(self.info_file):
            self._save_model_info({})
    
    def download_model(self, size: str = 'small', language: str = 'en', 
                      force: bool = False) -> bool:
        """Download a Vosk model.
        
        Args:
            size: Model size ('small' or 'medium')
            language: Language code
            force: Force download even if model exists
            
        Returns:
            True if download successful
        """
        # Validate model selection
        if size not in self.MODELS or language not in self.MODELS[size]:
            print(f"No {size} model available for language {language}")
            return False
        
        model_info = self.MODELS[size][language]
        model_url = model_info['url']
        model_path = os.path.join(self.base_path, f"{size}_{language}")
        
        # Check if model already exists
        if os.path.exists(model_path) and not force:
            print(f"Model already exists at {model_path}")
            return True
        
        try:
            # Download the model
            print(f"Downloading {size} {language} model ({model_info['size']})...")
            zip_path = os.path.join(self.base_path, 'temp_model.zip')
            
            response = requests.get(model_url, stream=True)
            total_size = int(response.headers.get('content-length', 0))
            
            with open(zip_path, 'wb') as f, tqdm(
                desc=f"{size}_{language}",
                total=total_size,
                unit='iB',
                unit_scale=True,
                unit_divisor=1024,
            ) as pbar:
                for data in response.iter_content(chunk_size=1024):
                    size = f.write(data)
                    pbar.update(size)
            
            # Extract the model
            print("Extracting model...")
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(model_path)
            
            # Clean up
            os.remove(zip_path)
            
            # Update model info
            self._update_model_info(size, language, model_path)
            
            print(f"Model downloaded and extracted to {model_path}")
            return True
            
        except Exception as e:
            print(f"Error downloading model: {e}")
            if os.path.exists(zip_path):
                os.remove(zip_path)
            return False
    
    def list_models(self) -> Dict[str, List[str]]:
        """List available models for download.
        
        Returns:
            Dictionary of available models by size
        """
        return {
            size: list(languages.keys())
            for size, languages in self.MODELS.items()
        }
    
    def get_installed_models(self) -> Dict[str, Dict[str, str]]:
        """Get information about installed models.
        
        Returns:
            Dictionary of installed model information
        """
        with open(self.info_file, 'r') as f:
            return json.load(f)
    
    def get_model_path(self, size: str = 'small', 
                      language: str = 'en') -> Optional[str]:
        """Get path to installed model.
        
        Args:
            size: Model size
            language: Language code
            
        Returns:
            Path to model if installed, None otherwise
        """
        models = self.get_installed_models()
        model_key = f"{size}_{language}"
        return models.get(model_key, {}).get('path')
    
    def _update_model_info(self, size: str, language: str, path: str):
        """Update installed model information.
        
        Args:
            size: Model size
            language: Language code
            path: Path to installed model
        """
        models = self.get_installed_models()
        model_key = f"{size}_{language}"
        
        models[model_key] = {
            'size': size,
            'language': language,
            'path': path,
            'installed_date': datetime.now().isoformat()
        }
        
        self._save_model_info(models)
    
    def _save_model_info(self, info: Dict):
        """Save model information to file.
        
        Args:
            info: Model information dictionary
        """
        with open(self.info_file, 'w') as f:
            json.dump(info, f, indent=2)
