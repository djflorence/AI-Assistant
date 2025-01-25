from typing import Dict, List, Optional
import json
import os

class PersonaService:
    def __init__(self, personas_file: str = "personas.json"):
        self.personas_file = personas_file
        self.personas = self._load_personas()
        self.current_persona = None

    def _load_personas(self) -> Dict:
        if os.path.exists(self.personas_file):
            with open(self.personas_file, 'r') as f:
                return json.load(f)
        return self._get_default_personas()

    def _get_default_personas(self) -> Dict:
        return {
            "professional": {
                "name": "Professional Assistant",
                "style": "formal and precise",
                "greeting": "Hello, how may I assist you today?",
                "farewell": "Thank you for your time. Is there anything else you need?",
                "characteristics": ["formal", "precise", "professional"]
            },
            "friendly": {
                "name": "Friendly Helper",
                "style": "casual and supportive",
                "greeting": "Hi there! 👋 What can I help you with?",
                "farewell": "Take care! Let me know if you need anything else!",
                "characteristics": ["casual", "friendly", "supportive"]
            },
            "technical": {
                "name": "Technical Expert",
                "style": "technical and detailed",
                "greeting": "Welcome. Ready to dive into technical details.",
                "farewell": "Let me know if you need any technical clarification.",
                "characteristics": ["technical", "detailed", "focused"]
            }
        }

    def get_personas(self) -> List[str]:
        return list(self.personas.keys())

    def set_persona(self, persona_name: str) -> Optional[Dict]:
        if persona_name in self.personas:
            self.current_persona = self.personas[persona_name]
            return self.current_persona
        return None

    def get_current_persona(self) -> Optional[Dict]:
        return self.current_persona

    def add_persona(self, name: str, style: str, greeting: str, 
                   farewell: str, characteristics: List[str]) -> Dict:
        persona = {
            "name": name,
            "style": style,
            "greeting": greeting,
            "farewell": farewell,
            "characteristics": characteristics
        }
        self.personas[name.lower()] = persona
        self._save_personas()
        return persona

    def _save_personas(self):
        with open(self.personas_file, 'w') as f:
            json.dump(self.personas, f, indent=2)

    def get_response_style(self, message: str) -> str:
        if not self.current_persona:
            return message
            
        # Adapt message based on current persona
        persona = self.current_persona
        if "formal" in persona["characteristics"]:
            message = message.replace("Hi", "Hello").replace("Hey", "Hello")
            message = message.replace("!", ".")
        elif "friendly" in persona["characteristics"]:
            message = message.replace("Hello", "Hi")
            if not message.endswith("!"):
                message = message + "!"
                
        return message
