import os
import queue
import threading
import speech_recognition as sr
from typing import Optional, Callable
import pyttsx3
import logging
from pydub import AudioSegment
from pydub.utils import which

# Set ffmpeg paths for pydub
FFMPEG_PATH = os.path.join(os.getenv('LOCALAPPDATA'), 'Microsoft', 'WinGet', 'Packages', 
                          'Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe', 
                          'ffmpeg-7.1-full_build', 'bin')

# Add ffmpeg to PATH
os.environ["PATH"] = FFMPEG_PATH + os.pathsep + os.environ.get("PATH", "")

# Override pydub's which function to always return our ffmpeg path
def _which(program):
    if program in ['ffmpeg', 'avconv']:
        return os.path.join(FFMPEG_PATH, 'ffmpeg.exe')
    elif program in ['ffprobe', 'avprobe']:
        return os.path.join(FFMPEG_PATH, 'ffprobe.exe')
    return None

# Monkey patch pydub's which function
import pydub.utils
pydub.utils.which = _which

# Set paths in AudioSegment
AudioSegment.converter = os.path.join(FFMPEG_PATH, 'ffmpeg.exe')
AudioSegment.ffmpeg = os.path.join(FFMPEG_PATH, 'ffmpeg.exe')
AudioSegment.ffprobe = os.path.join(FFMPEG_PATH, 'ffprobe.exe')

# Also set paths in pydub's converter module
import pydub.audio_segment
pydub.audio_segment.converter = os.path.join(FFMPEG_PATH, 'ffmpeg.exe')
pydub.audio_segment.FFMPEG_PATH = os.path.join(FFMPEG_PATH, 'ffmpeg.exe')
pydub.audio_segment.FFPROBE_PATH = os.path.join(FFMPEG_PATH, 'ffprobe.exe')

# Verify ffmpeg is accessible
if not which("ffmpeg"):
    logging.warning("ffmpeg not found in PATH")

class VoiceService:
    def __init__(self):
        self.recognizer = sr.Recognizer()
        self.engine = pyttsx3.init()
        self.recording = False
        self.enabled = True
        self._recording_thread = None
        
    def setup_voice(self, rate: int = 150, volume: float = 1.0):
        """Configure voice properties"""
        try:
            self.engine.setProperty('rate', rate)
            self.engine.setProperty('volume', volume)
            
            # Get available voices and set a default one
            voices = self.engine.getProperty('voices')
            if voices:
                self.engine.setProperty('voice', voices[0].id)
        except Exception as e:
            logging.error(f"Error setting up voice: {e}")

    def is_enabled(self) -> bool:
        """Check if voice service is enabled"""
        return self.enabled

    def is_recording(self) -> bool:
        """Check if currently recording"""
        return self.recording

    def start_recording(self, callback: Callable[[str], None]):
        """Start recording audio input"""
        if self.recording:
            return
            
        self.recording = True
        
        def record_audio():
            with sr.Microphone() as source:
                try:
                    self.recognizer.adjust_for_ambient_noise(source, duration=1)
                    while self.recording:
                        try:
                            audio = self.recognizer.listen(source, timeout=1, phrase_time_limit=10)
                            try:
                                text = self.recognizer.recognize_google(audio)
                                if text and callback:
                                    callback(text)
                            except sr.UnknownValueError:
                                pass
                            except sr.RequestError as e:
                                logging.error(f"Could not request results: {e}")
                        except sr.WaitTimeoutError:
                            continue
                except Exception as e:
                    logging.error(f"Error in record_audio: {e}")
                    self.recording = False
        
        self._recording_thread = threading.Thread(target=record_audio, daemon=True)
        self._recording_thread.start()

    def stop_recording(self):
        """Stop recording audio input"""
        self.recording = False
        if self._recording_thread:
            self._recording_thread.join(timeout=1)
            self._recording_thread = None

    def speak(self, text: str):
        """Convert text to speech"""
        if not self.enabled:
            return
            
        def speak_text():
            try:
                self.engine.say(text)
                self.engine.runAndWait()
            except Exception as e:
                logging.error(f"Error in speak_text: {e}")

        threading.Thread(target=speak_text, daemon=True).start()

    def toggle(self):
        """Toggle voice service on/off"""
        self.enabled = not self.enabled
        if not self.enabled and self.recording:
            self.stop_recording()
