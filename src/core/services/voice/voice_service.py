"""Voice service for handling speech recognition and synthesis."""
from typing import Optional, Dict, Any, Callable
from datetime import datetime
import os
import threading
from dataclasses import dataclass

from src.core.interfaces.service import Service
from src.core.event_bus import EventBus, VoiceInputStarted, VoiceInputEnded
from src.core.services.voice.voice_recognizer import VoiceRecognizer, RecognitionResult
from src.core.services.voice.voice_synthesizer import VoiceSynthesizer, SynthesisResult
from src.core.services.voice.vosk_downloader import VoskModelDownloader

@dataclass
class VoiceState:
    """Current state of voice service."""
    is_listening: bool = False
    is_speaking: bool = False
    current_speech: Optional[str] = None
    last_recognition: Optional[RecognitionResult] = None
    last_synthesis: Optional[SynthesisResult] = None

class VoiceService(Service):
    """Service for handling voice interactions."""
    
    def __init__(self, event_bus: EventBus, config: Dict[str, Any]):
        """Initialize voice service.
        
        Args:
            event_bus: Application event bus
            config: Configuration dictionary
        """
        self.event_bus = event_bus
        self.config = config
        self.voice_config = config['services']['voice']
        
        # Initialize model downloader
        self.model_downloader = VoskModelDownloader()
        
        # Initialize components
        self.recognizer = VoiceRecognizer(config)
        self.synthesizer = VoiceSynthesizer(config)
        
        # Initialize state
        self.state = VoiceState()
        self.state_lock = threading.Lock()
        
        # Callback for real-time transcription
        self.transcription_callback: Optional[Callable[[str], None]] = None
    
    def initialize(self) -> None:
        """Initialize the service."""
        # Create necessary directories
        os.makedirs(os.path.join('runtime', 'voice'), exist_ok=True)
        os.makedirs(os.path.join('runtime', 'voice', 'output'), exist_ok=True)
        
        # Download Vosk model if needed
        self._ensure_vosk_model()
    
    def cleanup(self) -> None:
        """Clean up resources."""
        self.stop_listening()
        self.stop_speaking()
        self.synthesizer.cleanup()
    
    def start_listening(self, callback: Optional[Callable[[str], None]] = None) -> bool:
        """Start listening for voice input.
        
        Args:
            callback: Optional callback for real-time transcription
            
        Returns:
            True if listening started successfully
        """
        with self.state_lock:
            if self.state.is_listening:
                return False
            
            try:
                self.transcription_callback = callback
                self.recognizer.start_recording(self._handle_transcription)
                self.state.is_listening = True
                
                # Publish event
                self.event_bus.publish(VoiceInputStarted(
                    device_id=self.voice_config.get('input_device', 'default')
                ))
                
                return True
                
            except Exception as e:
                print(f"Error starting voice input: {e}")
                return False
    
    def stop_listening(self) -> Optional[RecognitionResult]:
        """Stop listening and return recognition result.
        
        Returns:
            Recognition result if successful
        """
        with self.state_lock:
            if not self.state.is_listening:
                return None
            
            try:
                result = self.recognizer.stop_recording()
                self.state.is_listening = False
                self.state.last_recognition = result
                
                if result:
                    # Publish event
                    self.event_bus.publish(VoiceInputEnded(
                        text=result.text,
                        device_id=self.voice_config.get('input_device', 'default')
                    ))
                
                return result
                
            except Exception as e:
                print(f"Error stopping voice input: {e}")
                self.state.is_listening = False
                return None
    
    def speak(self, text: str, save_audio: bool = False) -> Optional[SynthesisResult]:
        """Synthesize and speak text.
        
        Args:
            text: Text to speak
            save_audio: Whether to save audio to file
            
        Returns:
            Synthesis result if save_audio is True
        """
        with self.state_lock:
            try:
                result = self.synthesizer.speak(text, save_audio)
                self.state.is_speaking = True
                self.state.current_speech = text
                self.state.last_synthesis = result
                return result
                
            except Exception as e:
                print(f"Error in speech synthesis: {e}")
                return None
    
    def stop_speaking(self):
        """Stop current speech synthesis."""
        with self.state_lock:
            self.synthesizer.stop_speaking()
            self.state.is_speaking = False
            self.state.current_speech = None
    
    def get_state(self) -> VoiceState:
        """Get current voice service state.
        
        Returns:
            Current state
        """
        with self.state_lock:
            return self.state
    
    def get_available_voices(self) -> Dict[str, Any]:
        """Get information about available voices.
        
        Returns:
            Dictionary of voice information
        """
        voices = self.synthesizer.get_available_voices()
        return {
            'count': len(voices),
            'voices': voices
        }
    
    def set_voice(self, voice_id: str) -> bool:
        """Set the voice to use.
        
        Args:
            voice_id: ID of the voice to use
            
        Returns:
            True if voice was set successfully
        """
        return self.synthesizer.set_voice(voice_id)
    
    def get_available_models(self) -> Dict[str, Any]:
        """Get information about available speech recognition models.
        
        Returns:
            Dictionary containing available and installed models
        """
        return {
            'available': self.model_downloader.list_models(),
            'installed': self.model_downloader.get_installed_models()
        }
    
    def download_model(self, size: str, language: str, force: bool = False) -> bool:
        """Download a specific Vosk model.
        
        Args:
            size: Model size ('small' or 'medium')
            language: Language code
            force: Force download even if model exists
            
        Returns:
            True if download successful
        """
        return self.model_downloader.download_model(size, language, force)
    
    def _handle_transcription(self, text: str):
        """Handle real-time transcription results.
        
        Args:
            text: Transcribed text
        """
        if self.transcription_callback:
            self.transcription_callback(text)
    
    def _ensure_vosk_model(self):
        """Download Vosk model if not present."""
        # Get model preferences from config
        size = self.voice_config.get('vosk_model_size', 'small')
        language = self.voice_config.get('vosk_model_language', 'en')
        
        # Check if model is installed
        model_path = self.model_downloader.get_model_path(size, language)
        if not model_path:
            print(f"Downloading {size} Vosk model for language {language}...")
            success = self.model_downloader.download_model(size, language)
            if not success:
                print("Failed to download Vosk model. Speech recognition will use online service only.")
