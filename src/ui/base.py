import tkinter as tk
from tkinter import ttk
from typing import Optional, Dict, Any, Callable

class BaseComponent(ttk.Frame):
    """Base class for UI components"""
    
    def __init__(self, master: tk.Widget, **kwargs):
        super().__init__(master, **kwargs)
        self.master = master
        self._setup_styles()
        self._create_widgets()
        self._setup_layout()
        self._bind_events()
    
    def _setup_styles(self):
        """Setup ttk styles for the component"""
        pass
    
    def _create_widgets(self):
        """Create widgets for the component"""
        pass
    
    def _setup_layout(self):
        """Setup widget layout"""
        pass
    
    def _bind_events(self):
        """Bind event handlers"""
        pass
    
    def update_theme(self, theme: Dict[str, Any]):
        """Update component theme"""
        pass
    
    def show(self):
        """Show the component"""
        self.grid()
    
    def hide(self):
        """Hide the component"""
        self.grid_remove()

class ScrollableFrame(BaseComponent):
    """A scrollable frame container with optional text widget for chat display"""
    
    def __init__(self, master: tk.Widget, chat_mode: bool = False, **kwargs):
        self.canvas = None
        self.scrollable_frame = None
        self.scrollbar = None
        self.chat_mode = chat_mode
        self.text_widget = None
        super().__init__(master, **kwargs)
    
    def _setup_styles(self):
        style = ttk.Style()
        style.configure("Scrollable.TFrame", background="#2b2b2b")
    
    def _create_widgets(self):
        if self.chat_mode:
            # Create text widget with scrollbar for chat
            self.text_widget = tk.Text(self, wrap=tk.WORD, bg="#2b2b2b", fg="#ffffff",
                                     insertbackground="#ffffff", state="disabled")
            self.scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.text_widget.yview)
            self.text_widget.configure(yscrollcommand=self.scrollbar.set)
        else:
            # Create canvas and scrollbar for normal scrollable frame
            self.canvas = tk.Canvas(self, bg="#2b2b2b", highlightthickness=0)
            self.scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
            self.scrollable_frame = ttk.Frame(self.canvas, style="Scrollable.TFrame")
            
            # Configure canvas
            self.scrollable_frame.bind(
                "<Configure>",
                lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
            )
            self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
            self.canvas.configure(yscrollcommand=self.scrollbar.set)
            
            # Bind mouse wheel
            self.bind_mousewheel()
    
    def _setup_layout(self):
        if self.chat_mode:
            self.text_widget.grid(row=0, column=0, sticky="nsew")
            self.scrollbar.grid(row=0, column=1, sticky="ns")
        else:
            self.canvas.grid(row=0, column=0, sticky="nsew")
            self.scrollbar.grid(row=0, column=1, sticky="ns")
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)
    
    def bind_mousewheel(self):
        """Bind mouse wheel to scrolling"""
        def _on_mousewheel(event):
            if self.chat_mode:
                self.text_widget.yview_scroll(int(-1 * (event.delta / 120)), "units")
            else:
                self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        
        if self.chat_mode:
            self.text_widget.bind_all("<MouseWheel>", _on_mousewheel)
        else:
            self.canvas.bind_all("<MouseWheel>", _on_mousewheel)
    
    def unbind_mousewheel(self):
        """Unbind mouse wheel scrolling"""
        if self.chat_mode:
            self.text_widget.unbind_all("<MouseWheel>")
        else:
            self.canvas.unbind_all("<MouseWheel>")

class StatusBar(BaseComponent):
    """Status bar component"""
    
    def __init__(self, master: tk.Widget, **kwargs):
        self.status_label = None
        self.progress_bar = None
        super().__init__(master, **kwargs)
    
    def _setup_styles(self):
        style = ttk.Style()
        style.configure("Status.TLabel",
                       background="#1e1e1e",
                       foreground="#ffffff",
                       padding=2)
        style.configure("Status.Horizontal.TProgressbar",
                       background="#007acc",
                       troughcolor="#2b2b2b")
    
    def _create_widgets(self):
        self.status_label = ttk.Label(self, text="Ready", style="Status.TLabel")
        self.progress_bar = ttk.Progressbar(self, mode="indeterminate",
                                          style="Status.Horizontal.TProgressbar")
    
    def _setup_layout(self):
        self.status_label.grid(row=0, column=0, sticky="ew")
        self.grid_columnconfigure(0, weight=1)
    
    def set_status(self, text: str, show_progress: bool = False):
        """Update status text and progress bar"""
        self.status_label.configure(text=text)
        if show_progress:
            self.progress_bar.grid(row=0, column=1, padx=5)
            self.progress_bar.start(10)
        else:
            self.progress_bar.stop()
            self.progress_bar.grid_remove()
    
    def clear(self):
        """Clear status"""
        self.status_label.configure(text="Ready")
        self.progress_bar.stop()
        self.progress_bar.grid_remove()
