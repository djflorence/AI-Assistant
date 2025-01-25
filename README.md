# AI Assistant Project

A powerful AI assistant that combines natural language processing, real-time weather data, and system monitoring capabilities to provide an interactive and helpful experience.

## Features

- Natural language chat interface
- Real-time weather information using OpenWeather API
- System monitoring and resource tracking
- File operations and management
- Plugin system for extensibility
- Memory management for contextual conversations

## Setup

1. Clone the repository
2. Create a virtual environment:
   ```bash
   python -m venv env
   source env/bin/activate  # On Windows: env\Scripts\activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Create a `.env` file with your API keys:
   ```
   OPENWEATHER_API_KEY=your_api_key_here
   ```
5. Run the application:
   ```bash
   python main.py
   ```

## Project Structure

- `src/`: Core application code
  - `core/`: Core functionality
  - `services/`: Various service modules
  - `ui/`: User interface components
- `plugins/`: Plugin system and available plugins
- `config/`: Configuration files
- `images/`: Image resources
- `styles/`: UI styling

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.
