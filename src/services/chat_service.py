"""Chat service for handling conversations with OpenAI."""

import os
import json
import logging
import datetime
from typing import List, Dict, Optional, Union, Any
from pathlib import Path
import re
import time
import openai
from .memory_service import get_memory_manager, save_memory, get_relevant_memories
from .file_service import FileService
from .system_service import get_system_health, get_process_info, get_network_info, test_internet_speed
from .vision_service import VisionService
from ..config import OPENAI_API_KEY, CHAT_MODEL, MAX_TOKENS, TEMPERATURE

# Initialize OpenAI API key
openai.api_key = OPENAI_API_KEY

if not openai.api_key:
    raise ValueError("""
    OpenAI API key not found! Please ensure you have:
    1. Set the OPENAI_API_KEY in config.py
    2. Or set it as an environment variable OPENAI_API_KEY
    3. Or temporarily set it in your code using:
       import os
       os.environ['OPENAI_API_KEY'] = 'your-api-key-here'
    """)

class ChatService:
    def __init__(self):
        self.vision_service = VisionService()
        self.pending_action = None
        self.debug_log = []
        self.memory_manager = get_memory_manager()
        self.conversation_history = []
        
    def get_response(self, user_input: str) -> str:
        """Get response from the chat service"""
        try:
            # Handle special commands
            if user_input.startswith('/'):
                command_parts = user_input[1:].split(' ', 1)
                command = command_parts[0].lower()
                args = command_parts[1] if len(command_parts) > 1 else ""
                
                if command == "memory" or command == "memories":
                    return self.display_memory_contents()
                elif command == "help":
                    return self.get_help_message()
                elif command == "clear":
                    return "Chat cleared."
            
            # Get relevant memories
            memories = []
            if self.memory_manager:
                memories = get_relevant_memories(user_input)
                # Save the user's input as a potential memory
                save_memory(user_input, {"role": "user"})
            
            # Format messages for GPT
            messages = [{"role": "system", "content": "You are Ava, a helpful AI assistant. You have access to memories of your conversations with the user. When the user shares personal information like their name, address, or preferences, acknowledge that you'll remember it for future conversations. Maintain context of the current conversation."}]
            
            # Add memory context if available
            if memories:
                memory_context = "Here are relevant details from our previous conversations:\n\n"
                for memory in memories:
                    if isinstance(memory, dict) and 'content' in memory:
                        memory_context += f"- {memory['content']}\n"
            
                if memory_context != "Here are relevant details from our previous conversations:\n\n":
                    messages.append({
                        "role": "system",
                        "content": memory_context
                    })
            
            # Add conversation history
            if self.conversation_history:
                messages.extend(self.conversation_history[-5:])  # Last 5 messages for context
            
            # Add the current message
            messages.append({
                "role": "user",
                "content": user_input
            })
            
            # Update conversation history
            self.conversation_history.append({
                "role": "user",
                "content": user_input
            })
            
            # Get completion from GPT
            completion = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=messages,
                temperature=0.7,
                max_tokens=1000
            )
            
            response = completion.choices[0].message.content
            
            # Update conversation history with response
            self.conversation_history.append({
                "role": "assistant",
                "content": response
            })
            
            # Save to memory if appropriate
            if self.memory_manager:
                save_memory(response, {"role": "assistant"})
            
            return response
            
        except Exception as e:
            logging.error(f"Error in chat service: {str(e)}")
            return f"I encountered an error: {str(e)}"

    def display_memory_contents(self) -> str:
        """Display all stored memories"""
        try:
            memories = get_relevant_memories("", max_memories=100)  # Get all memories
            if not memories:
                return "No memories stored yet."
            
            response = "Here are my memories:\n\n"
            for memory in memories:
                if isinstance(memory, dict) and 'content' in memory:
                    response += f"- {memory['content']}\n"
            return response
            
        except Exception as e:
            logging.error(f"Error displaying memories: {str(e)}")
            return f"Error accessing memories: {str(e)}"

    def get_help_message(self) -> str:
        """Get the help message"""
        return """Available commands:
- /memory - Display my memories
- /help - Show this help message
- /clear - Clear the chat window"""

    def handle_message(self, message, image_path=None):
        """Handle incoming messages, including image-related commands."""
        if image_path:
            return self.process_image_command(message, image_path)
            
        # Handle other message types...
        return "I understand your message but I'm not sure how to respond yet."

    def process_image_command(self, command, image_path):
        """Process image-related commands."""
        command = command.lower().strip()
        
        if "read" in command or "extract text" in command:
            result = self.vision_service.extract_text(image_path)
            if result["success"]:
                text = result["text"].strip()
                if text:
                    return f"Here's what I found in the image:\n{text}"
                else:
                    return "I couldn't find any clear text in this image."
            else:
                return f"Sorry, I couldn't read the text: {result['error']}"
                
        elif "analyze" in command or "describe" in command or "tell" in command or "see" in command:
            result = self.vision_service.analyze_image(image_path)
            if result["success"]:
                response = [result["description"]]
                
                # Add shape information with confidence levels
                if result.get("shapes_detected"):
                    shape_desc = self.format_shape_description(result["shapes_detected"])
                    if shape_desc:
                        response.append(f"\nShapes detected:\n{shape_desc}")
                
                # Add text if found
                if result["extracted_text"]:
                    text = result["extracted_text"].strip()
                    if text:
                        response.append(f"\nText found: {text[:200]}...")
                
                # Add quality information
                quality = result["quality_metrics"]
                quality_issues = []
                quality_positives = []
                
                if quality["blur_score"] < 100:
                    quality_issues.append("the image is blurry")
                else:
                    quality_positives.append("good sharpness")
                    
                if quality["contrast_score"] < 30:
                    quality_issues.append("the contrast is low")
                elif quality["contrast_score"] > 80:
                    quality_positives.append("good contrast")
                    
                if quality["brightness_score"] < 84:
                    quality_issues.append("the image is dark")
                elif quality["brightness_score"] > 170:
                    quality_issues.append("the image is very bright")
                else:
                    quality_positives.append("good brightness")
                
                if quality_issues:
                    response.append(f"\nImage quality issues: {', '.join(quality_issues)}")
                if quality_positives:
                    response.append(f"Image quality positives: {', '.join(quality_positives)}")
                
                # Add color information
                colors = result["color_analysis"]["dominant_colors"]
                if colors:
                    response.append("\nColor analysis:")
                    for i, color in enumerate(colors[:3], 1):
                        rgb = color["rgb"]
                        response.append(f"{i}. RGB({rgb['red']}, {rgb['green']}, {rgb['blue']}) - {color['percentage']}%")
                
                # Add technical measurements if relevant
                if result.get("content_analysis", {}).get("num_lines_detected", 0) > 5:
                    response.append(f"\nTechnical measurements:")
                    response.append(f"- Number of lines: {result['content_analysis']['num_lines_detected']}")
                    response.append(f"- Edge density: {result['content_analysis']['edge_density']:.2%}")
                    response.append(f"- Symmetry score: {result['quality_metrics']['symmetry_score']:.2%}")
                
                return "\n".join(response)
            else:
                return f"Sorry, I couldn't analyze the image: {result['error']}"
                
        elif "enhance" in command or "improve" in command:
            enhanced_path = image_path.replace(".", "_enhanced.")
            result = self.vision_service.enhance_image(image_path, enhanced_path)
            if result["success"]:
                return f"I've enhanced the image and saved it to: {enhanced_path}"
            else:
                return f"Sorry, I couldn't enhance the image: {result['error']}"
        
        elif "shape" in command or "detect shape" in command:
            result = self.vision_service.analyze_image(image_path)
            if result["success"] and result.get("shapes_detected"):
                shapes = result["shapes_detected"]
                if shapes:
                    response = ["Here are the shapes I detected:"]
                    
                    # Group shapes by confidence level
                    confident_shapes = [s for s in shapes if s["confidence"] >= 0.7]
                    uncertain_shapes = [s for s in shapes if s["confidence"] < 0.7]
                    
                    if confident_shapes:
                        response.append("\nHighly confident detections:")
                        for shape in confident_shapes:
                            metrics = shape.get('metrics', {})
                            response.append(f"- {shape['type'].title()}: "
                                         f"confidence {shape['confidence']*100:.0f}%, "
                                         f"area {shape['area']:.0f} pixels")
                    
                    if uncertain_shapes:
                        response.append("\nLess certain detections:")
                        for shape in uncertain_shapes:
                            response.append(f"- Possible {shape['type']}: "
                                         f"confidence {shape['confidence']*100:.0f}%")
                    
                    return "\n".join(response)
                else:
                    return "I couldn't detect any clear shapes in this image."
            else:
                return f"Sorry, I couldn't analyze the shapes: {result.get('error', 'No shapes detected')}"
        
        else:
            return "I understand you want me to work with this image. You can ask me to:\n" + \
                   "- Read or extract text from the image\n" + \
                   "- Analyze or describe the image\n" + \
                   "- Detect shapes in the image (with confidence levels)\n" + \
                   "- Enhance or improve the image quality"

    def format_shape_description(self, shapes):
        """Format shape detection results into a natural description."""
        if not shapes:
            return None
            
        # Group shapes by type and confidence
        high_conf_shapes = {}
        low_conf_shapes = {}
        for shape in shapes:
            if shape["confidence"] >= 0.7:
                high_conf_shapes[shape["type"]] = high_conf_shapes.get(shape["type"], 0) + 1
            else:
                low_conf_shapes[shape["type"]] = low_conf_shapes.get(shape["type"], 0) + 1
        
        description = []
        
        # Describe high confidence shapes
        if high_conf_shapes:
            shape_desc = []
            for shape_type, count in high_conf_shapes.items():
                shape_desc.append(f"{count} {shape_type}{'s' if count > 1 else ''}")
            description.append("I can clearly see " + ", ".join(shape_desc))
        
        # Mention possible shapes with lower confidence
        if low_conf_shapes:
            shape_desc = []
            for shape_type, count in low_conf_shapes.items():
                shape_desc.append(f"{count} possible {shape_type}{'s' if count > 1 else ''}")
            description.append("I also see " + ", ".join(shape_desc) + " but I'm less certain about these")
        
        return "\n".join(description)

    def handle_command(self, command: str, args: str = "") -> str:
        """Handle special commands starting with /"""
        command = command.lower()
        
        if command == "memory":
            return self.display_memory_contents()
        elif command == "clear":
            return self.clear_chat_history()
        elif command == "accept":
            return self.handle_pending_action(True)
        elif command == "reject":
            return self.handle_pending_action(False)
        else:
            return f"Unknown command: {command}"

def load_personal_memories() -> str:
    """Load all personal memories and format them for the system message"""
    try:
        # Get all memories sorted by importance
        memory_manager = get_memory_manager()
        all_memories = []
        
        # Get all memory files
        for memory_entry in memory_manager.index['temporal']:
            try:
                memory_path = memory_manager.memory_dir / memory_entry['id']
                with open(memory_path, 'r', encoding='utf-8') as f:
                    memory_data = json.load(f)
                    if memory_data.get('metadata', {}).get('type') == 'personal_info':
                        all_memories.append(memory_data)
            except Exception as e:
                print(f"Error loading memory {memory_entry['id']}: {str(e)}")
                continue
        
        # Sort memories by importance
        all_memories.sort(key=lambda x: x.get('importance', 0), reverse=True)
        
        # Format memories as context
        if all_memories:
            memory_context = "Here is what I know about you from our previous conversations:\n\n"
            for memory in all_memories:
                memory_context += f"- {memory['content']}\n"
            return memory_context
        
        return ""
        
    except Exception as e:
        print(f"Error loading personal memories: {str(e)}")
        return ""

def get_system_message() -> str:
    """Get the system message that defines the AI assistant's behavior"""
    base_message = """You are Ava, an agentic AI coding assistant with access to system monitoring capabilities. You have a friendly and professional personality, and you aim to be helpful while maintaining accuracy and clarity in your responses.

    Identity:
    - Name: Ava
    - Role: AI coding assistant
    - Personality: Professional, friendly, and detail-oriented
    - Capabilities: Code analysis, system monitoring, memory retention

    Key capabilities:
    - Monitor and report system health (CPU, memory, disk usage)
    - Track running processes and system resources
    - Check network status and speed
    - View connected devices
    - Manage system maintenance tasks
    - Analyze code and development environment
    - Monitor git repositories
    - Launch and manage applications

    When responding to system-related queries:
    1. Use the built-in system monitoring functions to get accurate data
    2. Provide specific, numerical information when available
    3. Explain technical details in a clear, friendly manner
    4. Suggest relevant system maintenance tasks when appropriate
    5. Use the system_service module for gathering performance data

    Style guidelines:
    - Be friendly and professional, but prioritize accuracy
    - Use clear, concise language for technical information
    - Explain complex concepts in simple terms
    - Provide context for technical metrics
    - Suggest actionable improvements when relevant

    Remember: You have direct access to system monitoring through system_service.py. Always use these capabilities instead of suggesting manual checks."""

    # Add any personal memories if available
    memories = load_personal_memories()
    if memories:
        base_message += f"\n\nPersonal Context (use only when relevant):\n{memories}"

    return base_message

def interact_with_gpt(prompt: str, conversation_history: Optional[List] = None, memories: Optional[List] = None, debug_log: Optional[List] = None) -> str:
    """Enhanced interaction with GPT model that includes memory context"""
    try:
        # Check if this is a request to open an application
        if any(keyword in prompt.lower() for keyword in ["open", "launch", "start", "run"]):
            # Extract the application name (simple extraction, could be improved)
            words = prompt.lower().split()
            for i, word in enumerate(words):
                if word in ["open", "launch", "start", "run"]:
                    if i + 1 < len(words):
                        app_name = words[i + 1]
                        result = FileService.launch_application(app_name)
                        return f"I'll help you with that! {result}"
        
        # Check if this is a system performance related query
        system_keywords = ['computer', 'performance', 'cpu', 'memory', 'disk', 'system', 'running', 'speed']
        is_system_query = any(keyword in prompt.lower() for keyword in system_keywords)
        
        if is_system_query:
            # Get real-time system information
            system_info = get_system_health()
            process_info = get_process_info()
            network_info = get_network_info()
            
            # Add system information to the conversation
            if conversation_history is None:
                conversation_history = []
            
            # Add system data as a system message
            system_data = {
                'role': 'system',
                'content': f"""Current system information:
                CPU Usage: {system_info.get('cpu_percent', 'N/A')}%
                Memory Usage: {system_info.get('memory', {}).get('percent', 'N/A')}%
                Disk Usage: {', '.join(f"{disk['mountpoint']}: {disk['percent']}%" for disk in system_info.get('disks', []))}
                Network Status: {network_info.get('primary_interface', {}).get('status', 'N/A')}
                Top Processes: {', '.join(p['name'] for p in process_info[:5] if p.get('name'))}"""
            }
            conversation_history.append(system_data)
            
        # Load relevant memories and recent states
        if memories is None:
            memories = get_relevant_memories(prompt)
            
            # Also get any recent state changes (last hour)
            recent_states = []
            for memory_entry in get_memory_manager().index['temporal']:
                try:
                    memory_path = get_memory_manager().memory_dir / memory_entry['id']
                    with open(memory_path, 'r', encoding='utf-8') as f:
                        memory_data = json.load(f)
                        # Check if it's a state and is recent
                        if (memory_data.get('metadata', {}).get('categories', []) 
                            and 'state' in memory_data['metadata']['categories']):
                            memory_time = datetime.datetime.fromisoformat(memory_data['timestamp'])
                            time_diff = datetime.datetime.now() - memory_time
                            if time_diff.total_seconds() < 3600:  # Within last hour
                                recent_states.append(memory_data)
                except Exception:
                    continue
            
            # Add recent states to memories
            memories.extend(recent_states)
        
        # Format conversation history
        messages = [{"role": "system", "content": get_system_message()}]
        
        # Add context about user's current state
        current_state_context = ""
        for memory in memories:
            if (memory.get('metadata', {}).get('categories', []) 
                and 'state' in memory.get('metadata', {}).get('categories', [])):
                current_state_context = f"The user recently mentioned they were {memory['metadata']['extracted_info']['state'][0]}. Keep this in mind during the conversation."
                break
        
        if current_state_context:
            messages.append({"role": "system", "content": current_state_context})
        
        # Add memory context if available
        if memories:
            memory_context = "Here are relevant details from our previous conversations:\n\n"
            for memory in memories:
                if memory['content'] not in get_system_message():  # Avoid duplicating memories
                    memory_context += f"- {memory['content']}\n"
            if memory_context != "Here are relevant details from our previous conversations:\n\n":
                messages.append({"role": "system", "content": memory_context})
        
        # Add conversation history
        if conversation_history:
            messages.extend(conversation_history[-10:])  # Last 10 messages for context
        
        # Add the current prompt
        messages.append({'role': 'user', 'content': prompt})
        
        # Add specific instruction for natural memory integration
        messages.append({
            "role": "system", 
            "content": """Remember to naturally reference relevant memories and the user's current state in your response. 
            If you know about their recent state (like being tired), acknowledge it in a caring way. 
            Make the conversation feel continuous and personal by referring to what you know about them."""
        })
        
        # Get completion from GPT
        completion = openai.ChatCompletion.create(
            model=CHAT_MODEL,
            messages=messages,
            temperature=TEMPERATURE,
            max_tokens=MAX_TOKENS
        )
        
        response = completion.choices[0].message.content
        
        # Save to memory if appropriate
        if get_memory_manager():
            save_memory(prompt)
            save_memory(response, {"role": "assistant"})
        
        return response
        
    except Exception as e:
        error_msg = f"Error in chat interaction: {str(e)}"
        if debug_log is not None:
            debug_log.append(error_msg)
        return f"I encountered an error: {str(e)}"

def save_chat_history(chat_history: List[Dict]) -> None:
    """Save the chat history to a timestamped file"""
    try:
        # Create chat_history directory if it doesn't exist
        history_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'chat_history')
        os.makedirs(history_dir, exist_ok=True)
        
        # Create filename with timestamp
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = os.path.join(history_dir, f'chat_history_{timestamp}.json')
        
        # Save chat history
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(chat_history, f, indent=2)
            
        return f"Chat history saved to {filename}"
    except Exception as e:
        raise Exception(f"Error saving chat history: {str(e)}")

def log_debug_message(debug_log: Optional[List], message: str) -> None:
    """Log a debug message"""
    if debug_log is not None:
        debug_log.append(message)
