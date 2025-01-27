"""Input area component for sending messages."""
import tkinter as tk
from tkinter import ttk
from typing import Optional, Callable
from src.core.event_bus import EventBus, MessageSent

class InputArea(ttk.Frame):
    """Component for inputting and sending messages."""
    
    def __init__(self, master, event_bus: EventBus, config: dict):
        """Initialize the input area.
        
        Args:
            master: The parent widget
            event_bus: The application event bus
            config: Configuration dictionary
        """
        super().__init__(master)
        self.event_bus = event_bus
        self.config = config
        
        self.setup_ui()
        self.setup_bindings()
    
    def setup_ui(self):
        """Set up the UI components."""
        # Create input frame
        input_frame = ttk.Frame(self)
        input_frame.pack(fill='x', padx=5, pady=5)
        
        # Create text input
        self.input_field = tk.Text(
            input_frame,
            wrap=tk.WORD,
            width=40,
            height=3,
            font=('Segoe UI', 10)
        )
        self.input_field.pack(side='left', fill='both', expand=True)
        
        # Create send button
        self.send_button = ttk.Button(
            input_frame,
            text='Send',
            command=self.send_message
        )
        self.send_button.pack(side='right', padx=5)
        
        # Create voice input button
        self.voice_button = ttk.Button(
            input_frame,
            text='🎤',
            width=3
        )
        self.voice_button.pack(side='right')
    
    def setup_bindings(self):
        """Set up keyboard bindings."""
        # Bind Enter to send message
        self.input_field.bind('<Return>', self._on_return)
        self.input_field.bind('<Shift-Return>', self._on_shift_return)
    
    def send_message(self):
        """Send the current message."""
        message = self.input_field.get('1.0', 'end-1c').strip()
        if message:
            # Publish message sent event
            self.event_bus.publish(MessageSent(
                content=message,
                user_id='user'  # In a real app, get this from user session
            ))
            
            # Clear input field
            self.input_field.delete('1.0', 'end')
    
    def set_voice_callback(self, callback: Callable[[], None]):
        """Set the callback for voice button clicks.
        
        Args:
            callback: The function to call when voice button is clicked
        """
        self.voice_button.configure(command=callback)
    
    def _on_return(self, event):
        """Handle Return key press."""
        self.send_message()
        return 'break'  # Prevent default behavior
    
    def _on_shift_return(self, event):
        """Handle Shift+Return key press."""
        return None  # Allow default behavior (newline)
