"""Main window of the application."""
import tkinter as tk
from tkinter import ttk
from typing import Dict, Any

from src.core.event_bus import EventBus
from src.core.services.chat.chat_service import ChatService
from src.core.services.memory.memory_service import MemoryService
from src.core.services.voice.voice_service import VoiceService

from src.ui.components.chat_display import ChatDisplay
from src.ui.components.input_area import InputArea
from src.ui.components.toolbar import Toolbar
from src.ui.components.task_panel import TaskPanel

class MainWindow(tk.Tk):
    """Main application window."""
    
    def __init__(
        self,
        chat_service: ChatService,
        memory_service: MemoryService,
        voice_service: VoiceService,
        event_bus: EventBus,
        config: Dict[str, Any]
    ):
        """Initialize the main window.
        
        Args:
            chat_service: Service for handling chat
            memory_service: Service for handling memory
            voice_service: Service for handling voice
            event_bus: Application event bus
            config: Configuration dictionary
        """
        super().__init__()
        
        self.chat_service = chat_service
        self.memory_service = memory_service
        self.voice_service = voice_service
        self.event_bus = event_bus
        self.config = config
        
        self.setup_window()
        self.setup_ui()
        self.setup_bindings()
    
    def setup_window(self):
        """Configure the main window."""
        # Set window title
        self.title(self.config['app']['name'])
        
        # Set window size
        window_config = self.config['ui']['window']
        self.geometry(f"{window_config['width']}x{window_config['height']}")
        self.minsize(window_config['min_width'], window_config['min_height'])
        
        # Configure grid
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)
    
    def setup_ui(self):
        """Set up the UI components."""
        # Create toolbar
        self.toolbar = Toolbar(self, self.config)
        self.toolbar.grid(row=0, column=0, sticky='ew')
        
        # Create main content frame
        content = ttk.Frame(self)
        content.grid(row=1, column=0, sticky='nsew')
        content.grid_columnconfigure(0, weight=1)
        content.grid_rowconfigure(0, weight=1)
        
        # Create chat frame
        chat_frame = ttk.Frame(content)
        chat_frame.grid(row=0, column=0, sticky='nsew')
        chat_frame.grid_rowconfigure(0, weight=1)
        chat_frame.grid_columnconfigure(0, weight=1)
        
        # Create chat display
        self.chat_display = ChatDisplay(chat_frame, self.event_bus, self.config)
        self.chat_display.grid(row=0, column=0, sticky='nsew')
        
        # Create input area
        self.input_area = InputArea(chat_frame, self.event_bus, self.config)
        self.input_area.grid(row=1, column=0, sticky='ew')
        
        # Create task panel
        self.task_panel = TaskPanel(content, self.config)
        self.task_panel.grid(row=0, column=1, sticky='ns')
    
    def setup_bindings(self):
        """Set up event bindings."""
        # Set toolbar callbacks
        self.toolbar.set_callback('clear', self.chat_display.clear)
        self.toolbar.set_callback('voice', self.toggle_voice)
        self.toolbar.set_callback('theme', self.toggle_theme)
        self.toolbar.set_callback('settings', self.show_settings)
        self.toolbar.set_callback('help', self.show_help)
        
        # Set voice callback
        self.input_area.set_voice_callback(self.toggle_voice)
    
    def toggle_voice(self):
        """Toggle voice input."""
        # This would be implemented to start/stop voice input
        pass
    
    def toggle_theme(self):
        """Toggle between light and dark theme."""
        # This would be implemented to switch themes
        pass
    
    def show_settings(self):
        """Show settings dialog."""
        # This would be implemented to show settings
        pass
    
    def show_help(self):
        """Show help dialog."""
        # This would be implemented to show help
        pass
