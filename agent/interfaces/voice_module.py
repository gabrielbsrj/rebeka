# voice_module.py
# VERSION: 1.0.0
# Voice module for Rebeka - TTS and STT capabilities

import os
import logging
import threading
import queue
from typing import Optional, Callable
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class VoiceConfig:
    """Configuration for voice capabilities."""
    tts_enabled: bool = True
    stt_enabled: bool = True
    tts_engine: str = "gtts"  # gtts, pyttsx3, windows
    stt_engine: str = "whisper"  # whisper, google, speech_recognition
    language: str = "pt"
    voice_rate: int = 150
    voice_volume: float = 1.0


class TextToSpeech:
    """Text-to-Speech engine for Rebeka."""
    
    def __init__(self, config: VoiceConfig):
        self.config = config
        self._speech_queue = queue.Queue()
        self._speech_thread = None
        self._running = False
        
    def speak(self, text: str, blocking: bool = False) -> None:
        """Speak the given text."""
        if not self.config.tts_enabled:
            return
            
        if blocking:
            self._speak_sync(text)
        else:
            self._speech_queue.put(text)
            if not self._running:
                self._start_speech_thread()
                
    def _start_speech_thread(self) -> None:
        """Start background speech thread."""
        self._running = True
        self._speech_thread = threading.Thread(target=self._speech_worker, daemon=True)
        self._speech_thread.start()
        
    def _speech_worker(self) -> None:
        """Background worker that processes speech queue."""
        while self._running:
            try:
                text = self._speech_queue.get(timeout=1)
                self._speak_sync(text)
            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"Speech error: {e}")
                
    def _speak_sync(self, text: str) -> None:
        """Synchronous speech."""
        try:
            if self.config.tts_engine == "gtts":
                self._speak_gtts(text)
            elif self.config.tts_engine == "pyttsx3":
                self._speak_pyttsx3(text)
            elif self.config.tts_engine == "windows":
                self._speak_windows(text)
            else:
                self._speak_gtts(text)
        except Exception as e:
            logger.error(f"TTS error: {e}")
            
    def _speak_gtts(self, text: str) -> None:
        """Google TTS (requires internet)."""
        from gtts import gTTS
        
        tts = gTTS(text=text, lang=self.config.language)
        
        temp_file = "temp_speech.mp3"
        tts.save(temp_file)
        
        os.system(f'start /min wmplayer "{temp_file}" /play /close')
        
    def _speak_pyttsx3(self, text: str) -> None:
        """pyttsx3 (offline, Windows)."""
        import pyttsx3
        
        engine = pyttsx3.init()
        engine.setProperty('rate', self.config.voice_rate)
        engine.setProperty('volume', self.config.voice_volume)
        engine.say(text)
        engine.runAndWait()
        
    def _speak_windows(self, text: str) -> None:
        """Windows SAPI (offline)."""
        import win32com.client
        import pythoncom
        
        pythoncom.CoInitialize()
        speaker = win32com.client.Dispatch("SAPI.SpVoice")
        speaker.Rate = int((self.config.voice_rate - 150) / 10)
        speaker.Volume = int(self.config.voice_volume * 100)
        speaker.Speak(text)
        
    def stop(self) -> None:
        """Stop speech."""
        self._running = False
        while not self._speech_queue.empty():
            try:
                self._speech_queue.get_nowait()
            except queue.Empty:
                break
                
    def close(self) -> None:
        """Close TTS engine."""
        self.stop()
        

class SpeechToText:
    """Speech-to-Text engine for Rebeka."""
    
    def __init__(self, config: VoiceConfig):
        self.config = config
        self._listening = False
        self._listen_thread = None
        self._callback: Optional[Callable] = None
        
    def listen(self, callback: Callable[[str], None], timeout: int = 5) -> None:
        """Start listening for speech."""
        if not self.config.stt_enabled:
            return
            
        self._callback = callback
        self._listening = True
        self._listen_thread = threading.Thread(
            target=self._listen_worker, 
            args=(timeout,),
            daemon=True
        )
        self._listen_thread.start()
        
    def _listen_worker(self, timeout: int) -> None:
        """Background worker that listens for speech."""
        try:
            if self.config.stt_engine == "whisper":
                self._listen_whisper(timeout)
            elif self.config.stt_engine == "google":
                self._listen_google(timeout)
            else:
                self._listen_speech_recognition(timeout)
        except Exception as e:
            logger.error(f"STT error: {e}")
            if self._callback:
                self._callback("")
                
    def _listen_whisper(self, timeout: int) -> None:
        """Listen using Whisper (local, accurate)."""
        import speech_recognition as sr
        
        recognizer = sr.Recognizer()
        with sr.Microphone() as source:
            recognizer.adjust_for_ambient_noise(source, duration=1)
            try:
                audio = recognizer.listen(source, timeout=timeout)
                # Use Whisper if available, otherwise Google
                try:
                    text = recognizer.recognize_whisper(audio, language=self.config.language)
                except:
                    text = recognizer.recognize_google(audio, language=self.config.language)
                    
                if self._callback:
                    self._callback(text)
            except Exception as e:
                logger.error(f"Whisper listen error: {e}")
                if self._callback:
                    self._callback("")
                    
    def _listen_google(self, timeout: int) -> None:
        """Listen using Google Speech Recognition (requires internet)."""
        import speech_recognition as sr
        
        recognizer = sr.Recognizer()
        with sr.Microphone() as source:
            recognizer.adjust_for_ambient_noise(source, duration=1)
            try:
                audio = recognizer.listen(source, timeout=timeout)
                text = recognizer.recognize_google(audio, language=self.config.language)
                if self._callback:
                    self._callback(text)
            except Exception as e:
                logger.error(f"Google STT error: {e}")
                if self._callback:
                    self._callback("")
                    
    def _listen_speech_recognition(self, timeout: int) -> None:
        """Default speech recognition."""
        self._listen_google(timeout)
        
    def stop(self) -> None:
        """Stop listening."""
        self._listening = False
        
    def close(self) -> None:
        """Close STT engine."""
        self.stop()


class VoiceManager:
    """
    Central manager for voice capabilities.
    Handles both TTS and STT.
    """
    
    def __init__(self, config: Optional[VoiceConfig] = None):
        self.config = config or VoiceConfig()
        self.tts = TextToSpeech(self.config)
        self.stt = SpeechToText(self.config)
        self._voice_enabled = True
        
    def speak(self, text: str, blocking: bool = False) -> None:
        """Rebeka speaks the given text."""
        if not self._voice_enabled:
            return
        self.tts.speak(text, blocking)
        
    def listen(self, callback: Callable[[str], None], timeout: int = 5) -> None:
        """Rebeka listens for speech."""
        if not self._voice_enabled:
            callback("")
            return
        self.stt.listen(callback, timeout)
        
    def toggle_voice(self, enabled: bool) -> None:
        """Toggle voice on/off."""
        self._voice_enabled = enabled
        
    def is_voice_enabled(self) -> bool:
        """Check if voice is enabled."""
        return self._voice_enabled
    
    def close(self) -> None:
        """Close all voice engines."""
        self.tts.close()
        self.stt.close()


# Global instance
_voice_manager: Optional[VoiceManager] = None


def get_voice_manager() -> VoiceManager:
    """Get or create the global voice manager."""
    global _voice_manager
    if _voice_manager is None:
        _voice_manager = VoiceManager()
    return _voice_manager


def speak(text: str, blocking: bool = False) -> None:
    """Quick function to make Rebeka speak."""
    get_voice_manager().speak(text, blocking)


def listen(callback: Callable[[str], None], timeout: int = 5) -> None:
    """Quick function to make Rebeka listen."""
    get_voice_manager().listen(callback, timeout)
