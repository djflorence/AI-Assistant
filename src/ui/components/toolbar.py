"""Toolbar component with action buttons."""
import tkinter as tk
from tkinter import ttk
from typing import Dict, Callable
from PIL import Image, ImageTk

class Toolbar(ttk.Frame):
    """Component for displaying action buttons."""
    
    def __init__(self, master, config: dict):
        """Initialize the toolbar.
        
        Args:
            master: The parent widget
            config: Configuration dictionary
        """
        super().__init__(master)
        self.config = config
        self.buttons: Dict[str, ttk.Button] = {}
        self.setup_ui()
    
    def setup_ui(self):
        """Set up the UI components."""
        # Create button frame
        button_frame = ttk.Frame(self)
        button_frame.pack(fill='x', padx=5, pady=5)
        
        # Default buttons
        self.add_button('clear', '🗑️', 'Clear chat')
        self.add_button('voice', '🎤', 'Toggle voice')
        self.add_button('theme', '🌓', 'Toggle theme')
        self.add_button('settings', '⚙️', 'Settings')
        self.add_button('help', '❓', 'Help')
    
    def add_button(self, name: str, text: str, tooltip: str = None):
        """Add a button to the toolbar.
        
        Args:
            name: Button identifier
            text: Button text/emoji
            tooltip: Optional tooltip text
        """
        button = ttk.Button(
            self,
            text=text,
            width=3
        )
        button.pack(side='left', padx=2)
        
        if tooltip:
            self._create_tooltip(button, tooltip)
        
        self.buttons[name] = button
    
    def set_callback(self, name: str, callback: Callable[[], None]):
        """Set the callback for a button.
        
        Args:
            name: Button identifier
            callback: Function to call when button is clicked
        """
        if name in self.buttons:
            self.buttons[name].configure(command=callback)
    
    def _create_tooltip(self, widget: ttk.Widget, text: str):
        """Create a tooltip for a widget.
        
        Args:
            widget: The widget to add tooltip to
            text: Tooltip text
        """
        tooltip = tk.Label(
            widget,
            text=text,
            background='#252526',
            foreground='#D4D4D4',
            relief='solid',
            borderwidth=1
        )
        
        def show_tooltip(event):
            tooltip.lift()
            tooltip.place(
                x=widget.winfo_rootx() - widget.winfo_x(),
                y=widget.winfo_rooty() - widget.winfo_y() + 30
            )
        
        def hide_tooltip(event):
            tooltip.place_forget()
        
        widget.bind('<Enter>', show_tooltip)
        widget.bind('<Leave>', hide_tooltip)
