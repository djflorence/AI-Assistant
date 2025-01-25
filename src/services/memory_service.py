"""Memory service for storing and retrieving conversation memories."""

import os
import json
import re
import datetime
from typing import Dict, List, Optional
from pathlib import Path

class Memory:
    def __init__(self, content: str, metadata: Dict = None):
        self.content = content
        self.metadata = metadata or {}
        self.timestamp = datetime.datetime.now().isoformat()
        self.importance = self._calculate_importance()
        
    def _calculate_importance(self) -> float:
        """Calculate importance score for memory"""
        score = 0.0
        
        # Personal information is most important
        if self._is_personal_info():
            score += 0.8
            self.metadata['type'] = 'personal_info'
        
        # Recent memories are more important
        age_hours = (datetime.datetime.now() - datetime.datetime.fromisoformat(self.timestamp)).total_seconds() / 3600
        time_factor = max(0, 1 - (age_hours / 24))  # Decay over 24 hours
        score += time_factor * 0.2
        
        return min(1.0, score)
        
    def _is_personal_info(self) -> bool:
        """Check if memory contains personal information"""
        content_lower = self.content.lower()
        personal_patterns = [
            r'(?:my name is|i am|i\'m|call me)\s+(\w+)',
            r'(?:name is|they call me)\s+(\w+)',
            r'(?:known as|go by)\s+(\w+)',
            r'(?:i live at|my address is|address is)\s+([0-9]+[^,]+(?:,\s*[^,]+)*)',  # Address pattern
            r'(?:live in|located in|based in)\s+([^,.]+(?:,\s*[^,]+)*)'  # Location pattern
        ]
        
        for pattern in personal_patterns:
            match = re.search(pattern, content_lower)
            if match:
                info_type = 'name'
                if 'address' in pattern or 'live' in pattern or 'located' in pattern:
                    info_type = 'address'
                
                self.metadata['personal_info'] = {
                    'type': info_type,
                    'value': match.group(1).strip()
                }
                return True
        return False

class MemoryManager:
    def __init__(self, memory_dir: str = None):
        if memory_dir is None:
            memory_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'memory')
        self.memory_dir = Path(memory_dir)
        self.memory_dir.mkdir(parents=True, exist_ok=True)
        
    def _load_secure_info(self) -> Dict[str, List[str]]:
        """Load secure information from david_info_secure.txt"""
        try:
            secure_file = self.memory_dir / 'david_info_secure.txt'
            if not secure_file.exists():
                return {}
                
            info = {'personal': [], 'interests': [], 'preferences': []}
            current_section = 'personal'
            
            with open(secure_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                    
                if line.startswith("David's Personal Information:"):
                    current_section = 'personal'
                elif line.startswith("Interests and Preferences:"):
                    current_section = 'interests'
                elif line.startswith(('1.', '2.', '3.', '4.', '5.', '6.', '7.', '8.', '9.')):
                    info[current_section].append(line[3:].strip())
                    
            return info
            
        except Exception as e:
            print(f"Error loading secure info: {str(e)}")
            return {}
        
    def add_memory(self, content: str, metadata: Dict = None) -> str:
        """Add a new memory"""
        try:
            memory = Memory(content, metadata)
            memory_id = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            
            # Save to file
            memory_path = self.memory_dir / f"{memory_id}.json"
            memory_data = {
                "content": memory.content,
                "metadata": memory.metadata,
                "timestamp": memory.timestamp,
                "importance": memory.importance
            }
            
            with open(memory_path, 'w', encoding='utf-8') as f:
                json.dump(memory_data, f, indent=2)
                
            return memory_id
            
        except Exception as e:
            print(f"Error saving memory: {str(e)}")
            return None
            
    def get_relevant_memories(self, context: str, max_memories: int = 5) -> List[Dict]:
        """Get memories relevant to the given context"""
        try:
            all_memories = []
            personal_info = {}
            
            # Load secure info first
            secure_info = self._load_secure_info()
            
            # Get all memory files
            memory_files = [f for f in os.listdir(self.memory_dir) if f.endswith('.json') and f != 'memory_index.json']
            
            # First pass: collect personal information and load memories
            for memory_file in memory_files:
                try:
                    with open(self.memory_dir / memory_file, 'r', encoding='utf-8') as f:
                        memory_data = json.load(f)
                        
                        # Handle old format memory files
                        if 'conversation' in memory_data:
                            # Convert old format to new format
                            for msg in memory_data['conversation']:
                                converted_memory = {
                                    'content': msg['content'],
                                    'metadata': {'role': msg['role']},
                                    'timestamp': memory_data.get('timestamp', '2000-01-01'),
                                    'importance': 0.5
                                }
                                all_memories.append(converted_memory)
                                
                                # Check for personal info in old format
                                if 'my name is' in msg['content'].lower():
                                    match = re.search(r'my name is (\w+)', msg['content'].lower())
                                    if match:
                                        personal_info['name'] = match.group(1).title()
                        else:
                            # New format memory
                            if memory_data.get('metadata', {}).get('type') == 'personal_info':
                                info = memory_data.get('metadata', {}).get('personal_info', {})
                                if info:
                                    personal_info[info['type']] = info['value']
                                    
                            all_memories.append(memory_data)
                except Exception as e:
                    print(f"Error loading memory {memory_file}: {str(e)}")
                    continue
            
            # Check if this is a personal info query
            is_personal_query = any(x in context.lower() for x in [
                'who am i', 'my name', 'what is my name', 'do you know my name',
                'what do you call me', 'what\'s my name', 'tell me about me',
                'what do you know about me', 'tell me what you know about me'
            ])
            
            if is_personal_query:
                # Create a comprehensive response from secure info
                response = []
                if secure_info.get('personal'):
                    response.extend(secure_info['personal'])
                if secure_info.get('interests'):
                    response.extend(secure_info['interests'])
                    
                if response:
                    return [{
                        'content': "Based on what I know about you:\n" + "\n".join(f"- {item}" for item in response),
                        'metadata': {'type': 'personal_info', 'role': 'assistant'},
                        'timestamp': datetime.datetime.now().isoformat(),
                        'importance': 1.0
                    }]
            
            # Sort by importance and recency
            all_memories.sort(key=lambda x: (
                float(x.get('importance', 0)),
                x.get('timestamp', '2000-01-01')
            ), reverse=True)
            
            return all_memories[:max_memories]
            
        except Exception as e:
            print(f"Error getting relevant memories: {str(e)}")
            return []

# Global memory manager instance
_memory_manager = None

def get_memory_manager():
    """Get or create the global memory manager instance"""
    global _memory_manager
    if _memory_manager is None:
        memory_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'memory')
        _memory_manager = MemoryManager(memory_dir)
    return _memory_manager

def save_memory(content: str, metadata: Dict = None):
    """Save a new memory"""
    manager = get_memory_manager()
    return manager.add_memory(content, metadata)

def get_relevant_memories(context: str, max_memories: int = 5):
    """Get memories relevant to the given context"""
    manager = get_memory_manager()
    return manager.get_relevant_memories(context, max_memories)
