"""
Voice Pipeline for Telugu Speech-to-Text and Text-to-Speech
Using SoundDevice (Python 3.12 compatible) - Google Cloud Only
"""

import sounddevice as sd
import soundfile as sf
import numpy as np
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


class AudioRecorder:
    """Records audio from microphone using SoundDevice"""
    
    def __init__(self):
        self.frames = []
        self.is_recording = False
        self.sample_rate = VoiceConfig.SAMPLE_RATE
        
    def record_audio(self, duration: int = 10) -> np.ndarray:
        """
        Record audio for specified duration
        
        Args:
            duration: Recording duration in seconds
            
        Returns:
            Numpy array of audio data
        """
        print(f"🎤 Recording for {duration} seconds... Speak now!")
        
        recording = sd.rec(
            int(duration * self.sample_rate),
            samplerate=self.sample_rate,
            channels=VoiceConfig.CHANNELS,
            dtype=VoiceConfig.DTYPE
        )
        
        sd.wait()  # Wait until recording is finished
        
        print("✓ Recording complete!")
        return recording
    
    def record_until_silence(self, silence_threshold: float = 0.02, 
                            silence_duration: float = 2.0) -> np.ndarray:
        """
        Record audio until silence is detected
        
        Args:
            silence_threshold: Amplitude threshold for silence
            silence_duration: Duration of silence to stop recording
            
        Returns:
            Numpy array of audio data
        """
        print("🎤 Recording... (will stop after silence)")
        
        self.frames = []
        self.is_recording = True
        silence_counter = 0
        
        def callback(indata, frames, time, status):
            """Called for each audio block"""
            if status:
                print(f"Status: {status}")
            
            self.frames.append(indata.copy())
            
            # Check for silence
            volume = np.abs(indata).mean()
            if volume < silence_threshold:
                silence_counter += frames / self.sample_rate
            else:
                silence_counter = 0
        
        # Start recording stream
        with sd.InputStream(
            samplerate=self.sample_rate,
            channels=VoiceConfig.CHANNELS,
            dtype=VoiceConfig.DTYPE,
            callback=callback
        ):
            print("Speak now... (Press Ctrl+C to stop manually)")
            try:
                while self.is_recording:
                    sd.sleep(100)
                    if silence_counter >= silence_duration:
                        break
            except KeyboardInterrupt:
                print("\n✓ Recording stopped manually")
        
        print("✓ Recording complete!")
        
        if self.frames:
            return np.concatenate(self.frames, axis=0)
        return np.array([])
    
    def save_to_wav(self, audio_data: np.ndarray, filename: str = "recording.wav"):
        """
        Save audio data to WAV file
        
        Args:
            audio_data: Numpy array of audio data
            filename: Output filename
        """
        sf.write(filename, audio_data, self.sample_rate)
        print(f"✓ Audio saved to {filename}")
    
    def get_wav_bytes(self, audio_data: np.ndarray) -> bytes:
        """
        Convert audio data to WAV format bytes
        
        Args:
            audio_data: Numpy array of audio data
            
        Returns:
            WAV format bytes
        """
        # Create in-memory WAV file
        wav_buffer = io.BytesIO()
        
        with wave.open(wav_buffer, 'wb') as wav_file:
            wav_file.setnchannels(VoiceConfig.CHANNELS)
            wav_file.setsampwidth(2)  # 16-bit
            wav_file.setframerate(self.sample_rate)
            wav_file.writeframes(audio_data.tobytes())
        
        return wav_buffer.getvalue()


class AudioPlayer:
    """Plays audio files using SoundDevice"""
    
    def __init__(self):
        pass
        
    def play_audio(self, filename: str):
        """
        Play audio file
        
        Args:
            filename: Path to audio file
        """
        try:
            print(f"🔊 Playing {filename}...")
            
            # Read audio file
            data, sample_rate = sf.read(filename)
            
            # Play audio
            sd.play(data, sample_rate)
            sd.wait()  # Wait until playback is finished
            
            print("✓ Playback complete")
            
        except Exception as e:
            print(f"Playback error: {e}")
    
    def play_from_bytes(self, audio_bytes: bytes):
        """
        Play audio from bytes
        
        Args:
            audio_bytes: Audio data in bytes
        """
        try:
            # Read from bytes
            buffer = io.BytesIO(audio_bytes)
            data, sample_rate = sf.read(buffer)
            
            # Play audio
            sd.play(data, sample_rate)
            sd.wait()
            
        except Exception as e:
            print(f"Playback error: {e}")


class VoicePipeline:
    """Complete voice pipeline using SoundDevice and Google Cloud"""
    
    def __init__(self, credentials_path: str):
        """
        Initialize voice pipeline
        
        Args:
            credentials_path: Path to Google Cloud credentials JSON
        """
        self.speech_service = GoogleSpeechService(credentials_path=credentials_path)
        self.recorder = AudioRecorder()
        self.player = AudioPlayer()
        
    def listen(self, duration: int = 10) -> Tuple[str, float]:
        """
        Record audio and convert to text
        
        Args:
            duration: Recording duration in seconds
            
        Returns:
            Tuple of (transcribed_text, confidence)
        """
        # Record audio
        audio_data = self.recorder.record_audio(duration)
        
        # Save to temporary file
        temp_file = "temp_recording.wav"
        self.recorder.save_to_wav(audio_data, temp_file)
        
        # Convert to WAV bytes for STT
        wav_bytes = self.recorder.get_wav_bytes(audio_data)
        
        # Convert to text
        text, confidence = self.speech_service.speech_to_text(wav_bytes)
        
        return text, confidence
    
    def speak(self, text: str, play: bool = True):
        """
        Convert text to speech and optionally play
        
        Args:
            text: Telugu text to speak
            play: Whether to play audio immediately
        """
        output_file = "response.wav"
        success = self.speech_service.text_to_speech(text, output_file)
        
        if success and play:
            self.player.play_audio(output_file)


# Example usage
if __name__ == "__main__":
    import os
    from dotenv import load_dotenv
    
    load_dotenv()
    
    print("=" * 80)
    print("Telugu Voice Pipeline with Google Cloud (Python 3.12 Compatible)")
    print("=" * 80)
    print()
    
    # Test available audio devices
    print("Available audio devices:")
    print(sd.query_devices())
    print()
    
    # Initialize pipeline
    pipeline = VoicePipeline(
        credentials_path=os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    )
    
    # Test TTS
    print("Testing Text-to-Speech...")
    pipeline.speak("నమస్కారం! ఇది సౌండ్‌డివైస్ తో పరీక్ష.", play=True)
    
    # Test STT (optional - comment out if no microphone)
    # print("\nTesting Speech-to-Text...")
    # print("Say something in Telugu:")
    # text, confidence = pipeline.listen(duration=5)
    # print(f"Recognized: {text} (confidence: {confidence:.2%})")
    
    print("\n✓ All tests complete!")