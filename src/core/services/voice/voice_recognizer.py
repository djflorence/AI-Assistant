"""Voice recognition component."""
import speech_recognition as sr
from vosk import Model, KaldiRecognizer
import json
import sounddevice as sd
import threading
import numpy as np
import queue
from typing import Optional, Callable, Dict, Any, List
import os
from dataclasses import dataclass
from datetime import datetime

from src.core.services.voice.model_cache import ModelCache
from src.core.services.voice.voice_detector import VoiceDetector, VADParams

@dataclass
class RecognitionResult:
    """Result from voice recognition."""
    text: str
    confidence: float
    timestamp: datetime
    source: str  # 'google', 'vosk', etc.
    speech_duration: Optional[float] = None

class VoiceRecognizer:
    """Handles voice recognition using multiple backends."""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize voice recognizer.
        
        Args:
            config: Configuration dictionary
        """
        self.config = config
        self.voice_config = config['services']['voice']
        
        # Initialize recognizer
        self.recognizer = sr.Recognizer()
        self.recognizer.energy_threshold = self.voice_config.get('energy_threshold', 300)
        self.recognizer.dynamic_energy_threshold = True
        
        # Initialize model cache
        self.model_cache = ModelCache(
            max_models=self.voice_config.get('max_cached_models', 2),
            cache_duration=self.voice_config.get('model_cache_duration', 3600)
        )
        
        # Initialize voice detector
        vad_params = VADParams(
            speech_energy_threshold=self.voice_config.get('vad_energy_threshold', 0.6),
            min_speech_duration=self.voice_config.get('min_speech_duration', 0.3),
            min_silence_duration=self.voice_config.get('min_silence_duration', 0.5)
        )
        self.voice_detector = VoiceDetector(params=vad_params)
        
        # Initialize Vosk
        self._initialize_vosk()
        
        # Audio recording settings
        self.sample_rate = 16000
        self.dtype = np.int16
        self.channels = 1
        self.chunk_size = 1024
        
        # Recording state
        self.recording = False
        self.audio_queue = queue.Queue()
        self.recording_thread: Optional[threading.Thread] = None
        self.current_speech_start: Optional[float] = None
        self.buffered_audio: List[np.ndarray] = []
    
    def _initialize_vosk(self):
        """Initialize Vosk recognizer."""
        model_path = os.path.join('runtime', 'voice', 'model')
        model_key = f"{self.voice_config.get('vosk_model_size', 'small')}_{self.voice_config.get('vosk_model_language', 'en')}"
        
        if os.path.exists(model_path):
            model = self.model_cache.get_model(model_path, model_key)
            if model:
                self.vosk_model = model
                self.vosk_recognizer = KaldiRecognizer(self.vosk_model, self.sample_rate)
            else:
                self.vosk_model = None
                self.vosk_recognizer = None
        else:
            self.vosk_model = None
            self.vosk_recognizer = None
    
    def start_recording(self, callback: Optional[Callable[[str], None]] = None):
        """Start recording audio.
        
        Args:
            callback: Optional callback for real-time transcription
        """
        if self.recording:
            return
        
        self.recording = True
        self.voice_detector.reset_state()
        self.buffered_audio.clear()
        self.current_speech_start = None
        
        self.recording_thread = threading.Thread(
            target=self._record_audio,
            args=(callback,)
        )
        self.recording_thread.start()
    
    def stop_recording(self) -> Optional[RecognitionResult]:
        """Stop recording and return recognition result.
        
        Returns:
            Recognition result if successful, None otherwise
        """
        if not self.recording:
            return None
        
        self.recording = False
        if self.recording_thread:
            self.recording_thread.join()
        
        # Process any remaining audio
        audio_data = []
        while not self.audio_queue.empty():
            audio_data.append(self.audio_queue.get())
        
        # Add buffered speech
        audio_data.extend(self.buffered_audio)
        
        if not audio_data:
            return None
        
        # Convert to numpy array
        audio_array = np.concatenate(audio_data)
        
        # Calculate speech duration
        speech_duration = None
        if self.current_speech_start is not None:
            speech_duration = datetime.now().timestamp() - self.current_speech_start
        
        # Try online recognition first
        result = self._recognize_google(audio_array)
        if result:
            result.speech_duration = speech_duration
            return result
        
        # Fall back to offline recognition
        result = self._recognize_vosk(audio_array)
        if result:
            result.speech_duration = speech_duration
        return result
    
    def _record_audio(self, callback: Optional[Callable[[str], None]]):
        """Record audio in chunks.
        
        Args:
            callback: Optional callback for real-time transcription
        """
        try:
            with sd.InputStream(
                samplerate=self.sample_rate,
                channels=self.channels,
                dtype=self.dtype,
                blocksize=self.chunk_size,
                callback=self._audio_callback
            ):
                while self.recording:
                    if not self.audio_queue.empty():
                        frame = self.audio_queue.get()
                        timestamp = datetime.now().timestamp()
                        
                        # Detect voice activity
                        is_speech, speech_start, speech_end = self.voice_detector.process_frame(
                            frame, timestamp
                        )
                        
                        if speech_start:
                            self.current_speech_start = speech_start
                            self.buffered_audio.clear()
                        
                        if is_speech:
                            self.buffered_audio.append(frame)
                            
                            # Real-time transcription
                            if callback and self.vosk_recognizer:
                                if self.vosk_recognizer.AcceptWaveform(frame.tobytes()):
                                    result = json.loads(self.vosk_recognizer.Result())
                                    if result.get('text'):
                                        callback(result['text'])
                        
                        elif speech_end and self.buffered_audio:
                            # Process complete utterance
                            audio_array = np.concatenate(self.buffered_audio)
                            if callback and self.vosk_recognizer:
                                self.vosk_recognizer.AcceptWaveform(audio_array.tobytes())
                                result = json.loads(self.vosk_recognizer.FinalResult())
                                if result.get('text'):
                                    callback(result['text'])
                            
                            # Clear buffer but keep reference time
                            self.buffered_audio.clear()
        
        except Exception as e:
            print(f"Error recording audio: {e}")
            self.recording = False
    
    def _audio_callback(self, indata, frames, time, status):
        """Callback for audio input.
        
        Args:
            indata: Input audio data
            frames: Number of frames
            time: Time info
            status: Stream status
        """
        if status:
            print(f"Audio callback status: {status}")
        if self.recording:
            self.audio_queue.put(indata.copy())
    
    def _recognize_google(self, audio_array: np.ndarray) -> Optional[RecognitionResult]:
        """Recognize speech using Google Speech Recognition.
        
        Args:
            audio_array: Audio data as numpy array
            
        Returns:
            Recognition result if successful, None otherwise
        """
        try:
            # Convert to audio data format expected by speech_recognition
            audio_data = sr.AudioData(
                audio_array.tobytes(),
                self.sample_rate,
                self.dtype.itemsize
            )
            
            # Perform recognition
            text = self.recognizer.recognize_google(
                audio_data,
                language=self.voice_config.get('language', 'en-US')
            )
            
            return RecognitionResult(
                text=text,
                confidence=0.8,  # Google doesn't provide confidence
                timestamp=datetime.now(),
                source='google'
            )
            
        except sr.UnknownValueError:
            return None
        except sr.RequestError as e:
            print(f"Could not request results from Google Speech Recognition: {e}")
            return None
    
    def _recognize_vosk(self, audio_array: np.ndarray) -> Optional[RecognitionResult]:
        """Recognize speech using Vosk offline recognition.
        
        Args:
            audio_array: Audio data as numpy array
            
        Returns:
            Recognition result if successful, None otherwise
        """
        if not self.vosk_recognizer:
            return None
        
        try:
            self.vosk_recognizer.AcceptWaveform(audio_array.tobytes())
            result = json.loads(self.vosk_recognizer.FinalResult())
            
            if result.get('text'):
                return RecognitionResult(
                    text=result['text'],
                    confidence=float(result.get('confidence', 0.6)),
                    timestamp=datetime.now(),
                    source='vosk'
                )
            
            return None
            
        except Exception as e:
            print(f"Error in Vosk recognition: {e}")
            return None

    def get_cache_stats(self) -> Dict[str, Any]:
        """Get model cache statistics.
        
        Returns:
            Cache statistics
        """
        return self.model_cache.get_cache_stats()
