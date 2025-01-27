"""Chat display component for showing messages."""
import tkinter as tk
from tkinter import ttk, scrolledtext
from typing import Optional
from datetime import datetime
from src.core.event_bus import EventBus, MessageSent, MessageReceived

class ChatDisplay(ttk.Frame):
    """Component for displaying chat messages."""
    
    def __init__(self, master, event_bus: EventBus, config: dict):
        """Initialize the chat display.
        
        Args:
            master: The parent widget
            event_bus: The application event bus
            config: Configuration dictionary
        """
        super().__init__(master)
        self.event_bus = event_bus
        self.config = config
        
        # Subscribe to events
        self.event_bus.subscribe(MessageSent, self._on_message_sent)
        self.event_bus.subscribe(MessageReceived, self._on_message_received)
        
        self.setup_ui()
        self.configure_tags()
    
    def setup_ui(self):
        """Set up the UI components."""
        # Create scrolled text widget
        self.chat_display = scrolledtext.ScrolledText(
            self,
            wrap=tk.WORD,
            width=50,
            height=20,
            font=('Segoe UI', 10)
        )
        self.chat_display.pack(expand=True, fill='both')
        
        # Make text widget read-only
        self.chat_display.configure(state='disabled')
    
    def configure_tags(self):
        """Configure text tags for message formatting."""
        self.chat_display.tag_configure(
            'user',
            foreground='#569CD6',
            spacing1=10,
            spacing3=5
        )
        self.chat_display.tag_configure(
            'assistant',
            foreground='#6A9955',
            spacing1=10,
            spacing3=5
        )
        self.chat_display.tag_configure(
            'timestamp',
            foreground='#808080',
            spacing1=5
        )
    
    def add_message(self, message: str, is_user: bool = True):
        """Add a message to the chat display.
        
        Args:
            message: The message to add
            is_user: Whether the message is from the user
        """
        timestamp = datetime.now().strftime(
            self.config['ui']['components']['chat_display']['timestamp_format']
        )
        
        self.chat_display.configure(state='normal')
        
        # Add timestamp
        self.chat_display.insert('end', f'[{timestamp}] ', 'timestamp')
        
        # Add message with appropriate tag
        tag = 'user' if is_user else 'assistant'
        prefix = 'You: ' if is_user else 'Assistant: '
        self.chat_display.insert('end', f'{prefix}{message}\n', tag)
        
        # Scroll to bottom
        self.chat_display.see('end')
        self.chat_display.configure(state='disabled')
    
    def clear(self):
        """Clear the chat display."""
        self.chat_display.configure(state='normal')
        self.chat_display.delete('1.0', 'end')
        self.chat_display.configure(state='disabled')
    
    def _on_message_sent(self, event: MessageSent):
        """Handle message sent event."""
        self.add_message(event.content, is_user=True)
    
    def _on_message_received(self, event: MessageReceived):
        """Handle message received event."""
        self.add_message(event.content, is_user=False)
