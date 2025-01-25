"""Configuration settings for the application."""

import os
import yaml
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Config:
    def __init__(self):
        self.config_dir = Path(__file__).parent.parent / 'config'
        self.load_config()
        
    def load_config(self):
        """Load configuration from YAML file and environment variables"""
        # Load default config
        config_file = self.config_dir / 'default.yaml'
        if not config_file.exists():
            raise FileNotFoundError(f"Configuration file not found: {config_file}")
            
        with open(config_file, 'r') as f:
            self.config = yaml.safe_load(f)
            
        # Override with environment variables
        self._override_from_env()
        
    def _override_from_env(self):
        """Override configuration with environment variables"""
        # API settings
        self.config['api']['openai']['api_key'] = os.getenv('OPENAI_API_KEY', '')
        self.config['api']['openai']['model'] = os.getenv('OPENAI_MODEL', self.config['api']['openai']['model'])
        
        # App settings
        self.config['app']['debug'] = os.getenv('DEBUG', '').lower() == 'true'
        self.config['app']['log_level'] = os.getenv('LOG_LEVEL', self.config['app']['log_level'])
        
        # Voice settings
        self.config['voice']['enabled'] = os.getenv('VOICE_ENABLED', '').lower() == 'true'
        if os.getenv('SPEECH_RECOGNITION_TIMEOUT'):
            self.config['voice']['timeout_seconds'] = int(os.getenv('SPEECH_RECOGNITION_TIMEOUT'))
            
        # Memory settings
        if os.getenv('MAX_MEMORIES'):
            self.config['memory']['max_memories'] = int(os.getenv('MAX_MEMORIES'))
        
        # Custom paths
        if os.getenv('CUSTOM_MEMORY_DIR'):
            self.config['paths']['memory_dir'] = os.getenv('CUSTOM_MEMORY_DIR')
        if os.getenv('CUSTOM_LOG_DIR'):
            self.config['paths']['logs_dir'] = os.getenv('CUSTOM_LOG_DIR')
            
    def get(self, key: str, default=None):
        """Get a configuration value using dot notation"""
        try:
            value = self.config
            for k in key.split('.'):
                value = value[k]
            return value
        except (KeyError, TypeError):
            return default
            
    def __getitem__(self, key: str):
        """Allow dictionary-style access to configuration"""
        return self.get(key)
        
# Create global config instance
config = Config()

# Backwards compatibility for existing code
OPENAI_API_KEY = config.get('api.openai.api_key', '')
CHAT_MODEL = config.get('api.openai.model', 'gpt-4')
MAX_TOKENS = config.get('api.openai.max_tokens', 800)
TEMPERATURE = config.get('api.openai.temperature', 0.7)
