"""
Production Flask Application for Telugu Government Scheme Voice Agent
Professional, reliable, zero-hallucination
"""

from flask import Flask, render_template, request, jsonify, send_file
from flask_cors import CORS
import os
import time
from datetime import datetime
from dotenv import load_dotenv
from agent_gemini import TeluguSchemeAgent, clean_text_for_tts
from voice_pipeline import VoicePipeline

load_dotenv()

app = Flask(__name__)
CORS(app)

# Global services
agent = None
voice_pipeline = None
active_sessions = {}

CONFIG = {
    "gemini_api_key": os.getenv("GEMINI_API_KEY"),
    "google_credentials": os.getenv("GOOGLE_APPLICATION_CREDENTIALS"),
    "schemes_path": "schemes_database.json"
}


def initialize():
    """Initialize all services"""
    global agent, voice_pipeline
    
    if not CONFIG["gemini_api_key"]:
        raise ValueError("GEMINI_API_KEY not found")
    
    if not CONFIG["google_credentials"]:
        raise ValueError("GOOGLE_APPLICATION_CREDENTIALS not found")
    
    print("Initializing services...")
    
    # Initialize agent
    agent = TeluguSchemeAgent(
        api_key=CONFIG["gemini_api_key"],
        schemes_path=CONFIG["schemes_path"]
    )
    
    # Initialize voice
    voice_pipeline = VoicePipeline(
        credentials_path=CONFIG["google_credentials"]
    )
    
    print("✓ Services ready")


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/api/start-session', methods=['POST'])
def start_session():
    """Start new session"""
    try:
        session_id = datetime.now().strftime("%Y%m%d%H%M%S%f")
        
        active_sessions[session_id] = {
            "started_at": datetime.now().isoformat(),
            "turn_count": 0,
            "turns": []
        }
        
        # Reset agent for this session
        agent.reset()
        
        return jsonify({
            "session_id": session_id,
            "status": "success"
        })
    
    except Exception as e:
        print(f"Session start error: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/voice-input', methods=['POST'])
def voice_input():
    """Handle voice input"""
    try:
        if 'audio' not in request.files:
            return jsonify({"error": "No audio file"}), 400
        
        audio_file = request.files['audio']
        session_id = request.form.get('session_id')
        
        # Get session
        session = active_sessions.get(session_id, {})
        session["turn_count"] = session.get("turn_count", 0) + 1
        turn = session["turn_count"]
        
        # Save audio temporarily
        temp_file = f"temp_audio_{session_id}_{turn}.webm"
        audio_file.save(temp_file)
        
        # Speech-to-text
        from google.cloud import speech_v1p1beta1 as speech
        
        with open(temp_file, 'rb') as f:
            audio_bytes = f.read()
        
        audio = speech.RecognitionAudio(content=audio_bytes)
        config = speech.RecognitionConfig(
            encoding=speech.RecognitionConfig.AudioEncoding.WEBM_OPUS,
            language_code="te-IN",
            enable_automatic_punctuation=True,
            model="default",
            use_enhanced=True
        )
        
        try:
            response = voice_pipeline.speech_service.stt_client.recognize(
                config=config, audio=audio
            )
            
            if response.results:
                text = response.results[0].alternatives[0].transcript
                confidence = response.results[0].alternatives[0].confidence
            else:
                os.remove(temp_file)
                return jsonify({"error": "Could not understand speech"}), 400
        
        except Exception as stt_error:
            print(f"STT error: {stt_error}")
            os.remove(temp_file)
            return jsonify({"error": "Speech recognition failed"}), 400
        
        os.remove(temp_file)
        
        print(f"[{session_id}] Turn {turn}: User said: {text}")
        
        # Process with agent
        response_text, metadata = agent.process_input(text)
        
        print(f"[{session_id}] Turn {turn}: Agent responds: {response_text}")
        
        # Clean for TTS
        clean_response = clean_text_for_tts(response_text)
        
        # Generate unique audio
        timestamp = int(time.time() * 1000)
        audio_file = f"response_{session_id}_{turn}_{timestamp}.wav"
        
        tts_success = voice_pipeline.speech_service.text_to_speech(
            clean_response, audio_file
        )
        
        if not tts_success:
            print(f"TTS failed for turn {turn}")
        
        # Save turn
        if session_id in active_sessions:
            active_sessions[session_id]["turns"].append({
                "turn": turn,
                "user_text": text,
                "confidence": float(confidence),
                "agent_response": response_text,
                "state": metadata["state"],
                "audio_file": audio_file,
                "timestamp": datetime.now().isoformat()
            })
        
        return jsonify({
            "status": "success",
            "user_text": text,
            "confidence": float(confidence),
            "agent_response": response_text,
            "audio_url": f"/api/audio/{session_id}/{turn}/{timestamp}",
            "turn_number": turn,
            "metadata": {
                "state": metadata["state"],
                "has_basic_info": metadata["has_basic_info"],
                "has_sufficient_info": metadata["has_sufficient_info"]
            }
        })
    
    except Exception as e:
        print(f"Voice input error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@app.route('/api/text-input', methods=['POST'])
def text_input():
    """Handle text input"""
    try:
        data = request.get_json()
        text = data.get('text', '').strip()
        session_id = data.get('session_id')
        
        if not text:
            return jsonify({"error": "No text provided"}), 400
        
        # Get session
        session = active_sessions.get(session_id, {})
        session["turn_count"] = session.get("turn_count", 0) + 1
        turn = session["turn_count"]
        
        print(f"[{session_id}] Turn {turn}: User typed: {text}")
        
        # Process with agent
        response_text, metadata = agent.process_input(text)
        
        print(f"[{session_id}] Turn {turn}: Agent responds: {response_text}")
        
        # Clean for TTS
        clean_response = clean_text_for_tts(response_text)
        
        # Generate unique audio
        timestamp = int(time.time() * 1000)
        audio_file = f"response_{session_id}_{turn}_{timestamp}.wav"
        
        tts_success = voice_pipeline.speech_service.text_to_speech(
            clean_response, audio_file
        )
        
        if not tts_success:
            print(f"TTS failed for turn {turn}")
        
        # Save turn
        if session_id in active_sessions:
            active_sessions[session_id]["turns"].append({
                "turn": turn,
                "user_text": text,
                "agent_response": response_text,
                "state": metadata["state"],
                "audio_file": audio_file,
                "timestamp": datetime.now().isoformat()
            })
        
        return jsonify({
            "status": "success",
            "agent_response": response_text,
            "audio_url": f"/api/audio/{session_id}/{turn}/{timestamp}",
            "turn_number": turn,
            "metadata": {
                "state": metadata["state"],
                "has_basic_info": metadata["has_basic_info"],
                "has_sufficient_info": metadata["has_sufficient_info"]
            }
        })
    
    except Exception as e:
        print(f"Text input error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@app.route('/api/audio/<session_id>/<int:turn>/<int:timestamp>')
def get_audio(session_id, turn, timestamp):
    """Serve audio file"""
    audio_path = f"response_{session_id}_{turn}_{timestamp}.wav"
    
    if os.path.exists(audio_path):
        response = send_file(audio_path, mimetype='audio/wav')
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
        return response
    else:
        return jsonify({"error": "Audio not found"}), 404


@app.route('/health')
def health():
    """Health check"""
    return jsonify({
        "status": "healthy",
        "agent": agent is not None,
        "voice": voice_pipeline is not None,
        "schemes": len(agent.database.schemes) if agent else 0,
        "active_sessions": len(active_sessions)
    })


def cleanup_old_files():
    """Clean up old audio files"""
    import glob
    current_time = time.time()
    
    for pattern in ["response_*.wav", "temp_audio_*.webm"]:
        for file in glob.glob(pattern):
            try:
                age = current_time - os.path.getmtime(file)
                if age > 3600:  # 1 hour
                    os.remove(file)
                    print(f"Cleaned: {file}")
            except Exception as e:
                print(f"Cleanup error for {file}: {e}")


if __name__ == '__main__':
    print("=" * 80)
    print("Telugu Government Scheme Voice Agent - Production Version")
    print("=" * 80)
    
    try:
        initialize()
        cleanup_old_files()
        
        print("\n✓ Ready!")
        print("✓ Professional agent with proper conversation flow")
        print("✓ Zero hallucination - only database schemes")
        print("✓ Natural language understanding")
        print(f"✓ Loaded {len(agent.database.schemes)} verified schemes")
        print("\nStarting server on http://localhost:5000")
        print("=" * 80)
        
        app.run(debug=True, host='0.0.0.0', port=5000)
    
    except Exception as e:
        print(f"\n✗ Initialization failed: {e}")
        print("\nChecklist:")
        print("1. .env file with GEMINI_API_KEY and GOOGLE_APPLICATION_CREDENTIALS")
        print("2. google-credentials.json exists")
        print("3. schemes_database.json exists")
        import traceback
        traceback.print_exc()