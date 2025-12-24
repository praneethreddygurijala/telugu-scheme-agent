"""
Professional Telugu Government Scheme Agent
COMPLETE WORKING VERSION - Production Ready
"""

import json
import re
import google.generativeai as genai
from typing import Dict, List, Optional, Tuple
from enum import Enum
from datetime import datetime


class AgentState(Enum):
    """Conversation states"""
    GREETING = "greeting"
    COLLECTING_BASIC_INFO = "collecting_basic_info"
    COLLECTING_ADDITIONAL_INFO = "collecting_additional_info"
    MATCHING_SCHEMES = "matching_schemes"
    PRESENTING_SCHEMES = "presenting_schemes"
    ANSWERING_QUESTIONS = "answering_questions"
    PROVIDING_APPLICATION_DETAILS = "providing_application_details"


class ConversationContext:
    """Manages conversation state and collected information"""
    
    def __init__(self):
        # User profile
        self.profile = {
            "age": None,
            "state": None,
            "occupation": None,
            "income": None,
            "gender": None,
            "has_land": None,
            "has_children": None,
        }
        
        # Conversation tracking
        self.conversation_history = []
        self.asked_questions = set()
        self.confirmed_schemes = []
        self.current_scheme_focus = None
        
        # Required info
        self.required_basic = {"age", "state"}
        self.required_additional = {"occupation"}
        
    def add_turn(self, role: str, content: str):
        """Add conversation turn"""
        self.conversation_history.append({
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat()
        })
    
    def update_profile(self, key: str, value):
        """Update user profile"""
        if key in self.profile:
            old_value = self.profile[key]
            self.profile[key] = value
            
            if old_value and old_value != value:
                print(f"INFO: {key} updated from {old_value} to {value}")
    
    def has_basic_info(self) -> bool:
        """Check if we have minimum required info"""
        return all(self.profile.get(field) is not None for field in self.required_basic)
    
    def has_sufficient_info(self) -> bool:
        """Check if we have enough info for good matching"""
        basic = self.has_basic_info()
        additional = self.profile.get("occupation") is not None
        return basic and additional
    
    def get_missing_basic_info(self) -> List[str]:
        """Get list of missing required fields"""
        return [field for field in self.required_basic 
                if self.profile.get(field) is None]
    
    def mark_question_asked(self, field: str):
        """Mark that we asked about this field"""
        self.asked_questions.add(field)
    
    def already_asked(self, field: str) -> bool:
        """Check if already asked"""
        return field in self.asked_questions
    
    def needs_gender_info(self, schemes: List[Dict]) -> bool:
        """Check if any eligible scheme needs gender"""
        if self.profile.get("gender"):
            return False
        
        for scheme_item in schemes:
            if scheme_item["scheme"]["eligibility"].get("gender"):
                return True
        return False


class SchemeDatabase:
    """Manages government schemes database"""
    
    def __init__(self, schemes_path: str):
        with open(schemes_path, 'r', encoding='utf-8') as f:
            self.data = json.load(f)
        
        self.schemes = self.data["schemes"]
        print(f"Loaded {len(self.schemes)} schemes from database")
    
    def find_eligible_schemes(self, profile: Dict) -> List[Dict]:
        """Find schemes user is eligible for"""
        eligible = []
        
        for scheme in self.schemes:
            score, reasons = self._calculate_eligibility(scheme, profile)
            
            if score >= 75:
                eligible.append({
                    "scheme": scheme,
                    "eligibility_score": score,
                    "match_reasons": reasons
                })
        
        eligible.sort(key=lambda x: x["eligibility_score"], reverse=True)
        return eligible
    
    def _calculate_eligibility(self, scheme: Dict, profile: Dict) -> Tuple[int, List[str]]:
        """Calculate eligibility score - STRICT matching"""
        eligibility = scheme["eligibility"]
        score = 0
        max_score = 0
        reasons = []
        
        # CRITICAL: Age check - both min and max must match
        if profile.get("age"):
            if eligibility.get("age_min") is not None:
                max_score += 25
                if profile["age"] >= eligibility["age_min"]:
                    score += 25
                else:
                    return 0, ["వయస్సు తక్కువ"]
            
            if eligibility.get("age_max") is not None:
                max_score += 25
                if profile["age"] <= eligibility["age_max"]:
                    score += 25
                    reasons.append("వయస్సు అర్హత సరిపోతుంది")
                else:
                    return 0, ["వయస్సు మించింది"]
        
        # State check - MUST match
        if eligibility.get("state"):
            max_score += 25
            if profile.get("state"):
                user_state = profile["state"].lower()
                scheme_state = eligibility["state"].lower()
                
                if scheme_state == "all india" or user_state in scheme_state:
                    score += 25
                    reasons.append("రాష్ట్ర అర్హత సరిపోతుంది")
                else:
                    return 0, ["రాష్ట్రం సరిపోలేదు"]
        
        # Occupation check - MUST match if specified
        if eligibility.get("occupation") and eligibility["occupation"]:
            max_score += 25
            if profile.get("occupation"):
                user_occ = profile["occupation"].lower()
                scheme_occs = [o.lower() for o in eligibility["occupation"]]
                
                if user_occ in scheme_occs:
                    score += 25
                    reasons.append("వృత్తి అర్హత సరిపోతుంది")
                else:
                    return 0, ["వృత్తి సరిపోలేదు"]
            else:
                return 0, ["వృత్తి సమాచారం కావాలి"]
        
        # Gender check if specified
        if eligibility.get("gender"):
            max_score += 10
            if profile.get("gender"):
                if profile["gender"].lower() == eligibility["gender"].lower():
                    score += 10
                else:
                    return 0, ["లింగం సరిపోలేదు"]
        
        # Income check
        if eligibility.get("income_max"):
            max_score += 15
            if profile.get("income"):
                if profile["income"] <= eligibility["income_max"]:
                    score += 15
                    reasons.append("ఆదాయం పరిమితిలో ఉంది")
        
        if max_score > 0:
            return int((score / max_score) * 100), reasons
        return 0, []


class ResponseGenerator:
    """Generates natural Telugu responses using Gemini"""
    
    def __init__(self, api_key: str):
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(
            model_name="gemini-2.0-flash-exp",
            generation_config={
                "temperature": 0.6,
                "top_p": 0.9,
                "max_output_tokens": 150,
            }
        )
    
    def generate_response(self, context: str, task: str, user_input: str) -> str:
        """Generate appropriate response"""
        
        prompt = f"""You are a helpful Telugu government scheme assistant.

CONTEXT:
{context}

TASK:
{task}

USER INPUT: "{user_input}"

CRITICAL RULES:
1. Respond ONLY in Telugu (తెలుగులో మాత్రమే)
2. Be natural and conversational - like talking to a friend
3. NEVER use titles like తాతయ్య/అమ్మ/చిన్నారి - just be respectful without titles
4. Keep responses SHORT - maximum 3-4 sentences
5. Be direct and helpful
6. Don't copy-paste from data - explain naturally in your own words
7. For application process, be clear and action-oriented
8. Don't spell out English URLs - just mention they exist

Generate response (Telugu only, max 4 sentences):"""

        try:
            response = self.model.generate_content(prompt)
            text = response.text.strip()
            
            # Clean up
            text = re.sub(r'\*+', '', text)
            text = re.sub(r'#', '', text)
            text = text.strip()
            
            # Proper spacing
            text = re.sub(r'([.!?])\s*', r'\1 ', text)
            text = re.sub(r'\s+', ' ', text)
            
            return text
            
        except Exception as e:
            print(f"Gemini error: {e}")
            return "క్షమించండి, సమస్య వచ్చింది. మళ్లీ ప్రయత్నించండి."


class TeluguSchemeAgent:
    """Main agent orchestrator"""
    
    def __init__(self, api_key: str, schemes_path: str):
        self.context = ConversationContext()
        self.database = SchemeDatabase(schemes_path)
        self.generator = ResponseGenerator(api_key)
        self.state = AgentState.GREETING
        
        self.info_extractors = {
            "age": self._extract_age,
            "state": self._extract_state,
            "occupation": self._extract_occupation,
            "income": self._extract_income,
            "gender": self._extract_gender,
        }
    
    def process_input(self, user_input: str) -> Tuple[str, Dict]:
        """Main processing method"""
        
        # Add to history
        self.context.add_turn("user", user_input)
        
        # Extract information FIRST
        self._extract_all_info(user_input)
        
        # Determine next action based on state
        response = self._process_state(user_input)
        
        # Add response to history
        self.context.add_turn("assistant", response)
        
        # Build metadata
        metadata = {
            "state": self.state.value,
            "profile": self.context.profile,
            "has_basic_info": self.context.has_basic_info(),
            "has_sufficient_info": self.context.has_sufficient_info()
        }
        
        return response, metadata
    
    def _process_state(self, user_input: str) -> str:
        """Process based on current state"""
        
        if self.state == AgentState.GREETING:
            return self._handle_greeting()
        
        elif self.state == AgentState.COLLECTING_BASIC_INFO:
            return self._handle_collecting_basic()
        
        elif self.state == AgentState.COLLECTING_ADDITIONAL_INFO:
            return self._handle_collecting_additional()
        
        elif self.state == AgentState.MATCHING_SCHEMES:
            return self._handle_matching()
        
        elif self.state == AgentState.PRESENTING_SCHEMES:
            return self._handle_presenting(user_input)
        
        elif self.state == AgentState.ANSWERING_QUESTIONS:
            return self._handle_questions(user_input)
        
        elif self.state == AgentState.PROVIDING_APPLICATION_DETAILS:
            return self._handle_application_details(user_input)
        
        else:
            return "క్షమించండి, నేను మీ ప్రశ్న అర్థం చేసుకోలేకపోయాను."
    
    def _handle_greeting(self) -> str:
        """Handle initial greeting"""
        self.state = AgentState.COLLECTING_BASIC_INFO
        return "నమస్కారం! మీకు అనుకూలమైన ప్రభుత్వ పథకాలను కనుగొనడంలో నేను సహాయం చేస్తాను. మీ వయస్సు ఎంత?"
    
    def _handle_collecting_basic(self) -> str:
        """Collect basic required info"""
        missing = self.context.get_missing_basic_info()
        
        if not missing:
            self.state = AgentState.COLLECTING_ADDITIONAL_INFO
            return self._handle_collecting_additional()
        
        field = missing[0]
        
        # Don't ask if already asked
        if self.context.already_asked(field):
            if len(missing) > 1:
                field = missing[1]
            else:
                self.state = AgentState.COLLECTING_ADDITIONAL_INFO
                return self._handle_collecting_additional()
        
        self.context.mark_question_asked(field)
        
        if field == "age":
            return "మీ వయస్సు ఎంత?"
        elif field == "state":
            return "మీరు ఏ రాష్ట్రానికి చెందినవారు? తెలంగాణ లేదా ఆంధ్రప్రదేశ్?"
        
        return "దయచేసి మీ సమాచారం అందించండి."
    
    def _handle_collecting_additional(self) -> str:
        """Collect additional info for better matching"""
        
        if not self.context.profile.get("occupation"):
            if not self.context.already_asked("occupation"):
                self.context.mark_question_asked("occupation")
                return "మీ వృత్తి ఏమిటి? రైతు, చేనేత, కూలీ, వ్యాపారి, విద్యార్థి?"
        
        # Have enough info
        self.state = AgentState.MATCHING_SCHEMES
        return self._handle_matching()
    
    def _handle_matching(self) -> str:
        """Match schemes and present"""
        
        if not self.context.has_basic_info():
            self.state = AgentState.COLLECTING_BASIC_INFO
            return self._handle_collecting_basic()
        
        # Find eligible schemes
        eligible = self.database.find_eligible_schemes(self.context.profile)
        
        # Debug logging
        print(f"DEBUG: User profile: {self.context.profile}")
        print(f"DEBUG: Found {len(eligible)} eligible schemes")
        for item in eligible[:5]:
            print(f"  - {item['scheme']['name_telugu']}: {item['eligibility_score']}%")
        
        if not eligible:
            # If no schemes found and student, give specific message
            if self.context.profile.get("occupation") == "student":
                return "క్షమించండి, మీ వయస్సు మరియు విద్యార్థి స్థితికి సరిపోయే పథకాలు ప్రస్తుతం డేటాబేస్‌లో లేవు. దయచేసి స్థానిక విద్యా శాఖ లేదా పాఠశాలలో విచారించండి."
            
            if not self.context.profile.get("occupation"):
                self.state = AgentState.COLLECTING_ADDITIONAL_INFO
                return "మీ వృత్తి గురించి చెప్పండి, మరింత మంచి పథకాలు కనుగొనేందుకు."
            
            return "క్షమించండి, ప్రస్తుతం మీకు సరిపోయే పథకాలు కనపడలేదు."
        
        # Present top schemes using Gemini
        self.state = AgentState.PRESENTING_SCHEMES
        self.context.confirmed_schemes = eligible[:3]
        
        # Build scheme info
        scheme_info = ""
        for i, item in enumerate(self.context.confirmed_schemes, 1):
            scheme = item["scheme"]
            scheme_info += f"{i}. {scheme['name_telugu']} - {scheme['benefits']}\n"
        
        context = f"""User Profile:
Age: {self.context.profile.get('age')}
State: {self.context.profile.get('state')}
Occupation: {self.context.profile.get('occupation')}

Eligible Schemes (verified matches):
{scheme_info}"""
        
        task = """Present these schemes to the user in natural Telugu:
- Start with "మీకు ఈ పథకాలు సరిపోతాయి:"
- List each scheme with bullet (•) and ONLY Telugu name + one-line benefit
- Keep it short and clear
- End by asking "ఏ పథకం గురించి తెలుసుకోవాలనుకుంటున్నారు?"
Maximum 5 sentences total."""
        
        return self.generator.generate_response(context, task, "show schemes")
    
    def _handle_presenting(self, user_input: str) -> str:
        """Handle questions about presented schemes"""
        
        user_lower = user_input.lower()
        
        # Check if user is asking about a DIFFERENT scheme
        for item in self.context.confirmed_schemes:
            scheme = item["scheme"]
            scheme_name_words = scheme["name_telugu"].split()
            
            if (scheme["name_telugu"].lower() in user_lower or 
                scheme["name_english"].lower() in user_lower or
                any(word.lower() in user_lower for word in scheme_name_words if len(word) > 2)):
                
                self.context.current_scheme_focus = scheme
                self.state = AgentState.ANSWERING_QUESTIONS
                
                context = f"""Scheme:
Name: {scheme['name_telugu']}
Description: {scheme['description_telugu']}
Benefits: {scheme['benefits']}
Category: {scheme['category']}"""
                
                task = """Explain this scheme naturally in Telugu:
- Start with scheme name
- Explain what it provides in 2 simple sentences
- Mention the main benefit with numbers
- End by asking "దరఖాస్తు ఎలా చేయాలో తెలుసుకోవాలా?"
Maximum 4 sentences."""
                
                return self.generator.generate_response(context, task, user_input)
        
        # Check if asking about application
        if any(word in user_lower for word in ['దరఖాస్తు', 'apply', 'ఎలా', 'how', 'process', 'చేయాలి']):
            self.state = AgentState.PROVIDING_APPLICATION_DETAILS
            return self._handle_application_details(user_input)
        
        # General question
        self.state = AgentState.ANSWERING_QUESTIONS
        return self._handle_questions(user_input)
    
    def _handle_questions(self, user_input: str) -> str:
        """Handle general questions"""
        
        user_lower = user_input.lower()
        
        # Check if user is asking about a DIFFERENT scheme
        if self.context.confirmed_schemes:
            for item in self.context.confirmed_schemes:
                scheme = item["scheme"]
                scheme_name_words = scheme["name_telugu"].split()
                
                if (scheme["name_telugu"].lower() in user_lower or 
                    scheme["name_english"].lower() in user_lower or
                    any(word.lower() in user_lower for word in scheme_name_words if len(word) > 2)):
                    
                    self.context.current_scheme_focus = scheme
                    
                    context = f"""Scheme:
Name: {scheme['name_telugu']}
Description: {scheme['description_telugu']}
Benefits: {scheme['benefits']}"""
                    
                    task = """Explain this scheme naturally:
- Start with scheme name
- What it provides in 2 sentences
- Main benefit with numbers
- Ask "దరఖాస్తు ఎలా చేయాలో తెలుసుకోవాలా?"
Max 4 sentences."""
                    
                    return self.generator.generate_response(context, task, user_input)
        
        # Check for application request
        if any(word in user_lower for word in ['దరఖాస్తు', 'apply', 'process', 'ఎలా', 'how', 'చేయాలి', 'yes', 'avunu', 'అవును', 'విస్తరంగా', 'vivaranga']):
            self.state = AgentState.PROVIDING_APPLICATION_DETAILS
            return self._handle_application_details(user_input)
        
        # Use LLM for general answer
        context = str(self.context.profile)
        
        if self.context.confirmed_schemes:
            scheme_list = "\n".join([
                f"- {item['scheme']['name_telugu']}: {item['scheme']['benefits']}"
                for item in self.context.confirmed_schemes
            ])
            context = f"User Profile: {context}\n\nEligible Schemes:\n{scheme_list}"
        
        task = "Answer the user's question helpfully in natural Telugu. Keep it short and clear. Maximum 3 sentences."
        
        return self.generator.generate_response(str(context), task, user_input)
    
    def _handle_application_details(self, user_input: str) -> str:
        """Provide application details"""
        
        user_lower = user_input.lower()
        
        # Check if user is asking about a DIFFERENT scheme now
        if self.context.confirmed_schemes:
            for item in self.context.confirmed_schemes:
                scheme = item["scheme"]
                scheme_name_words = scheme["name_telugu"].split()
                
                if (scheme["name_telugu"].lower() in user_lower or 
                    scheme["name_english"].lower() in user_lower or
                    any(word.lower() in user_lower for word in scheme_name_words if len(word) > 2)):
                    
                    self.context.current_scheme_focus = scheme
                    break
        
        scheme = self.context.current_scheme_focus
        
        if not scheme and self.context.confirmed_schemes:
            scheme = self.context.confirmed_schemes[0]["scheme"]
            self.context.current_scheme_focus = scheme
        
        if not scheme:
            return "దయచేసి ముందు ఏ పథకం కావాలో చెప్పండి."
        
        app_process = scheme.get("application_process", {})
        steps = app_process.get("steps_telugu", [])
        online_url = app_process.get("online_url", "")
        offline_loc = app_process.get("offline_location", "")
        
        if not steps:
            return f"{scheme['name_telugu']} దరఖాస్తు విధానం ప్రస్తుతం అందుబాటులో లేదు."
        
        # Provide clear, actionable steps
        response = f"**{scheme['name_telugu']} దరఖాస్తు చేయడం ఎలా:**\n\n"
        
        for i, step in enumerate(steps, 1):
            response += f"{i}. {step}\n"
        
        if online_url:
            response += f"\n🌐 **ఆన్‌లైన్:** వెబ్‌సైట్ లో కూడా చేయవచ్చు"
        
        if offline_loc:
            response += f"\n📍 **ఆఫ్‌లైన్:** {offline_loc} కి వెళ్ళండి"
        
        response += "\n\nఇంకా ఏదైనా సహాయం కావాలా?"
        
        # RESET state so it can handle new scheme requests
        self.state = AgentState.ANSWERING_QUESTIONS
        
        return response
    
    def _extract_all_info(self, user_input: str):
        """Extract all possible information from user input"""
        for field, extractor in self.info_extractors.items():
            value = extractor(user_input)
            if value:
                self.context.update_profile(field, value)
    
    def _extract_age(self, text: str) -> Optional[int]:
        """Extract age from text"""
        # Age with keywords
        match = re.search(r'(\d{1,3})\s*(?:years|సంవత్సరాల|ఏళ్ళు|year|సంవత్సరం|ఏళ్ల)', text.lower())
        if match:
            age = int(match.group(1))
            if 1 <= age <= 120:
                return age
        
        # Standalone number (if in collection state)
        if self.state in [AgentState.COLLECTING_BASIC_INFO, AgentState.COLLECTING_ADDITIONAL_INFO]:
            match = re.search(r'\b(\d{1,3})\b', text)
            if match:
                age = int(match.group(1))
                if 1 <= age <= 120:
                    return age
        
        return None
    
    def _extract_state(self, text: str) -> Optional[str]:
        """Extract state from text"""
        text_lower = text.lower()
        
        if any(word in text_lower for word in ['telangana', 'తెలంగాణ', 'తెలంగాణా']):
            return "Telangana"
        elif any(word in text_lower for word in ['andhra', 'ఆంధ్ర', 'ఆంధ్రప్రదేశ్', 'ఆంధ్రప్రదేశ']):
            return "Andhra Pradesh"
        
        return None
    
    def _extract_occupation(self, text: str) -> Optional[str]:
        """Extract occupation from text"""
        text_lower = text.lower()
        
        occupations = {
            "student": ['విద్యార్థి', 'student', 'చదువు', 'స్కూల్', 'కాలేజీ', 'college', 'school'],
            "farmer": ['రైతు', 'rythu', 'farmer', 'agriculture', 'వ్యవసాయం', 'వ్యవసాయ'],
            "weaver": ['చేనేత', 'weaver', 'handloom', 'చేనేత కార్మికుడు'],
            "labor": ['కూలీ', 'labor', 'worker', 'labour', 'కార్మికుడు'],
            "business": ['వ్యాపారి', 'business', 'trader', 'వ్యాపారం'],
        }
        
        for occ, keywords in occupations.items():
            if any(keyword in text_lower for keyword in keywords):
                return occ
        
        return None
    
    def _extract_income(self, text: str) -> Optional[int]:
        """Extract income from text"""
        match = re.search(r'(\d+(?:,\d+)*)\s*(?:rupees|రూపాయల|income|ఆదాయం)', text.lower())
        if match:
            income_str = match.group(1).replace(',', '')
            return int(income_str)
        
        return None
    
    def _extract_gender(self, text: str) -> Optional[str]:
        """Extract gender from text"""
        text_lower = text.lower()
        
        if any(word in text_lower for word in ['అబ్బాయి', 'boy', 'male', 'పురుషుడు']):
            return "male"
        elif any(word in text_lower for word in ['అమ్మాయి', 'girl', 'female', 'మహిళ', 'స్త్రీ']):
            return "female"
        
        return None
    
    def reset(self):
        """Reset conversation"""
        self.context = ConversationContext()
        self.state = AgentState.GREETING


def clean_text_for_tts(text: str) -> str:
    """Clean text for TTS - Remove ALL English content"""
    # Remove markdown bold
    text = re.sub(r'\*\*([^*]+)\*\*', r'\1', text)
    
    # Remove other markdown
    text = re.sub(r'\*+', '', text)
    text = re.sub(r'#', '', text)
    
    # Remove emojis
    text = re.sub(r'[🌐📍🎤✔❌]', '', text)
    
    # Remove bullet points
    text = re.sub(r'^\s*[-•]\s+', '', text, flags=re.MULTILINE)
    
    # Remove English in parentheses
    text = re.sub(r'\s*\([^)]*[a-zA-Z][^)]*\)', '', text)
    
    # Remove standalone English words
    text = re.sub(r'\b[a-zA-Z]+\b', '', text)
    
    # Clean whitespace
    text = re.sub(r'\s+', ' ', text)
    text = re.sub(r'\n\s*\n+', '\n', text)
    
    return text.strip()