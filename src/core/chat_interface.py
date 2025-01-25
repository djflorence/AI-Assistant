import os
import sys
import json
import time
import queue
import logging
import datetime
import threading
import re
from typing import List, Dict, Optional, Union, Any
from pathlib import Path
from threading import Thread
from queue import Queue, Empty

import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
from tkinter.scrolledtext import ScrolledText
from PIL import Image, ImageTk
import re
from datetime import datetime
from queue import Queue, Empty
from threading import Thread
from src.services.file_service import FileService
from src.services.system_service import (
    get_system_health,
    get_process_info,
    get_network_info,
    test_internet_speed,
    get_system_devices,
    get_environment_info,
    scan_installed_apps
)
from src.services.chat_service import (
    interact_with_gpt,
    save_chat_history,
    get_relevant_memories,
    save_memory,
    ChatService
)
from src.services.realtime_service import RealtimeService
from src.services.rss_service import RSSService
from src.services.snippet_service import SnippetService
from src.services.summarization_service import SummarizationService
from src.services.persona_service import PersonaService
from src.services.plugin_service import PluginService
from src.services.voice_service import VoiceService
from src.services.vision_service import VisionService
from src.services.screen_monitor_service import ScreenMonitorService
import time
import logging
import re

# Theme colors
class Theme:
    def __init__(self):
        self.colors = {
            'background': '#1E1E1E',
            'text': '#D4D4D4',
            'accent': '#569CD6',
            'error': '#F44747',
            'success': '#6A9955',
            'warning': '#CE9178',
            'secondary_text': '#808080',
            'button': '#2D2D2D',
            'button_hover': '#3D3D3D',
            'tooltip_bg': '#252526',
            'tooltip_fg': '#D4D4D4'
        }

THEME = Theme()

class ModernScrolledText(ScrolledText):
    """Custom ScrolledText widget with modern styling"""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Configure scrollbar
        scrollbar = ttk.Scrollbar(self, orient='vertical', command=self.yview)
        scrollbar.pack(side='right', fill='y')
        
        self.configure(yscrollcommand=scrollbar.set)
        
        # Style the scrollbar
        style = ttk.Style()
        style.configure('Custom.Vertical.TScrollbar',
                       background=THEME.colors['background'],
                       troughcolor=THEME.colors['button'],
                       arrowcolor=THEME.colors['text'])
        scrollbar.configure(style='Custom.Vertical.TScrollbar')

class TaskPanel(ttk.Frame):
    """Panel showing current tasks and their status."""
    def __init__(self, master, theme):
        super().__init__(master)
        self.theme = theme
        self.tasks = {}  # {task_id: task_info}
        self.setup_ui()
        
    def setup_ui(self):
        """Set up the task panel UI."""
        # Title
        title_frame = ttk.Frame(self)
        title_frame.pack(fill='x', padx=5, pady=5)
        
        title_label = ttk.Label(
            title_frame, 
            text="Active Tasks",
            font=('Segoe UI', 12, 'bold'),
            foreground=self.theme.colors['text']
        )
        title_label.pack(side='left')
        
        # Task list frame with scrollbar
        self.task_frame = ttk.Frame(self)
        self.task_frame.pack(fill='both', expand=True, padx=5)
        
        # Canvas for scrolling
        self.canvas = tk.Canvas(
            self.task_frame,
            bg=self.theme.colors['background'],
            highlightthickness=0
        )
        scrollbar = ttk.Scrollbar(
            self.task_frame,
            orient='vertical',
            command=self.canvas.yview
        )
        
        # Frame to hold task items
        self.task_list = ttk.Frame(self.canvas)
        self.task_list.bind(
            '<Configure>',
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox('all'))
        )
        
        # Create window in canvas
        self.canvas.create_window((0, 0), window=self.task_list, anchor='nw', width=self.canvas.winfo_reqwidth())
        self.canvas.configure(yscrollcommand=scrollbar.set)
        
        # Pack scrolling components
        self.canvas.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')
        
        # Bind mouse wheel
        self.canvas.bind('<MouseWheel>', self._on_mousewheel)
        
    def _on_mousewheel(self, event):
        """Handle mouse wheel scrolling."""
        self.canvas.yview_scroll(int(-1 * (event.delta / 120)), 'units')
        
    def add_task(self, task_id, task_type, details=None):
        """Add a new task to the panel."""
        # Create task frame
        task_frame = ttk.Frame(self.task_list)
        task_frame.pack(fill='x', padx=5, pady=2)
        
        # Task icon based on type
        icon_label = ttk.Label(
            task_frame,
            text=self._get_task_icon(task_type),
            font=('Segoe UI', 14),
            foreground=self.theme.colors['text']
        )
        icon_label.pack(side='left', padx=5)
        
        # Task info
        info_frame = ttk.Frame(task_frame)
        info_frame.pack(side='left', fill='x', expand=True, padx=5)
        
        title_label = ttk.Label(
            info_frame,
            text=self._get_task_title(task_type),
            font=('Segoe UI', 10, 'bold'),
            foreground=self.theme.colors['text']
        )
        title_label.pack(anchor='w')
        
        # Status label with loading animation
        status_label = ttk.Label(
            info_frame,
            text="Processing...",
            font=('Segoe UI', 9),
            foreground=self.theme.colors['secondary_text']
        )
        status_label.pack(anchor='w')
        
        # Store task info
        self.tasks[task_id] = {
            'frame': task_frame,
            'status_label': status_label,
            'type': task_type,
            'details': details,
            'start_time': time.time()
        }
        
        # Start loading animation
        self._animate_loading(task_id)
        
        # If it's an image task, show the image preview
        if task_type == 'image' and details:
            try:
                # Create image preview
                img = Image.open(details)
                # Resize to fit panel
                img.thumbnail((180, 180))
                photo = ImageTk.PhotoImage(img)
                
                preview = ttk.Label(task_frame, image=photo)
                preview.image = photo  # Keep reference
                preview.pack(pady=5)
                self.tasks[task_id]['preview'] = preview
            except Exception as e:
                print(f"Error creating image preview: {e}")
        
        # Update scroll region
        self.canvas.configure(scrollregion=self.canvas.bbox('all'))
        
    def update_task(self, task_id, status, result=None):
        """Update task status and optionally show result."""
        if task_id in self.tasks:
            task = self.tasks[task_id]
            status_label = task['status_label']
            
            if status == 'completed':
                status_label.configure(
                    text="Completed",
                    foreground=self.theme.colors['success']
                )
                # Schedule removal after 5 seconds
                self.after(5000, lambda: self.remove_task(task_id))
            elif status == 'error':
                status_label.configure(
                    text=f"Error: {result if result else 'Unknown error'}",
                    foreground=self.theme.colors['error']
                )
            elif status == 'cancelled':
                status_label.configure(
                    text="Cancelled",
                    foreground=self.theme.colors['warning']
                )
                # Schedule removal after 3 seconds
                self.after(3000, lambda: self.remove_task(task_id))
    
    def remove_task(self, task_id):
        """Remove a task from the panel."""
        if task_id in self.tasks:
            self.tasks[task_id]['frame'].destroy()
            del self.tasks[task_id]
            # Update scroll region
            self.canvas.configure(scrollregion=self.canvas.bbox('all'))
    
    def _get_task_icon(self, task_type):
        """Get appropriate icon for task type."""
        icons = {
            'image': '🖼️',
            'text': '📝',
            'voice': '🎤',
            'code': '💻',
            'file': '📁',
            'system': '⚙️',
            'default': '📋'
        }
        return icons.get(task_type, icons['default'])
    
    def _get_task_title(self, task_type):
        """Get appropriate title for task type."""
        titles = {
            'image': 'Analyzing Image',
            'text': 'Processing Text',
            'voice': 'Processing Voice',
            'code': 'Analyzing Code',
            'file': 'Processing File',
            'system': 'System Task',
            'default': 'Processing'
        }
        return titles.get(task_type, titles['default'])
    
    def _animate_loading(self, task_id):
        """Animate the loading dots for a task."""
        if task_id in self.tasks:
            task = self.tasks[task_id]
            status_label = task['status_label']
            current_text = status_label.cget('text')
            
            if current_text.startswith('Processing'):
                dots = current_text.count('.')
                new_dots = '.' * ((dots + 1) % 4)
                status_label.configure(text=f"Processing{new_dots}")
                
                # Continue animation
                self.after(500, lambda: self._animate_loading(task_id))

class ChatInterface(ttk.Frame):
    def __init__(self, master=None):
        super().__init__(master)
        self.master = master
        self.master.title("AI Assistant")
        
        # Configure window
        self.master.configure(bg=THEME.colors['background'])
        self.setup_window_geometry()
        
        # Initialize variables
        self.conversation_history = []
        self.max_history = 50
        self.callback_queue = Queue()
        self.last_command = None
        self.accept_all_commands = True
        
        # Initialize services
        self.snippet_service = SnippetService()
        self.summarization_service = SummarizationService()
        self.persona_service = PersonaService()
        self.plugin_service = PluginService()
        self.vision_service = VisionService()
        self.voice_service = VoiceService()
        self.chat_service = ChatService()
        self.file_service = FileService()
        self.realtime_service = RealtimeService()
        self.rss_service = RSSService()
        
        # Start RSS auto-updates
        self.rss_service.start_auto_update()
        
        # Initialize voice
        self.voice_service.setup_voice()
        
        # Initialize screen monitor - disabled to avoid conflicts
        self.screen_monitor = None
        
        # Scan for installed applications
        from src.services.system_service import scan_installed_apps
        scan_installed_apps()
        
        # Set up UI
        self.configure_styles()
        self.create_widgets()
        
        # Set default persona
        self.persona_service.set_persona("professional")
        
        # Start monitoring
        try:
            self.file_service.start_monitoring('uploaded_files', self.on_file_change)
            self.file_service.start_monitoring('screenshots', self.on_file_change)
        except Exception as e:
            logging.error(f"Error setting up file monitoring: {e}")
        
        # Start queue checker
        self.check_queue()
        
        # Bind cleanup to window closing
        self.master.protocol("WM_DELETE_WINDOW", self.on_closing)
    
    def setup_window_geometry(self):
        """Set up responsive window geometry"""
        # Get screen dimensions
        screen_width = self.master.winfo_screenwidth()
        screen_height = self.master.winfo_screenheight()
        
        # Calculate window size (80% of screen)
        window_width = int(screen_width * 0.8)
        window_height = int(screen_height * 0.8)
        
        # Calculate position
        x = (screen_width - window_width) // 2
        y = (screen_height - window_height) // 2
        
        # Set minimum size
        self.master.minsize(800, 600)
        
        # Set geometry
        self.master.geometry(f'{window_width}x{window_height}+{x}+{y}')
        
        # Configure grid weights for responsiveness
        self.master.grid_rowconfigure(0, weight=1)
        self.master.grid_columnconfigure(0, weight=1)
    
    def create_widgets(self):
        """Create and arrange all UI widgets"""
        # Main container with task panel
        main_container = ttk.PanedWindow(self, orient='horizontal')
        main_container.pack(fill='both', expand=True)
        
        # Left panel for chat and buttons
        left_panel = ttk.Frame(main_container)
        main_container.add(left_panel, weight=7)
        
        # Right panel for tasks
        self.task_panel = TaskPanel(main_container, THEME)
        main_container.add(self.task_panel, weight=3)
        
        # Create status bar in left panel
        self.status_bar = ttk.Label(
            left_panel,
            text="Ready",
            style='Status.TLabel',
            anchor='w'
        )
        self.status_bar.pack(fill='x', padx=5, pady=2)
        
        # Create toolbar in left panel
        self.create_toolbar(left_panel)
        
        # Create main content area in left panel
        content = ttk.Frame(left_panel)
        content.pack(fill='both', expand=True, padx=5, pady=5)
        
        # Create left sidebar for buttons
        self.sidebar = ttk.Frame(content, style='Sidebar.TFrame')
        self.sidebar.pack(side='left', fill='y', padx=5, pady=5)
        
        # Create chat area container
        chat_container = ttk.Frame(content)
        chat_container.pack(side='left', fill='both', expand=True)
        
        # Set up chat area in chat container
        self.setup_chat_area(chat_container)
        
        # Set up input area in chat container
        self.setup_input_area(chat_container)
        
        # Set up sidebar buttons
        self.setup_buttons()
    
    def configure_styles(self):
        """Configure ttk styles for the interface"""
        style = ttk.Style()
        
        # Configure frame styles
        style.configure('Main.TFrame', background=THEME.colors['background'])
        style.configure('Sidebar.TFrame', background=THEME.colors['button'])
        
        # Configure button styles
        style.configure('Sidebar.TButton',
            background=THEME.colors['button'],
            foreground=THEME.colors['text'],
            padding=5
        )
        style.map('Sidebar.TButton',
            background=[('active', THEME.colors['button_hover'])]
        )
        
        style.configure('Toolbar.TButton',
            background=THEME.colors['button'],
            foreground=THEME.colors['text'],
            padding=2
        )
        style.map('Toolbar.TButton',
            background=[('active', THEME.colors['button_hover'])]
        )
        
        # Configure label styles
        style.configure('Status.TLabel',
            background=THEME.colors['background'],
            foreground=THEME.colors['text'],
            padding=2
        )
        
        # Configure chat styles
        style.configure('Chat.TFrame',
            background=THEME.colors['background']
        )
        
        # Configure checkbutton styles
        style.configure('Toolbar.TCheckbutton',
            background=THEME.colors['background'],
            foreground=THEME.colors['text']
        )
    
    def create_toolbar(self, parent):
        """Create toolbar with action buttons"""
        toolbar = ttk.Frame(parent)
        toolbar.pack(fill='x', padx=5, pady=2)
        
        # Image upload button
        upload_btn = ttk.Button(
            toolbar,
            text="📷",
            width=3,
            command=self.upload_file,
            style='Toolbar.TButton'
        )
        upload_btn.pack(side='left', padx=2)
        
        # Add tooltip for upload button
        self.create_tooltip(upload_btn, "Upload image for analysis")
        
        # Voice input button
        self.voice_button = ttk.Button(
            toolbar,
            text="🎤",
            width=3,
            command=self.toggle_voice_input,
            style='Toolbar.TButton'
        )
        self.voice_button.pack(side='left', padx=2)
        self.create_tooltip(self.voice_button, "Toggle voice input")
        
        # Persona selector
        ttk.Label(toolbar, text="Persona:").pack(side='left', padx=2)
        self.persona_var = tk.StringVar(value="professional")
        persona_combo = ttk.Combobox(
            toolbar,
            textvariable=self.persona_var,
            values=self.persona_service.get_personas(),
            state="readonly",
            width=15
        )
        persona_combo.pack(side='left', padx=2)
        persona_combo.bind('<<ComboboxSelected>>', self.on_persona_change)
        
        # Voice toggle
        self.voice_var = tk.BooleanVar(value=False)
        voice_btn = ttk.Checkbutton(
            toolbar,
            text="Voice Input",
            variable=self.voice_var,
            command=self.toggle_voice_input,
            style='Toolbar.TCheckbutton'
        )
        voice_btn.pack(side='left', padx=10)
        
        # Snippet button
        snippet_btn = ttk.Button(
            toolbar,
            text="Snippets",
            command=self.show_snippets,
            style='Toolbar.TButton'
        )
        snippet_btn.pack(side='left', padx=2)
        
        # Summary button
        summary_btn = ttk.Button(
            toolbar,
            text="Summarize",
            command=self.show_summary,
            style='Toolbar.TButton'
        )
        summary_btn.pack(side='left', padx=2)
        
        # Plugins button
        plugins_btn = ttk.Button(
            toolbar,
            text="Plugins",
            command=self.show_plugins,
            style='Toolbar.TButton'
        )
        plugins_btn.pack(side='left', padx=2)
    
    def setup_buttons(self):
        """Set up the sidebar buttons"""
        buttons = [
            ("System Health", self.show_system_health),
            ("Processes", self.show_processes),
            ("Network Info", self.show_network_info),
            ("Speed Test", self.run_speed_test),
            ("Devices", self.show_devices),
            ("Clean System", self.clean_temp_files),
            ("Analyze Code", self.analyze_code),
            ("Git Status", self.show_git_status),
            ("Dev Servers", self.show_dev_servers),
            ("Environment", self.show_env_info),
            ("Clear Chat", self.clear_chat),
            ("Save Chat", self.save_chat),
            ("Toggle Theme", self.toggle_theme)
        ]
        
        for text, command in buttons:
            btn = ttk.Button(
                self.sidebar,
                text=text,
                command=command,
                style='Sidebar.TButton',
                width=15
            )
            btn.pack(fill='x', padx=5, pady=2)
    
    def setup_chat_area(self, parent):
        """Set up the chat display area"""
        # Create chat display
        self.chat_display = ModernScrolledText(
            parent,
            wrap='word',
            font=('Segoe UI', 10),
            padx=10,
            pady=10,
            height=20,
            background=THEME.colors['background'],
            foreground=THEME.colors['text'],
            insertbackground=THEME.colors['text']
        )
        self.chat_display.pack(fill='both', expand=True, padx=5, pady=5)
        self.chat_display.configure(state='disabled')
        
        # Configure tags for different message types
        self.chat_display.tag_configure(
            'user',
            foreground=THEME.colors['text'],
            spacing1=10,
            spacing3=10
        )
        self.chat_display.tag_configure(
            'assistant',
            foreground=THEME.colors['accent'],
            spacing1=10,
            spacing3=10
        )
        self.chat_display.tag_configure(
            'error',
            foreground=THEME.colors['error'],
            spacing1=10,
            spacing3=10
        )
        self.chat_display.tag_configure(
            'system',
            foreground=THEME.colors['secondary_text'],
            spacing1=10,
            spacing3=10
        )
        
    def setup_input_area(self, parent):
        """Set up the input area for chat"""
        input_frame = ttk.Frame(parent)
        input_frame.pack(fill='x', padx=5, pady=5)
        
        # Create input field
        self.input_field = tk.Text(
            input_frame,
            font=('Segoe UI', 10),
            height=5,
            width=50
        )
        self.input_field.pack(side='left', fill='x', expand=True, padx=(0, 5))
        
        # Bind events
        self.input_field.bind('<Return>', self.send_message)
        self.input_field.bind('<Control-Return>', lambda e: self.input_field.insert(tk.END, '\n'))
        
        # Create send button
        self.send_button = ttk.Button(
            input_frame,
            text="Send",
            command=self.send_message,
            style='Custom.TButton',
            width=8
        )
        self.send_button.pack(side='right')
        
        # Focus input field
        self.input_field.focus()
    
    def configure_tags(self):
        """Configure text tags for chat display"""
        # Configure text colors
        self.chat_display.tag_configure('user', foreground='#4CAF50')  # Green for user
        self.chat_display.tag_configure('assistant', foreground='#2196F3')  # Blue for assistant
        self.chat_display.tag_configure('system', foreground=THEME.colors['error'])  # Red for system/error messages
        self.chat_display.tag_configure('timestamp', foreground='#9E9E9E')  # Gray for timestamp
        self.chat_display.tag_configure('message', foreground=THEME.colors['text'])  # White for message content
        self.chat_display.tag_configure('name', foreground=THEME.colors['text'])  # White for name

    def check_queue(self):
        """Check for callbacks in the queue"""
        try:
            while True:  # Process all available callbacks
                try:
                    callback = self.callback_queue.get_nowait()
                    if callback:
                        callback()
                except queue.Empty:
                    break
                except Exception as callback_error:
                    logging.error(f"Error executing callback: {str(callback_error)}")
        except Exception as queue_error:
            logging.error(f"Error in check_queue: {str(queue_error)}")
        finally:
            # Schedule the next check
            if self.master:  # Only schedule if window still exists
                self.master.after(100, self.check_queue)
    
    def send_message(self, event=None):
        """Send a message to the chat"""
        message = self.input_field.get("1.0", "end-1c").strip()
        if not message:
            return

        # Clear input
        self.input_field.delete("1.0", tk.END)
        
        # Update status
        self.update_status("Processing your request...")
        
        # Display user message
        self.add_to_chat(message, is_user=True)
        
        # Save message to history
        self.conversation_history.append({
            "message": message,
            "is_user": True,
            "timestamp": datetime.now().isoformat()
        })

        # Process message in background
        def process_message():
            try:
                # Check for weather-related queries
                weather_patterns = [
                    r'weather (?:in|at|for)? ?(.+)',
                    r'what\'s the weather (?:like )?(?:in|at|for)? ?(.+)?',
                    r'how\'s the weather (?:in|at|for)? ?(.+)?',
                    r'temperature (?:in|at|for)? ?(.+)',
                    r'current weather',
                    r'weather'
                ]
                
                for pattern in weather_patterns:
                    match = re.search(pattern, message.lower())
                    if match:
                        try:
                            city = match.group(1) if match.groups() and match.group(1) else "Boston"
                            # Clean up city name
                            city = city.strip().replace(',', ' ').replace('  ', ' ')
                            weather_data = self.realtime_service.get_weather(city)
                            if weather_data:
                                response = (
                                    f"🌤️ Weather in {weather_data['location']} as of {weather_data['timestamp']}:\n"
                                    f"Temperature: {weather_data['temperature']}°F (Feels like {weather_data['feels_like']}°F)\n"
                                    f"Condition: {weather_data['description']}\n"
                                    f"Humidity: {weather_data['humidity']}%\n"
                                    f"Wind Speed: {weather_data['wind_speed']} mph"
                                )
                            else:
                                response = f"Sorry, I couldn't find weather data for {city}. Please try another location."
                            self.callback_queue.put(lambda: self.add_to_chat(response, is_user=False))
                            return
                        except Exception as weather_error:
                            error_msg = f"Sorry, I couldn't get the weather information: {str(weather_error)}"
                            self.callback_queue.put(lambda: self.add_to_chat(error_msg, is_user=False))
                            return
                
                # Get response from chat service
                response = self.chat_service.get_response(message)
                self.callback_queue.put(lambda: self.add_to_chat(response, is_user=False))
                
            except Exception as e:
                error_msg = f"Error processing message: {str(e)}"
                self.callback_queue.put(lambda: self.add_to_chat(error_msg, is_user=False))
            finally:
                self.callback_queue.put(lambda: self.update_status("Ready"))

        Thread(target=process_message, daemon=True).start()
        
    def show_system_health(self):
        """Show system health information"""
        try:
            health_info = get_system_health()
            self.display_system_info("System Health", health_info)
        except Exception as e:
            self.add_to_chat(f"Error getting system health: {str(e)}", is_user=False)

    def show_processes(self):
        """Show running processes"""
        try:
            processes = get_process_info()
            self.display_system_info("Running Processes", processes)
        except Exception as e:
            self.add_to_chat(f"Error getting process info: {str(e)}", is_user=False)

    def show_network_info(self):
        """Show network information"""
        try:
            network_info = get_network_info()
            self.display_system_info("Network Information", network_info)
        except Exception as e:
            self.add_to_chat(f"Error getting network info: {str(e)}", is_user=False)

    def show_devices(self):
        """Show connected devices"""
        try:
            devices = get_system_devices()
            self.display_system_info("Connected Devices", devices)
        except Exception as e:
            self.add_to_chat(f"Error getting device info: {str(e)}", is_user=False)

    def show_env_info(self):
        """Show environment information"""
        try:
            info = get_environment_info()
            self.display_system_info("Environment Information", info)
        except Exception as e:
            self.add_to_chat(f"Error getting environment info: {str(e)}", is_user=False)

    def display_system_info(self, title, info):
        """Display system information in a well-formatted way"""
        if info is None:
            self.add_to_chat(f"Unable to get {title.lower()} information.", is_user=False)
            return

        response = f"{title}:\n\n"

        if title == "System Health":
            # CPU Information
            response += "CPU:\n"
            if 'cpu' in info:
                response += f"  Usage: {info['cpu']['usage']}%\n"
                if info['cpu']['temperature']:
                    response += f"  Temperature: {info['cpu']['temperature']}°C\n"
            response += "\n"
            
            # Memory Information
            if 'memory' in info:
                mem = info['memory']
                total_gb = mem['total'] / (1024 ** 3)
                used_gb = mem['used'] / (1024 ** 3)
                avail_gb = mem['available'] / (1024 ** 3)
                response += "Memory:\n"
                response += f"  Total: {total_gb:.1f} GB\n"
                response += f"  Used: {used_gb:.1f} GB ({mem['percent']}%)\n"
                response += f"  Available: {avail_gb:.1f} GB\n\n"
            
            # Disk Information
            if 'disks' in info:
                response += "Storage:\n"
                for disk in info['disks']:
                    total_gb = disk['total'] / (1024**3)
                    used_gb = disk['used'] / (1024**3)
                    free_gb = disk['free'] / (1024**3)
                    response += f"  {disk['device']} ({disk['fstype']}):\n"
                    response += f"    Total: {total_gb:.1f} GB\n"
                    response += f"    Used: {used_gb:.1f} GB ({disk['percent']}%)\n"
                    response += f"    Free: {free_gb:.1f} GB\n"
                response += "\n"
            
            # Battery Information
            if info.get('battery'):
                response += "Battery:\n"
                response += f"  Level: {info['battery']['percent']}%\n"
                response += f"  Power: {'Plugged In' if info['battery']['power_plugged'] else 'On Battery'}\n"
                if info['battery']['time_left'] != "Unknown":
                    response += f"  Time Left: {info['battery']['time_left']}\n"

        elif title == "Running Processes":
            response += "Top processes by CPU usage:\n\n"
            if isinstance(info, list):
                for proc in info[:20]:  # Show top 20 processes
                    response += f"PID: {proc['pid']:<6} | CPU: {proc['cpu_percent']:>5.1f}% | RAM: {proc['memory_info']:>8} | {proc['name']}\n"

        elif title == "Network Information":
            if 'interfaces' in info:
                response += "Network Interfaces:\n"
                for interface in info['interfaces']:
                    response += f"\n  {interface['name']}:\n"
                    for addr in interface['addresses']:
                        response += f"    IP: {addr['ip']}\n"
                        response += f"    Netmask: {addr['netmask']}\n"
                        if addr['broadcast']:
                            response += f"    Broadcast: {addr['broadcast']}\n"
                response += "\n"

            if 'connections' in info:
                response += "Active Network Connections:\n"
                # Group connections by status
                status_groups = {}
                for conn in info['connections']:
                    status = conn['status']
                    if status not in status_groups:
                        status_groups[status] = []
                    status_groups[status].append(conn)
                
                for status, conns in sorted(status_groups.items()):
                    response += f"\n  {status}:\n"
                    for conn in conns:
                        response += f"    {conn['name']} (PID: {conn['pid']}) - {conn['type']} Port {conn['port']}\n"

        elif title == "Connected Devices":
            if 'usb_devices' in info:
                response += "USB Devices:\n"
                for device in info['usb_devices']:
                    response += f"  • {device['name']}\n"
                    response += f"    Status: {device['status']}\n"
                response += "\n"
            
            if 'disk_drives' in info:
                response += "Disk Drives:\n"
                for drive in info['disk_drives']:
                    response += f"  • {drive['name']}\n"
                    if drive.get('size'):
                        size_gb = int(int(drive['size']) / (1024**3))
                        response += f"    Size: {size_gb} GB\n"
                    if drive.get('interface'):
                        response += f"    Interface: {drive['interface']}\n"
                response += "\n"
            
            if 'network_adapters' in info:
                response += "Network Adapters:\n"
                for adapter in info['network_adapters']:
                    response += f"  • {adapter['name']}\n"
                    if adapter.get('mac_address'):
                        response += f"    MAC: {adapter['mac_address']}\n"
                response += "\n"
            
            if 'monitors' in info:
                response += "Monitors:\n"
                for monitor in info['monitors']:
                    response += f"  • {monitor['name']}\n"
                    if monitor.get('screen_width') and monitor.get('screen_height'):
                        response += f"    Resolution: {monitor['screen_width']}x{monitor['screen_height']}\n"

        elif title == "Environment Information":
            if 'python' in info:
                response += "Python:\n"
                if 'version' in info['python']:
                    response += f"  Version: {info['python']['version']}\n"
                if 'packages' in info['python']:
                    response += "  Key Packages:\n"
                    for pkg, ver in info['python']['packages'].items():
                        response += f"    {pkg}: {ver}\n"
                response += "\n"
            
            if 'system' in info:
                response += "System:\n"
                for key, value in info['system'].items():
                    response += f"  {key.replace('_', ' ').title()}: {value}\n"
                response += "\n"
            
            if 'environment' in info and info['environment']:
                response += "Environment Variables:\n"
                for var, value in info['environment'].items():
                    response += f"  {var}: {value}\n"

        else:
            # Generic dictionary handling for unknown types
            if isinstance(info, dict):
                for key, value in info.items():
                    if isinstance(value, dict):
                        response += f"{key}:\n"
                        for subkey, subvalue in value.items():
                            response += f"  {subkey}: {subvalue}\n"
                    else:
                        response += f"{key}: {value}\n"
            elif isinstance(info, list):
                for item in info:
                    response += f"- {item}\n"
            else:
                response += str(info)

        self.add_to_chat(response, is_user=False)
    
    def run_speed_test(self):
        """Run an internet speed test"""
        self.add_to_chat("Running speed test... This may take a minute.", is_user=False)
        
        def run_test():
            try:
                # Run speedtest using speedtest-cli
                import speedtest
                
                # Create speedtest instance
                st = speedtest.Speedtest()
                
                # Get best server
                self.add_to_chat("Finding best server...", is_user=False)
                st.get_best_server()
                
                # Test download speed
                self.add_to_chat("Testing download speed...", is_user=False)
                download_speed = st.download() / 1_000_000  # Convert to Mbps
                
                # Test upload speed
                self.add_to_chat("Testing upload speed...", is_user=False)
                upload_speed = st.upload() / 1_000_000  # Convert to Mbps
                
                # Get ping
                ping = st.results.ping
                
                # Format results
                results = (
                    "Speed Test Results:\n\n"
                    f"Download Speed: {download_speed:.2f} Mbps\n"
                    f"Upload Speed: {upload_speed:.2f} Mbps\n"
                    f"Ping: {ping:.2f} ms"
                )
                
                self.add_to_chat(results, is_user=False)
                
            except ImportError:
                self.add_to_chat("speedtest-cli package not found. Installing...", is_user=False)
                try:
                    import subprocess
                    subprocess.check_call([sys.executable, "-m", "pip", "install", "speedtest-cli"])
                    self.add_to_chat("speedtest-cli installed. Please try the speed test again.", is_user=False)
                except Exception as e:
                    self.add_to_chat(f"Error installing speedtest-cli: {str(e)}", is_user=False)
                    
            except Exception as e:
                self.add_to_chat(f"Error running speed test: {str(e)}", is_user=False)
        
        # Start the speed test in a new thread
        Thread(target=run_test, daemon=True).start()
    
    def analyze_code(self):
        """Analyze code in a file or directory"""
        self.add_to_chat("/analyze", is_user=True)
        
        # Create a dialog window for input
        dialog = tk.Toplevel()
        dialog.title("Code Analysis")
        dialog.geometry("400x200")
        dialog.transient(self.winfo_toplevel())  # Make dialog modal
        
        # Center the dialog
        dialog.geometry("+%d+%d" % (
            self.winfo_toplevel().winfo_rootx() + 50,
            self.winfo_toplevel().winfo_rooty() + 50))
        
        # Configure dialog style
        dialog.configure(bg=THEME.colors['background'])
        
        # Add explanation label
        ttk.Label(dialog, text="Choose what to analyze:", style='Default.TLabel').pack(pady=10)
        
        # Create radio buttons for choice
        choice_var = tk.StringVar(value="file")
        ttk.Radiobutton(dialog, text="Single File", value="file", variable=choice_var).pack()
        ttk.Radiobutton(dialog, text="Directory", value="directory", variable=choice_var).pack()
        
        # Path entry
        path_frame = ttk.Frame(dialog)
        path_frame.pack(fill='x', padx=20, pady=10)
        
        path_var = tk.StringVar()
        path_entry = ttk.Entry(path_frame, textvariable=path_var)
        path_entry.pack(side='left', fill='x', expand=True)
        
        def browse():
            if choice_var.get() == "file":
                path = filedialog.askopenfilename(
                    title="Select File to Analyze",
                    initialdir='/',
                    filetypes=[
                        ("Code Files", "*.py;*.js;*.java;*.cpp;*.c;*.h;*.cs;*.php;*.rb;*.go"),
                        ("All Files", "*.*")
                    ]
                )
            else:
                path = filedialog.askdirectory(
                    title="Select Directory to Analyze"
                )
            if path:
                path_var.set(path)
        
        browse_btn = ttk.Button(path_frame, text="Browse", command=browse)
        browse_btn.pack(side='right', padx=(5, 0))
        
        def analyze():
            path = path_var.get().strip()
            if not path:
                self.add_to_chat("Please select a path to analyze.", is_user=False)
                dialog.destroy()
                return
                
            dialog.destroy()
            self.update_status("Analyzing code...")
            
            if choice_var.get() == "file":
                analysis = FileService.analyze_code_file(path)
                if analysis:
                    message = f"Analysis of {analysis['filename']}:\n\n"
                    
                    # File info
                    message += "File Information:\n"
                    message += f"  Type: {analysis['extension']}\n"
                    message += f"  Size: {FileService.format_size(analysis['size'])}\n\n"
                    
                    # Line counts
                    message += "Line Statistics:\n"
                    message += f"  Total Lines: {analysis['lines']['total']}\n"
                    message += f"  Code Lines: {analysis['lines']['code']}\n"
                    message += f"  Comment Lines: {analysis['lines']['comments']}\n"
                    message += f"  Blank Lines: {analysis['lines']['blank']}\n\n"
                    
                    # Functions
                    if analysis['functions']:
                        message += f"Functions Found: {len(analysis['functions'])}\n"
                        message += "Top Functions by Complexity:\n"
                        sorted_funcs = sorted(analysis['functions'], 
                                           key=lambda x: x.get('complexity', 0), 
                                           reverse=True)[:5]
                        for func in sorted_funcs:
                            message += f"  • {func.get('name', 'Unknown')}"
                            if 'complexity' in func:
                                message += f" (Complexity: {func['complexity']})"
                            message += "\n"
                        message += "\n"
                    
                    # Classes
                    if analysis['classes']:
                        message += f"Classes Found: {len(analysis['classes'])}\n"
                        for cls in analysis['classes']:
                            message += f"  • {cls.get('name', 'Unknown')}"
                            methods = cls.get('methods', [])
                            if methods:
                                message += f" ({len(methods)} methods)"
                            message += "\n"
                        message += "\n"
                    
                    # TODOs
                    if analysis['todos']:
                        message += "TODOs Found:\n"
                        for todo in analysis['todos']:
                            message += f"  • Line {todo.get('line', '?')}: {todo.get('content', '')}\n"
                    
                else:
                    message = f"Unable to analyze file: {path}"
            else:
                analysis = FileService.analyze_code_directory(path)
                if analysis:
                    message = f"Analysis of directory: {analysis['directory']}\n\n"
                    
                    # File Statistics
                    message += "File Statistics:\n"
                    message += f"  Total Files: {analysis['files']['total']}\n"
                    if analysis['files']['by_type']:
                        message += "  File Types:\n"
                        for ext, count in analysis['files']['by_type'].items():
                            message += f"    {ext}: {count} files\n"
                    message += "\n"
                    
                    # Line Statistics
                    message += "Line Statistics:\n"
                    message += f"  Total Lines: {analysis['lines']['total']}\n"
                    message += f"  Code Lines: {analysis['lines']['code']}\n"
                    message += f"  Comment Lines: {analysis['lines']['comments']}\n"
                    message += f"  Blank Lines: {analysis['lines']['blank']}\n\n"
                    
                    # Functions
                    if analysis['functions']:
                        message += f"Functions Found: {len(analysis['functions'])}\n"
                        message += "Top Functions by Complexity:\n"
                        sorted_funcs = sorted(analysis['functions'], 
                                           key=lambda x: x.get('complexity', 0), 
                                           reverse=True)[:5]
                        for func in sorted_funcs:
                            message += f"  • {func.get('name', 'Unknown')} in {func.get('file', 'Unknown')}"
                            if 'complexity' in func:
                                message += f" (Complexity: {func['complexity']})"
                            message += "\n"
                        message += "\n"
                    
                    # Classes
                    if analysis['classes']:
                        message += f"Classes Found: {len(analysis['classes'])}\n"
                        message += "Top Classes by Methods:\n"
                        sorted_classes = sorted(analysis['classes'], 
                                             key=lambda x: len(x.get('methods', [])), 
                                             reverse=True)[:5]
                        for cls in sorted_classes:
                            message += f"  • {cls.get('name', 'Unknown')} in {cls.get('file', 'Unknown')}"
                            methods = cls.get('methods', [])
                            if methods:
                                message += f" ({len(methods)} methods)"
                            message += "\n"
                        message += "\n"
                    
                    # TODOs
                    if analysis['todos']:
                        message += "TODOs Found:\n"
                        for todo in analysis['todos'][:5]:  # Show first 5 TODOs
                            message += f"  • {todo.get('file', 'Unknown')}:{todo.get('line', '?')}\n"
                            message += f"    {todo.get('content', '')}\n"
                else:
                    message = f"Unable to analyze directory: {path}"
            
            self.add_to_chat(message, is_user=False)
            self.update_status("Ready")
        
        # Add analyze button
        ttk.Button(dialog, text="Analyze", command=analyze).pack(pady=10)
        
        # Make dialog modal
        dialog.grab_set()
        dialog.focus_set()
        dialog.wait_window()
    
    def show_git_status(self):
        """Show git status"""
        self.add_to_chat("/git", is_user=True)
        status = FileService.check_git_status()
        if status:
            response = "Git Repository Status:\n\n"

            if status['branch']:
                response += f"Current branch: {status['branch']}\n\n"
            
            if status['changes']:
                response += "Changes:\n"
                for change in status['changes']:
                    response += f"  {change}\n"
            else:
                response += "Working tree clean\n"
            
            if status['untracked']:
                response += "\nUntracked files:\n"
                for file in status['untracked']:
                    response += f"  {file}\n"
            
            if status['remotes']:
                response += "\nRemotes:\n"
                for remote in status['remotes']:
                    response += f"  {remote}\n"
        else:
            response = "Not a git repository or unable to get status."
        self.add_to_chat(response, is_user=False)
    
    def show_dev_servers(self):
        """Show running development servers"""
        self.add_to_chat("/servers", is_user=True)
        servers = FileService.find_development_servers()
        if servers:
            response = "Running Development Servers:\n\n"
            for server in servers:
                response += f"• {server['process_name']} (PID: {server['pid']})\n"
                if 'local_address' in server:
                    response += f"  Address: {server['local_address']}\n"
                if 'status' in server:
                    response += f"  Status: {server['status']}\n"
                response += "\n"
        else:
            response = "No development servers currently running."
        self.add_to_chat(response, is_user=False)
    
    def toggle_theme(self):
        """Toggle between light and dark theme"""
        # TODO: Implement theme toggling
        pass

    def update_status(self, message: str):
        """Update the status bar message"""
        if hasattr(self, 'status_bar'):
            self.status_bar.config(text=message)
            self.master.update_idletasks()

    def on_persona_change(self, event):
        """Handle persona change"""
        persona = self.persona_var.get()
        self.persona_service.set_persona(persona)
        self.add_to_chat(f"Switched to {persona} persona", is_user=False)

    def toggle_voice(self):
        """Toggle voice input/output"""
        if self.voice_var.get():
            self.voice_service.start_listening(self.on_voice_input)
            self.add_to_chat("Voice input enabled", is_user=False)
        else:
            self.voice_service.stop_listening()
            self.add_to_chat("Voice input disabled", is_user=False)

    def on_voice_input(self, text):
        """Handle voice input"""
        if text:
            self.input_field.delete("1.0", tk.END)
            self.input_field.insert("1.0", text)
            self.send_message()

    def show_snippets(self):
        """Show code snippets dialog"""
        dialog = tk.Toplevel(self)
        dialog.title("Code Snippets")
        dialog.geometry("600x400")
        
        # Create snippet list
        listbox = tk.Listbox(dialog, width=50)
        listbox.pack(fill="both", expand=True, padx=5, pady=5)
        
        for snippet in self.snippet_service.get_snippets():
            listbox.insert(tk.END, f"{snippet['title']} ({snippet['language']})")
            
        def insert_snippet():
            selection = listbox.curselection()
            if selection:
                snippet = self.snippet_service.get_snippets()[selection[0]]
                self.input_field.insert(tk.END, snippet['code'])
                dialog.destroy()
                
        ttk.Button(dialog, text="Insert", command=insert_snippet).pack(pady=5)

    def show_summary(self):
        """Show conversation summary dialog"""
        summary = self.summarization_service.summarize_conversation(
            self.conversation_history)
        
        dialog = tk.Toplevel(self)
        dialog.title("Conversation Summary")
        dialog.geometry("600x400")
        
        text = ScrolledText(dialog)
        text.pack(fill="both", expand=True, padx=5, pady=5)
        text.insert(tk.END, summary)
        text.configure(state="disabled")

    def show_plugins(self):
        """Show plugins dialog"""
        dialog = tk.Toplevel(self)
        dialog.title("Plugins")
        dialog.geometry("600x400")
        
        # Create plugin list
        for name, plugin in self.plugin_service.get_plugins().items():
            frame = ttk.LabelFrame(dialog, text=name)
            frame.pack(fill="x", padx=5, pady=5)
            
            ttk.Label(frame, text=plugin.description).pack(anchor="w")
            
            for cmd_name, cmd in plugin.commands.items():
                ttk.Button(frame, text=cmd_name,
                          command=lambda p=name, c=cmd_name: 
                          self.execute_plugin(p, c)).pack(side="left", padx=2)

    def execute_plugin(self, plugin_name, command):
        """Execute a plugin command"""
        try:
            result = self.plugin_service.execute_command(plugin_name, command)
            self.add_to_chat(f"Plugin result: {result}", is_user=False)
        except Exception as e:
            self.add_to_chat(f"Plugin error: {str(e)}", is_user=False)

    def clean_temp_files(self):
        """Clean temporary files"""
        try:
            self.add_to_chat("/clean", is_user=True)
            result = FileService.clean_system()
            if result:
                response = "System Cleanup Results:\n\n"
                total_cleaned = 0
                for location, info in result.items():
                    if info['cleaned'] > 0:
                        response += f"{location}:\n"
                        response += f"  Files removed: {info['cleaned']}\n"
                        response += f"  Space freed: {info['space_freed']}\n\n"
                        total_cleaned += info['cleaned']
                if total_cleaned > 0:
                    response += f"\nTotal files cleaned: {total_cleaned}"
                else:
                    response = "No files needed cleaning."
            else:
                response = "Unable to perform system cleanup."
            self.add_to_chat(response, is_user=False)
        except Exception as e:
            self.add_to_chat(f"Error cleaning temporary files: {str(e)}", is_user=False)

    def process_message(self, message):
        """Process the message and generate appropriate response."""
        try:
            # Check for commands first
            if message.startswith('/'):
                if self.handle_command(message):
                    return
            
            # Check for weather-related queries
            weather_patterns = [
                r'weather (?:in|at|for)? ?(.+)',
                r'what\'s the weather (?:like )?(?:in|at|for)? ?(.+)?',
                r'how\'s the weather (?:in|at|for)? ?(.+)?',
                r'temperature (?:in|at|for)? ?(.+)',
                r'current weather',
                r'weather'
            ]
            
            for pattern in weather_patterns:
                match = re.search(pattern, message.lower())
                if match:
                    try:
                        city = match.group(1) if match.groups() and match.group(1) else "Boston"
                        weather_data = self.realtime_service.get_weather(city)
                        response = (
                            f"🌤️ Weather in {weather_data['location']} as of {weather_data['timestamp']}:\n"
                            f"Temperature: {weather_data['temperature']}°F (Feels like {weather_data['feels_like']}°F)\n"
                            f"Condition: {weather_data['description']}\n"
                            f"Humidity: {weather_data['humidity']}%\n"
                            f"Wind Speed: {weather_data['wind_speed']} mph"
                        )
                        self.add_to_chat(response, is_user=False)
                        return
                    except Exception as e:
                        self.add_to_chat(f"Error getting weather: {str(e)}", is_user=False)
                        return
            
            # Get conversation history
            history = self.get_conversation_history()
            
            # Get response from chat service
            response = self.chat_service.get_response(message, history)
            
            # Add response to chat
            self.add_to_chat(response, is_user=False)
            
            # Save to memory if important
            if self.chat_service.is_important(message, response):
                save_memory(message, response)
                
        except Exception as e:
            self.add_to_chat(f"Error: {str(e)}", is_user=False)
            
    def get_conversation_history(self) -> List[Dict]:
        """Get the conversation history in a format suitable for the chat service"""
        history = []
        # Get messages from the chat display
        text = self.chat_display.get("1.0", tk.END)
        messages = text.split("\n")
        
        for msg in messages:
            msg = msg.strip()
            if msg:
                # Check if it's a user message (starts with "You: ")
                if msg.startswith("You: "):
                    history.append({
                        'role': 'user',
                        'content': msg[5:].strip()  # Remove "You: " prefix
                    })
                # Check if it's an assistant message (starts with "Assistant: ")
                elif msg.startswith("Assistant: "):
                    history.append({
                        'role': 'assistant',
                        'content': msg[11:].strip()  # Remove "Assistant: " prefix
                    })
        
        # Return last 5 messages for context
        return history[-5:] if history else []

    def setup_file_monitoring(self):
        """Set up resilient file monitoring that auto-restarts on errors"""
        try:
            if self.directory_monitor:
                self.directory_monitor.stop()
            
            directory = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            self.directory_monitor = self.file_service.DirectoryMonitor(directory, self.handle_file_change)
            self.directory_monitor.start()
            
            # Start monitoring checker thread
            Thread(target=self.check_monitoring, daemon=True).start()
            
        except Exception as e:
            print(f"Error setting up file monitoring: {e}")
            # Retry after delay
            self.after(5000, self.setup_file_monitoring)
    
    def check_monitoring(self):
        """Continuously check monitoring status and restart if needed"""
        while True:
            try:
                if not self.directory_monitor or not self.directory_monitor.is_monitoring:
                    print("File monitoring stopped, restarting...")
                    self.setup_file_monitoring()
                time.sleep(5)  # Check every 5 seconds
            except Exception as e:
                print(f"Error in monitoring checker: {e}")
                time.sleep(5)  # Wait before retrying
    
    def handle_file_change(self, event_type, file_path):
        """Handle file system events"""
        try:
            if event_type == 'created':
                # New file created
                filename = os.path.basename(file_path)
                self.add_to_chat(f"New file detected: {filename}", is_user=False)
            elif event_type == 'modified':
                # File modified
                filename = os.path.basename(file_path)
                self.add_to_chat(f"File modified: {filename}", is_user=False)
            elif event_type == 'deleted':
                # File deleted
                filename = os.path.basename(file_path)
                self.add_to_chat(f"File removed: {filename}", is_user=False)
        except Exception as e:
            logging.error(f"Error handling file change: {e}")

    def on_file_change(self, event_type, file_path):
        """Handle file changes in monitored directories"""
        try:
            # Only handle image files
            if not file_path.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.bmp')):
                return
                
            # Get just the filename
            filename = os.path.basename(file_path)
            
            # Only log new files, not modifications
            if event_type == 'created':
                logging.info(f"New screenshot detected: {filename}")
            
        except Exception as e:
            logging.error(f"Error handling file change: {e}")

    def on_closing(self):
        """Clean up resources before closing."""
        try:
            # Stop RSS service
            if hasattr(self, 'rss_service'):
                self.rss_service.stop_auto_update()
                
            # Clean up other services
            if hasattr(self, 'voice_service'):
                self.voice_service.cleanup()
            if hasattr(self, 'file_service'):
                self.file_service.stop_monitoring()
            
            # Save any pending data
            self.save_chat()
            
            # Clean up temporary files
            self.clean_temp_files()
            
            # Destroy the window
            if self.master:
                self.master.destroy()
            
        except Exception as e:
            logging.error(f"Error during cleanup: {str(e)}")
            
        finally:
            # Destroy the window
            if self.master:
                self.master.destroy()

    def toggle_voice_input(self):
        """Toggle voice input on/off"""
        try:
            if hasattr(self, 'voice_service'):
                if self.voice_service.is_listening:
                    self.stop_voice_input()
                    self.voice_button.configure(style='Toolbar.TButton')
                else:
                    self.start_voice_input()
                    self.voice_button.configure(style='Active.Toolbar.TButton')
        except Exception as e:
            self.add_to_chat(f"Error toggling voice input: {str(e)}", is_user=False)

    def start_voice_input(self):
        """Start voice input recording"""
        try:
            if hasattr(self, 'voice_service'):
                self.voice_service.start_listening(self.on_voice_input)
        except Exception as e:
            self.add_to_chat(f"Error starting voice input: {str(e)}", is_user=False)

    def stop_voice_input(self):
        """Stop voice input recording"""
        try:
            if hasattr(self, 'voice_service'):
                self.voice_service.stop_listening()
                logging.error(f"Error stopping voice input: {e}")
        except Exception as e:
            logging.error(f"Error stopping voice input: {e}")

    def upload_file(self):
        """Handle file upload"""
        filetypes = (
            ('All files', '*.*'),
            ('Text files', '*.txt'),
            ('Python files', '*.py'),
            ('Image files', '*.png *.jpg *.jpeg *.gif *.bmp'),
            ('Document files', '*.pdf *.doc *.docx')
        )
        
        filename = filedialog.askopenfilename(
            title='Select a file to analyze',
            initialdir='/',
            filetypes=filetypes
        )
        
        if filename:
            # Create uploads directory if it doesn't exist
            os.makedirs('uploaded_files', exist_ok=True)
            
            # Copy file to uploads directory
            base_name = os.path.basename(filename)
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_')
            new_filename = os.path.join('uploaded_files', timestamp + base_name)
            
            try:
                import shutil
                shutil.copy2(filename, new_filename)
                
                # Check file type and process accordingly
                _, ext = os.path.splitext(filename)
                ext = ext.lower()
                
                if ext in ['.png', '.jpg', '.jpeg', '.gif', '.bmp']:
                    self.analyze_image_full(new_filename)
                elif ext in ['.txt', '.py', '.md', '.json', '.yaml', '.yml']:
                    self.analyze_text_file(new_filename)
                elif ext in ['.pdf', '.doc', '.docx']:
                    self.analyze_document(new_filename)
                else:
                    self.add_to_chat(f"I'll take a look at {base_name}", is_user=False)
                    self.analyze_generic_file(new_filename)
                    
            except Exception as e:
                self.add_to_chat(f"Error processing file: {str(e)}", is_user=False)
    
    def take_screenshot(self):
        """Take and analyze a screenshot"""
        try:
            # Create screenshots directory if it doesn't exist
            os.makedirs('screenshots', exist_ok=True)
            
            # Generate filename with timestamp
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = os.path.join('screenshots', f'screenshot_{timestamp}.png')
            
            # Take screenshot
            self.screen_monitor.take_screenshot(filename)
            
            # Analyze the screenshot
            self.analyze_image_full(filename)
            
        except Exception as e:
            self.add_to_chat(f"Error taking screenshot: {str(e)}", is_user=False)
    
    def open_settings(self):
        """Open settings dialog"""
        # Create settings window
        settings_window = tk.Toplevel(self)
        settings_window.title("Settings")
        settings_window.geometry("400x500")
        settings_window.transient(self)
        settings_window.grab_set()
        
        # Add settings content
        ttk.Label(
            settings_window,
            text="Settings",
            font=('Segoe UI', 16, 'bold')
        ).pack(pady=10)
        
        # Create notebook for settings categories
        notebook = ttk.Notebook(settings_window)
        notebook.pack(fill='both', expand=True, padx=10, pady=5)
        
        # General settings
        general_frame = ttk.Frame(notebook)
        notebook.add(general_frame, text="General")
        
        # Voice settings
        voice_frame = ttk.Frame(notebook)
        notebook.add(voice_frame, text="Voice")
        
        # Theme settings
        theme_frame = ttk.Frame(notebook)
        notebook.add(theme_frame, text="Theme")
        
        # Add some basic settings
        ttk.Label(
            general_frame,
            text="Coming soon...",
            font=('Segoe UI', 10)
        ).pack(pady=20)

    def create_tooltip(self, widget, text):
        """Create a tooltip for a widget"""
        def show_tooltip(event=None):
            tooltip = tk.Toplevel()
            tooltip.wm_overrideredirect(True)
            tooltip.wm_geometry(f"+{event.x_root+10}+{event.y_root+10}")
            
            # Configure tooltip style
            tooltip.configure(bg=THEME.colors['tooltip_bg'])
            
            # Create label
            label = ttk.Label(
                tooltip,
                text=text,
                background=THEME.colors['tooltip_bg'],
                foreground=THEME.colors['tooltip_fg'],
                relief='solid',
                borderwidth=1,
                padding=(5, 2)
            )
            label.pack()
            
            def hide_tooltip():
                tooltip.destroy()
            
            # Auto-hide after 2 seconds
            tooltip.after(2000, hide_tooltip)
            widget.tooltip = tooltip
        
        def enter(event):
            show_tooltip(event)
        
        def leave(event):
            if hasattr(widget, 'tooltip'):
                widget.tooltip.destroy()
                del widget.tooltip
        
        widget.bind('<Enter>', enter)
        widget.bind('<Leave>', leave)

    def show_memory(self):
        """Show memory usage"""
        try:
            memory_info = self.file_service.get_memory_info()
            self.display_system_info("Memory Information", memory_info)
        except Exception as e:
            self.add_to_chat(f"Error getting memory info: {str(e)}", is_user=False)

    def process_message(self):
        """Process the message in the input field."""
        try:
            message = self.input_field.get("1.0", "end-1c").strip()
            if not message:
                return
                
            # Clear input field
            self.input_field.delete("1.0", tk.END)
            
            # Add user message to chat
            self.add_to_chat(message, is_user=True)
            
            # Get conversation history for context
            history = self.get_conversation_history()
            
            # Process through chat service
            response = self.chat_service.get_response(message, history)
            
            # Add assistant response to chat
            if response:
                self.add_to_chat(response, is_user=False)
                
                # Use voice if enabled
                if self.voice_service and self.voice_service.is_enabled():
                    self.voice_service.speak(response)
            
            # Save chat
            self.save_chat()
            
        except Exception as e:
            logging.error(f"Error processing message: {e}")
            self.add_to_chat(f"I encountered an error: {str(e)}", is_user=False)

    def toggle_voice_input(self):
        """Toggle voice input on/off"""
        try:
            if not self.voice_service.is_recording():
                self.start_voice_input()
            else:
                self.stop_voice_input()
        except Exception as e:
            logging.error(f"Error toggling voice input: {e}")
            self.add_to_chat("Error with voice input. Please try again.", is_user=False)

    def start_voice_input(self):
        """Start voice input recording"""
        try:
            self.voice_service.start_recording(callback=self.on_voice_input)
            self.update_status("Listening...")
        except Exception as e:
            logging.error(f"Error starting voice input: {e}")
            self.add_to_chat("Could not start voice input. Please try again.", is_user=False)

    def stop_voice_input(self):
        """Stop voice input recording"""
        try:
            self.voice_service.stop_recording()
            self.update_status("Voice input stopped")
        except Exception as e:
            logging.error(f"Error stopping voice input: {e}")

    def clear_chat(self):
        """Clear the chat display"""
        self.chat_display.configure(state='normal')
        self.chat_display.delete("1.0", tk.END)
        self.conversation_history.clear()
        self.chat_display.configure(state='disabled')

    def save_chat(self):
        """Save the chat history to a file"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            filename = f"chat_history_{timestamp}.txt"
            
            with open(filename, 'w', encoding='utf-8') as f:
                chat_content = self.chat_display.get("1.0", tk.END)
                f.write(chat_content)
            
            self.add_to_chat(f"Chat saved to {filename}", is_user=False)
            self.update_status("Chat saved successfully")
            
        except Exception as e:
            self.add_to_chat(f"Error saving chat: {str(e)}", is_user=False)
            self.update_status("Error saving chat")

    def add_to_chat(self, message, is_user=True):
        """Add a message to the chat display"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        # Store message in conversation history
        self.conversation_history.append({
            'message': message,
            'is_user': is_user,
            'timestamp': timestamp
        })
        
        # Format and display message
        display_name = "You: " if is_user else "Assistant: "
        self.chat_display.configure(state='normal')
        self.chat_display.insert(tk.END, f"[{timestamp}] ", "timestamp")
        self.chat_display.insert(tk.END, display_name, "name")
        self.chat_display.insert(tk.END, f"{message}\n", "user" if is_user else "assistant")
        self.chat_display.configure(state='disabled')
        self.chat_display.see(tk.END)
