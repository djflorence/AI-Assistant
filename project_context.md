# AI Assistant Project Context

## Project Structure
```
c:/AI/
├── main.py                 # Main entry point
├── memory/                 # Memory storage directory
│   ├── *.json             # Memory files
│   └── david_info_secure.txt  # Secure personal information
└── src/
    ├── core/
    │   └── chat_interface.py  # Main chat UI and interaction handling
    └── services/
        ├── chat_service.py    # Chat and GPT interaction service
        ├── memory_service.py  # Memory management service
        ├── voice_service.py   # Voice input/output service
        ├── vision_service.py  # Image processing service
        └── other services...  # Additional functionality
```

## Key Components

### Memory System
- Uses both JSON files and secure text file for storage
- Handles both old and new format memory files
- Prioritizes personal information and recent memories
- Supports conversation history and context maintenance

### Voice System
- Speech-to-text for input
- Text-to-speech for output
- Toggle functionality with status tracking
- Error handling and recovery

### Chat Interface
- Modern UI with dark theme
- Support for text and voice input
- Memory display and command system
- Status updates and error handling

## Important Files
1. `david_info_secure.txt`: Contains personal information and preferences
2. `memory/*.json`: Stores conversation history and learned information
3. `chat_service.py`: Handles GPT interactions and memory integration
4. `memory_service.py`: Manages all memory operations and retrieval

## Special Commands
- `/memory` or `/memories`: Display recent memories
- `/help`: Show available commands
- `/clear`: Clear chat window

## Critical Features
1. Personal information handling and recall
2. Conversation context maintenance
3. Voice input/output functionality
4. Memory persistence across sessions

## Development Notes
- Python environment in `ai_env/`
- Uses OpenAI's GPT for chat functionality
- Implements memory manager for persistent storage
- Voice services require speech recognition setup

To restore context in a new session:
1. Ensure the project structure is intact
2. Verify `david_info_secure.txt` is present in the memory directory
3. Check that all memory files are accessible
4. Confirm Python environment is properly set up

## Recent Updates
- Enhanced memory system with secure info integration
- Improved voice input reliability
- Better personal information handling
- Fixed conversation context maintenance
