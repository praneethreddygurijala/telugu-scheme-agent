# Telugu Government Scheme Voice Assistant 🎤

A professional voice-enabled AI assistant that helps Telugu-speaking citizens discover government schemes they're eligible for through natural conversation in Telugu.

## 🌟 Features

- **Bilingual Voice Interface**: Speak in Telugu and get responses in Telugu
- **Smart Eligibility Matching**: Finds schemes based on age, occupation, income, and location
- **Natural Conversations**: Uses Google Gemini 2.0 Flash for context-aware dialogue
- **Zero Hallucination**: Only presents schemes from verified database
- **Multi-Input Support**: Voice recording or text input
- **Real-time TTS Responses**: Instant audio feedback in Telugu
- **Session Management**: Maintains conversation context throughout interaction

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Web Frontend                              │
│         (HTML/CSS/JS with Telugu UI)                        │
└──────────────────────────┬──────────────────────────────────┘
                           │
                      ┌────▼────┐
                      │  Flask  │
                      │   API   │
                      └────┬────┘
                           │
        ┌──────────────────┼──────────────────┐
        │                  │                  │
   ┌────▼─────┐      ┌────▼────┐      ┌─────▼──────┐
   │  Voice   │      │  Agent  │      │  Schemes   │
   │ Pipeline │      │  Engine │──────│  Database  │
   └────┬─────┘      └────┬────┘      │   (JSON)   │
        │                 │            └────────────┘
        │                 │                   ▲
        │            ┌────▼────┐              │
        │            │ Context │              │
        │            │ Manager │              │
        │            └────┬────┘              │
        │                 │                   │
        │            ┌────▼─────────┐         │
        │            │ Eligibility  │─────────┘
        │            │   Matcher    │  (Reads & Filters)
        │            └──────────────┘
        │
   ┌────▼──────────────────────┐
   │    Google Cloud APIs      │
   │  - Speech-to-Text (STT)   │
   │  - Text-to-Speech (TTS)   │
   └───────────────────────────┘
             │
        ┌────▼──────────────┐
        │  Gemini 2.0 Flash │
        │  (Response Gen)   │
        │  - Takes scheme   │
        │    data as input  │
        │  - Generates      │
        │    natural Telugu │
        └───────────────────┘
```

### Data Flow:

1. **User Input** → Voice/Text to Frontend
2. **Frontend** → Sends to Flask API
3. **Agent Engine** → Extracts user information (age, occupation, state, etc.)
4. **Eligibility Matcher** → Queries JSON database with user profile
5. **Database** → Returns only matching schemes (strict filtering)
6. **Gemini** → Takes filtered schemes + context, generates natural Telugu response
7. **Voice Pipeline** → Converts response to speech
8. **Frontend** → Plays audio and displays text

**Key Point**: Gemini NEVER generates scheme information. It only:
- Helps extract user information from natural language
- Generates conversational responses using pre-filtered database schemes
- Ensures zero hallucination by working with verified data only

## 📋 Prerequisites

- **Python 3.12+**
- **Google Cloud Account** with:
  - Speech-to-Text API enabled
  - Text-to-Speech API enabled
  - Service account with credentials
- **Google Gemini API Key**

## 🚀 Installation

### 1. Clone Repository

```bash
git clone https://github.com/yourusername/telugu-scheme-assistant.git
cd telugu-scheme-assistant
```

### 2. Create Virtual Environment

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Set Up Credentials

Create a `.env` file in the project root:

```env
GEMINI_API_KEY=your_gemini_api_key_here
GOOGLE_APPLICATION_CREDENTIALS=google-credentials.json
```

Place your Google Cloud service account JSON file as `google-credentials.json` in the project root.

### 5. Verify Scheme Database

Ensure `schemes_database.json` exists with government scheme data.

## 💻 Usage

### Start the Server

```bash
python app.py
```

The application will start at `http://localhost:5000`

### API Endpoints

#### Start Session
```http
POST /api/start-session
Response: { "session_id": "string", "status": "success" }
```

#### Voice Input
```http
POST /api/voice-input
Content-Type: multipart/form-data
Body: { audio: File, session_id: string }
Response: { status, user_text, agent_response, audio_url, metadata }
```

#### Text Input
```http
POST /api/text-input
Content-Type: application/json
Body: { text: string, session_id: string }
Response: { status, agent_response, audio_url, metadata }
```

#### Get Audio
```http
GET /api/audio/<session_id>/<turn>/<timestamp>
Response: audio/wav file
```

#### Health Check
```http
GET /health
Response: { status, agent, voice, schemes, active_sessions }
```

## 🧠 Agent States

The conversational agent follows a state machine:

1. **GREETING** - Initial welcome
2. **COLLECTING_BASIC_INFO** - Gather age, state
3. **COLLECTING_ADDITIONAL_INFO** - Gather occupation, income
4. **MATCHING_SCHEMES** - Find eligible schemes
5. **PRESENTING_SCHEMES** - Show top 3 matches
6. **ANSWERING_QUESTIONS** - Handle scheme queries
7. **PROVIDING_APPLICATION_DETAILS** - Guide through application process

## 📊 Scheme Database Structure

```json
{
  "id": "EDU001",
  "name_telugu": "పోస్ట్ మ్యాట్రిక్ స్కాలర్‌షిప్",
  "name_english": "Post-Matric Scholarship",
  "category": "education",
  "scheme_type": "state",
  "state": "Telangana",
  "description_telugu": "...",
  "benefits": "సంవత్సరానికి ₹15,000 నుండి ₹50,000 వరకు",
  "eligibility": {
    "age_min": 14,
    "age_max": 25,
    "occupation": ["student"],
    "income_max": 200000,
    "state": "Telangana"
  },
  "application_process": {
    "steps_telugu": [...],
    "online_url": "...",
    "offline_location": "..."
  }
}
```

## 🔧 Configuration

### Audio Settings (voice_pipeline.py)
```python
SAMPLE_RATE = 16000
CHANNELS = 1
DTYPE = 'int16'
TELUGU_GOOGLE = "te-IN"
GOOGLE_VOICE = "te-IN-Standard-A"
```

### Gemini Settings (agent_gemini.py)
```python
model_name = "gemini-2.0-flash-exp"
temperature = 0.6
top_p = 0.9
max_output_tokens = 150
```

## 📁 Project Structure

```
telugu-scheme-assistant/
├── app.py                    # Flask application
├── agent_gemini.py           # Conversational agent with Gemini
├── voice_pipeline.py         # Speech-to-Text and Text-to-Speech
├── schemes_database.json     # Government schemes data
├── requirements.txt          # Python dependencies
├── .env                      # Environment variables
├── google-credentials.json   # Google Cloud credentials
├── templates/
│   └── index.html           # Web interface
└── README.md 
└── architecture.md
└── Evaluation transcript.md              
```

## 🎯 Key Features Explained

### How the System Prevents Hallucination

**Critical Design Choice**: The system uses a **Database-First approach** with Gemini as a response formatter only.

**Workflow**:
1. User provides information (age: 20, occupation: student, state: Telangana)
2. **Agent extracts** structured data using regex and keyword matching
3. **Eligibility Matcher** queries `schemes_database.json` with strict filters
4. Database returns **only verified schemes** that match criteria (e.g., Post-Matric Scholarship)
5. **Gemini receives**: Pre-filtered scheme data + user context
6. **Gemini generates**: Natural Telugu explanation of those specific schemes
7. User hears/sees: Accurate information about real government schemes

**What Gemini Does**:
- ✅ Converts scheme data into conversational Telugu
- ✅ Asks clarifying questions based on conversation state
- ✅ Explains application processes in simple language

**What Gemini NEVER Does**:
- ❌ Invents or suggests schemes not in database
- ❌ Makes up eligibility criteria
- ❌ Creates fake benefit amounts
- ❌ Generates application URLs

### Eligibility Matching Algorithm

The agent uses **strict matching** with scoring:
- Age constraints: MUST match (25 points each for min/max)
- State requirement: MUST match (25 points)
- Occupation: MUST match if specified (25 points)
- Income: Evaluated if provided (15 points)
- Gender: MUST match if specified (10 points)

Schemes need **≥75% score** to be eligible.

**Example**:
```python
User: { age: 20, state: "Telangana", occupation: "student" }
Database has: 11 total schemes
After matching: 3 eligible schemes (Post-Matric, National Means, Sukanya)
Gemini formats: "మీకు ఈ పథకాలు సరిపోతాయి: 1. పోస్ట్ మ్యాట్రిక్..."
```

### Context Management

- Tracks user profile (age, state, occupation, income, gender)
- Maintains conversation history
- Remembers which questions were already asked
- Focuses on currently discussed scheme

### Response Generation

Uses Google Gemini 2.0 Flash to generate:
- Natural Telugu responses **based on provided scheme data**
- Contextually appropriate questions
- Scheme explanations in simple language
- Application process guidance **from database steps**

All responses are:
- Maximum 3-4 sentences
- No formal titles (తాతయ్య/అమ్మ)
- Conversational and friendly
- Cleaned for TTS (no English, emojis, or markdown)

## 🔒 Security Notes

- Never commit `.env` or `google-credentials.json`
- Add them to `.gitignore`
- Rotate API keys regularly
- Use environment-specific credentials

## 🐛 Troubleshooting

### Audio Not Working
- Check microphone permissions
- Verify audio device: `python -c "import sounddevice as sd; print(sd.query_devices())"`
- Ensure correct sample rate (16000 Hz)

### STT/TTS Errors
- Verify Google Cloud credentials path
- Check API quotas in Google Cloud Console
- Ensure Speech APIs are enabled

### No Schemes Found
- Check user profile values in logs
- Verify scheme eligibility criteria
- Review database matching logic

### Session Issues
- Clear browser cache
- Start new session
- Check server logs for errors

## 📈 Performance

- Average response time: 2-3 seconds
- STT accuracy: ~95% for clear Telugu speech
- TTS quality: Native Telugu voice (te-IN-Standard-A)
- Concurrent sessions: Supports multiple users

## 🙏 Acknowledgments

- Google Cloud for Speech APIs
- Google Gemini for conversational AI
- Telangana and Andhra Pradesh governments for scheme data
- SoundDevice library for Python 3.12 audio support



