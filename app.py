"""
Production Flask Application for Telugu Government Scheme Voice Agent
Ready for Render/Railway/Heroku Deployment
"""

from flask import Flask, render_template, request, jsonify, send_file
from flask_cors import CORS
import os
import time
import json
import tempfile
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

# Configuration
CONFIG = {
    "gemini_api_key": os.getenv("GEMINI_API_KEY"),
    "google_credentials": None,
    "schemes_path": "schemes_database.json"
}


def setup_google_credentials():
    """
    Setup Google Cloud credentials from environment variable or file
    Works for both local development and cloud deployment
    """
    # First, try to get credentials from environment variable (for deployment)
    google_creds_json = os.getenv('GOOGLE_CREDENTIALS')
    
    if google_creds_json:
        print("📝 Using Google credentials from environment variable")
        try:
            # Parse JSON from environment variable
            creds_dict = json.loads(google_creds_json)
            
            # Create temporary file
            temp_creds = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json')
            json.dump(creds_dict, temp_creds)
            temp_creds.close()
            
            # Set environment variable to point to temp file
            os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = temp_creds.name
            return temp_creds.name
        except Exception as e:
            print(f"❌ Error parsing Google credentials from env: {e}")
            raise
    
    # Fallback to file path (for local development)
    creds_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "google-credentials.json")
    
    if os.path.exists(creds_path):
        print(f"📝 Using Google credentials from file: {creds_path}")
        return creds_path
    
    raise ValueError("Google credentials not found! Set GOOGLE_CREDENTIALS env var or provide google-credentials.json file")


def initialize():
    """Initialize all services"""
    global agent, voice_pipeline
    
    print("🚀 Initializing services...")
    
    # Check Gemini API key
    if not CONFIG["gemini_api_key"]:
        raise ValueError("GEMINI_API_KEY not found in environment variables")
    
    # Setup Google credentials
    try:
        CONFIG["google_credentials"] = setup_google_credentials()
    except Exception as e:
        print(f"❌ Google credentials setup failed: {e}")
        raise
    
    # Initialize agent
    print("🤖 Initializing agent...")
    agent = TeluguSchemeAgent(
        api_key=CONFIG["gemini_api_key"],
        schemes_path=CONFIG["schemes_path"]
    )
    
    # Initialize voice pipeline
    print("🎤 Initializing voice pipeline...")
    voice_pipeline = VoicePipeline(
        credentials_path=CONFIG["google_credentials"]
    )
    
    print("✅ All services initialized successfully")
    print(f"📊 Loaded {len(agent.database.schemes)} schemes")


@app.route('/')
def index():
    """Serve the main page"""
    return render_template('index.html')


@app.route('/api/start-session', methods=['POST'])
def start_session():
    """Start new conversation session"""
    try:
        session_id = datetime.now().strftime("%Y%m%d%H%M%S%f")
        
        active_sessions[session_id] = {
            "started_at": datetime.now().isoformat(),
            "turn_count": 0,
            "turns": []
        }
        
        # Reset agent for this session
        agent.reset()
        
        print(f"✅ New session started: {session_id}")
        
        return jsonify({
            "session_id": session_id,
            "status": "success"
        })
    
    except Exception as e:
        print(f"❌ Session start error: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/voice-input', methods=['POST'])
def voice_input():
    """Handle voice input from user"""
    try:
        if 'audio' not in request.files:
            return jsonify({"error": "No audio file"}), 400
        
        audio_file = request.files['audio']
        session_id = request.form.get('session_id')
        
        # Get or create session
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
            print(f"❌ STT error: {stt_error}")
            os.remove(temp_file)
            return jsonify({"error": "Speech recognition failed"}), 400
        
        # Clean up temp file
        os.remove(temp_file)
        
        print(f"🎤 [{session_id}] Turn {turn}: User said: {text}")
        
        # Process with agent
        response_text, metadata = agent.process_input(text)
        
        print(f"🤖 [{session_id}] Turn {turn}: Agent responds: {response_text[:100]}...")
        
        # Clean for TTS
        clean_response = clean_text_for_tts(response_text)
        
        # Generate unique audio filename
        timestamp = int(time.time() * 1000)
        audio_file = f"response_{session_id}_{turn}_{timestamp}.wav"
        
        # Text-to-speech
        tts_success = voice_pipeline.speech_service.text_to_speech(
            clean_response, audio_file
        )
        
        if not tts_success:
            print(f"⚠️ TTS failed for turn {turn}")
        
        # Save turn to session
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
        print(f"❌ Voice input error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@app.route('/api/text-input', methods=['POST'])
def text_input():
    """Handle text input from user"""
    try:
        data = request.get_json()
        text = data.get('text', '').strip()
        session_id = data.get('session_id')
        
        if not text:
            return jsonify({"error": "No text provided"}), 400
        
        # Get or create session
        session = active_sessions.get(session_id, {})
        session["turn_count"] = session.get("turn_count", 0) + 1
        turn = session["turn_count"]
        
        print(f"💬 [{session_id}] Turn {turn}: User typed: {text}")
        
        # Process with agent
        response_text, metadata = agent.process_input(text)
        
        print(f"🤖 [{session_id}] Turn {turn}: Agent responds: {response_text[:100]}...")
        
        # Clean for TTS
        clean_response = clean_text_for_tts(response_text)
        
        # Generate unique audio filename
        timestamp = int(time.time() * 1000)
        audio_file = f"response_{session_id}_{turn}_{timestamp}.wav"
        
        # Text-to-speech
        tts_success = voice_pipeline.speech_service.text_to_speech(
            clean_response, audio_file
        )
        
        if not tts_success:
            print(f"⚠️ TTS failed for turn {turn}")
        
        # Save turn to session
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
        print(f"❌ Text input error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@app.route('/api/audio/<session_id>/<int:turn>/<int:timestamp>')
def get_audio(session_id, turn, timestamp):
    """Serve generated audio file"""
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
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "agent": agent is not None,
        "voice": voice_pipeline is not None,
        "schemes": len(agent.database.schemes) if agent else 0,
        "active_sessions": len(active_sessions),
        "environment": os.getenv("ENVIRONMENT", "development")
    })


def cleanup_old_files():
    """Clean up old audio files (older than 1 hour)"""
    import glob
    current_time = time.time()
    
    for pattern in ["response_*.wav", "temp_audio_*.webm"]:
        for file in glob.glob(pattern):
            try:
                age = current_time - os.path.getmtime(file)
                if age > 3600:  # 1 hour
                    os.remove(file)
                    print(f"🧹 Cleaned: {file}")
            except Exception as e:
                print(f"⚠️ Cleanup error for {file}: {e}")


# Initialize on startup
try:
    print("=" * 80)
    print("🇮🇳 Telugu Government Scheme Voice Agent - Production")
    print("=" * 80)
    
    initialize()
    cleanup_old_files()
    
    print("\n✅ Server Ready!")
    print(f"✅ Environment: {os.getenv('ENVIRONMENT', 'development')}")
    print(f"✅ Loaded {len(agent.database.schemes)} schemes")
    print("=" * 80)
    
except Exception as e:
    print(f"\n❌ Initialization failed: {e}")
    print("\n📋 Checklist:")
    print("1. GEMINI_API_KEY environment variable set")
    print("2. GOOGLE_CREDENTIALS environment variable or google-credentials.json file")
    print("3. schemes_database.json exists")
    import traceback
    traceback.print_exc()
    exit(1)


if __name__ == '__main__':
    # Get port from environment (required for cloud deployment)
    port = int(os.environ.get('PORT', 5000))
    
    # Run server
    # debug=False for production, host='0.0.0.0' to accept external connections
    app.run(
        debug=os.getenv('DEBUG', 'False').lower() == 'true',
        host='0.0.0.0',
        port=port
    )