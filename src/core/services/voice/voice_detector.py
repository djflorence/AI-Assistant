"""Voice activity detection for improved speech recognition."""
import numpy as np
from typing import Optional, Tuple, List
from dataclasses import dataclass
import collections
from scipy.signal import butter, lfilter
import threading

@dataclass
class VADParams:
    """Voice Activity Detection parameters."""
    frame_duration: float = 0.03  # Frame duration in seconds
    min_speech_duration: float = 0.3  # Minimum speech duration
    min_silence_duration: float = 0.5  # Minimum silence duration
    speech_energy_threshold: float = 0.6  # Energy threshold for speech
    speech_correlation_threshold: float = 0.5  # Correlation threshold
    smoothing_window: int = 5  # Number of frames for smoothing

class VoiceDetector:
    """Detects voice activity in audio stream."""
    
    def __init__(self, sample_rate: int = 16000, params: Optional[VADParams] = None):
        """Initialize voice detector.
        
        Args:
            sample_rate: Audio sample rate
            params: VAD parameters
        """
        self.sample_rate = sample_rate
        self.params = params or VADParams()
        
        # Calculate frame size
        self.frame_size = int(sample_rate * self.params.frame_duration)
        
        # Initialize state
        self.reset_state()
        
        # Design bandpass filter for speech frequencies (300-3000 Hz)
        nyquist = sample_rate / 2
        low = 300 / nyquist
        high = 3000 / nyquist
        self.b, self.a = butter(4, [low, high], btype='band')
        
        # Thread safety
        self._lock = threading.Lock()
    
    def reset_state(self):
        """Reset detector state."""
        self.is_speech = False
        self.speech_start_time: Optional[float] = None
        self.silence_start_time: Optional[float] = None
        self.energy_history = collections.deque(maxlen=self.params.smoothing_window)
        self.correlation_history = collections.deque(maxlen=self.params.smoothing_window)
        self.prev_frame = None
    
    def process_frame(self, frame: np.ndarray, timestamp: float) -> Tuple[bool, Optional[float], Optional[float]]:
        """Process a frame of audio data.
        
        Args:
            frame: Audio frame data
            timestamp: Frame timestamp
            
        Returns:
            Tuple of (is_speech, speech_start, speech_end)
        """
        with self._lock:
            # Filter the frame
            filtered_frame = self._filter_frame(frame)
            
            # Calculate features
            energy = self._calculate_energy(filtered_frame)
            correlation = self._calculate_correlation(filtered_frame)
            
            # Update history
            self.energy_history.append(energy)
            self.correlation_history.append(correlation)
            
            # Get smoothed values
            smooth_energy = np.mean(self.energy_history) if self.energy_history else energy
            smooth_correlation = np.mean(self.correlation_history) if self.correlation_history else correlation
            
            # Detect speech
            is_speech_frame = (
                smooth_energy > self.params.speech_energy_threshold and
                smooth_correlation > self.params.speech_correlation_threshold
            )
            
            speech_start = speech_end = None
            
            if is_speech_frame and not self.is_speech:
                # Speech started
                if self.silence_start_time is None or (
                    timestamp - self.silence_start_time >= self.params.min_silence_duration
                ):
                    self.is_speech = True
                    self.speech_start_time = timestamp
                    speech_start = timestamp
                    self.silence_start_time = None
            
            elif not is_speech_frame and self.is_speech:
                # Potential speech end
                if self.silence_start_time is None:
                    self.silence_start_time = timestamp
                elif timestamp - self.silence_start_time >= self.params.min_silence_duration:
                    # Confirmed speech end
                    if self.speech_start_time is not None:
                        speech_duration = timestamp - self.speech_start_time
                        if speech_duration >= self.params.min_speech_duration:
                            speech_end = timestamp
                    
                    self.is_speech = False
                    self.speech_start_time = None
            
            # Update previous frame
            self.prev_frame = filtered_frame
            
            return self.is_speech, speech_start, speech_end
    
    def _filter_frame(self, frame: np.ndarray) -> np.ndarray:
        """Apply bandpass filter to frame.
        
        Args:
            frame: Input frame
            
        Returns:
            Filtered frame
        """
        return lfilter(self.b, self.a, frame)
    
    def _calculate_energy(self, frame: np.ndarray) -> float:
        """Calculate frame energy.
        
        Args:
            frame: Input frame
            
        Returns:
            Frame energy
        """
        return np.sum(frame ** 2) / len(frame)
    
    def _calculate_correlation(self, frame: np.ndarray) -> float:
        """Calculate correlation with previous frame.
        
        Args:
            frame: Input frame
            
        Returns:
            Correlation coefficient
        """
        if self.prev_frame is None:
            return 0.0
        
        correlation = np.correlate(frame, self.prev_frame)[0]
        norm = np.sqrt(np.sum(frame ** 2) * np.sum(self.prev_frame ** 2))
        
        return correlation / norm if norm > 0 else 0.0
