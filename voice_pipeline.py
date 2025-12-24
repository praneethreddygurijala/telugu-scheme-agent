"""
Voice Pipeline for Telugu Speech-to-Text and Text-to-Speech
Web Service Version - NO SOUNDDEVICE (for cloud deployment)
"""

from google.cloud import speech_v1p1beta1 as speech
from google.cloud import texttospeech
from typing import Tuple
import os
import io
import wave


class VoiceConfig:
    """Configuration for voice services"""
    
    # Audio settings
    SAMPLE_RATE = 16000
    CHANNELS = 1
    DTYPE = 'int16'
    
    # Telugu language codes
    TELUGU_GOOGLE = "te-IN"
    
    # Voice names
    GOOGLE_VOICE = "te-IN-Standard-A"  # Female voice


class GoogleSpeechService:
    """Google Cloud Speech-to-Text and Text-to-Speech"""
    
    def __init__(self, credentials_path: str):
        """
        Initialize Google Speech services
        
        Args:
            credentials_path: Path to Google Cloud credentials JSON
        """
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = credentials_path
        
        self.stt_client = speech.SpeechClient()
        self.tts_client = texttospeech.TextToSpeechClient()
        
    def speech_to_text(self, audio_data: bytes) -> Tuple[str, float]:
        """
        Convert Telugu speech to text
        
        Args:
            audio_data: Raw audio bytes (WAV format)
            
        Returns:
            Tuple of (transcribed_text, confidence_score)
        """
        audio = speech.RecognitionAudio(content=audio_data)
        
        config = speech.RecognitionConfig(
            encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
            sample_rate_hertz=VoiceConfig.SAMPLE_RATE,
            language_code=VoiceConfig.TELUGU_GOOGLE,
            enable_automatic_punctuation=True,
            model="default",
            use_enhanced=True,
            alternative_language_codes=["en-IN"]
        )
        
        try:
            response = self.stt_client.recognize(config=config, audio=audio)
            
            if not response.results:
                return "", 0.0
            
            result = response.results[0]
            alternative = result.alternatives[0]
            
            return alternative.transcript, alternative.confidence
            
        except Exception as e:
            print(f"STT Error: {e}")
            return "", 0.0
    
    def text_to_speech(self, text: str, output_file: str = "output.wav") -> bool:
        """
        Convert Telugu text to speech
        
        Args:
            text: Telugu text to synthesize
            output_file: Path to save audio file
            
        Returns:
            Success status
        """
        synthesis_input = texttospeech.SynthesisInput(text=text)
        
        voice = texttospeech.VoiceSelectionParams(
            language_code=VoiceConfig.TELUGU_GOOGLE,
            name=VoiceConfig.GOOGLE_VOICE,
            ssml_gender=texttospeech.SsmlVoiceGender.FEMALE
        )
        
        audio_config = texttospeech.AudioConfig(
            audio_encoding=texttospeech.AudioEncoding.LINEAR16,
            sample_rate_hertz=VoiceConfig.SAMPLE_RATE,
            speaking_rate=1.0,
            pitch=0.0
        )
        
        try:
            response = self.tts_client.synthesize_speech(
                input=synthesis_input,
                voice=voice,
                audio_config=audio_config
            )
            
            # Save audio to file
            with open(output_file, "wb") as out:
                out.write(response.audio_content)
            
            return True
            
        except Exception as e:
            print(f"TTS Error: {e}")
            return False


class VoicePipeline:
    """Complete voice pipeline using Google Cloud (Web Service Version)"""
    
    def __init__(self, credentials_path: str):
        """
        Initialize voice pipeline
        
        Args:
            credentials_path: Path to Google Cloud credentials JSON
        """
        self.speech_service = GoogleSpeechService(credentials_path=credentials_path)
    
    def speak(self, text: str, output_file: str = "response.wav") -> bool:
        """
        Convert text to speech
        
        Args:
            text: Telugu text to speak
            output_file: Output filename
            
        Returns:
            Success status
        """
        return self.speech_service.text_to_speech(text, output_file)