"""Text-to-speech synthesis component."""
import pyttsx3
import threading
from typing import Optional, Dict, Any, List
from queue import Queue
import os
from dataclasses import dataclass
from datetime import datetime

@dataclass
class SynthesisResult:
    """Result from voice synthesis."""
    text: str
    audio_file: str
    timestamp: datetime
    voice_id: str
    duration: float

class VoiceSynthesizer:
    """Handles text-to-speech synthesis."""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize voice synthesizer.
        
        Args:
            config: Configuration dictionary
        """
        self.config = config
        self.voice_config = config['services']['voice']
        
        # Initialize engine
        self.engine = pyttsx3.init()
        self.setup_engine()
        
        # Speech queue
        self.speech_queue = Queue()
        self.is_speaking = False
        self.current_speech: Optional[str] = None
        
        # Start speech thread
        self.speech_thread = threading.Thread(target=self._process_speech_queue)
        self.speech_thread.daemon = True
        self.speech_thread.start()
    
    def setup_engine(self):
        """Configure the TTS engine."""
        # Set properties
        self.engine.setProperty('rate', self.voice_config.get('speech_rate', 150))
        self.engine.setProperty('volume', self.voice_config.get('volume', 1.0))
        
        # Get available voices
        voices = self.engine.getProperty('voices')
        if voices:
            # Set default voice (usually index 0 is male, 1 is female)
            voice_index = 1 if len(voices) > 1 else 0
            self.engine.setProperty('voice', voices[voice_index].id)
    
    def get_available_voices(self) -> List[Dict[str, Any]]:
        """Get list of available voices.
        
        Returns:
            List of voice information dictionaries
        """
        voices = []
        for voice in self.engine.getProperty('voices'):
            voices.append({
                'id': voice.id,
                'name': voice.name,
                'languages': voice.languages,
                'gender': voice.gender
            })
        return voices
    
    def set_voice(self, voice_id: str) -> bool:
        """Set the voice to use.
        
        Args:
            voice_id: ID of the voice to use
            
        Returns:
            True if voice was set successfully
        """
        try:
            self.engine.setProperty('voice', voice_id)
            return True
        except Exception as e:
            print(f"Error setting voice: {e}")
            return False
    
    def speak(self, text: str, save_audio: bool = False) -> Optional[SynthesisResult]:
        """Synthesize speech from text.
        
        Args:
            text: Text to synthesize
            save_audio: Whether to save audio to file
            
        Returns:
            Synthesis result if save_audio is True
        """
        if save_audio:
            # Create output directory
            output_dir = os.path.join('runtime', 'voice', 'output')
            os.makedirs(output_dir, exist_ok=True)
            
            # Generate output filename
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_file = os.path.join(output_dir, f'speech_{timestamp}.wav')
            
            try:
                # Save to file
                self.engine.save_to_file(text, output_file)
                self.engine.runAndWait()
                
                # Get voice properties
                voice = self.engine.getProperty('voice')
                duration = len(text.split()) * 0.3  # Rough estimate
                
                return SynthesisResult(
                    text=text,
                    audio_file=output_file,
                    timestamp=datetime.now(),
                    voice_id=voice,
                    duration=duration
                )
            
            except Exception as e:
                print(f"Error saving speech to file: {e}")
                if os.path.exists(output_file):
                    os.remove(output_file)
                return None
        
        else:
            # Add to speech queue
            self.speech_queue.put(text)
            return None
    
    def stop_speaking(self):
        """Stop current speech and clear queue."""
        self.engine.stop()
        with self.speech_queue.mutex:
            self.speech_queue.queue.clear()
        self.is_speaking = False
        self.current_speech = None
    
    def _process_speech_queue(self):
        """Process queued speech requests."""
        while True:
            try:
                # Get next text to speak
                text = self.speech_queue.get()
                self.is_speaking = True
                self.current_speech = text
                
                # Speak the text
                self.engine.say(text)
                self.engine.runAndWait()
                
                self.is_speaking = False
                self.current_speech = None
                
            except Exception as e:
                print(f"Error in speech processing: {e}")
                self.is_speaking = False
                self.current_speech = None
            
            finally:
                self.speech_queue.task_done()
    
    def cleanup(self):
        """Clean up resources."""
        self.stop_speaking()
        self.engine.stop()
