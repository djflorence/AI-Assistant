"""Task panel for showing running tasks."""
import tkinter as tk
from tkinter import ttk
from typing import Dict, Optional
import time
from dataclasses import dataclass
from enum import Enum

class TaskStatus(Enum):
    """Possible states for a task."""
    RUNNING = 'running'
    DONE = 'done'
    ERROR = 'error'

@dataclass
class TaskInfo:
    """Information about a task."""
    task_type: str
    status: TaskStatus
    details: Optional[str] = None
    result: Optional[str] = None
    start_time: float = time.time()

class TaskPanel(ttk.Frame):
    """Panel showing current tasks and their status."""
    
    def __init__(self, master, config: dict):
        """Initialize the task panel.
        
        Args:
            master: The parent widget
            config: Configuration dictionary
        """
        super().__init__(master)
        self.config = config
        self.tasks: Dict[str, TaskInfo] = {}
        self.setup_ui()
    
    def setup_ui(self):
        """Set up the UI components."""
        # Create canvas and scrollbar
        self.canvas = tk.Canvas(
            self,
            background=self.config['interface']['theme'] == 'dark' and '#1E1E1E' or '#FFFFFF'
        )
        scrollbar = ttk.Scrollbar(
            self,
            orient='vertical',
            command=self.canvas.yview
        )
        
        # Create frame for tasks
        self.task_frame = ttk.Frame(self.canvas)
        self.task_frame.bind(
            '<Configure>',
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox('all'))
        )
        
        # Add task frame to canvas
        self.canvas.create_window((0, 0), window=self.task_frame, anchor='nw')
        self.canvas.configure(yscrollcommand=scrollbar.set)
        
        # Pack widgets
        self.canvas.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')
        
        # Bind mouse wheel
        self.canvas.bind_all('<MouseWheel>', self._on_mousewheel)
    
    def add_task(self, task_id: str, task_type: str, details: Optional[str] = None):
        """Add a new task to the panel.
        
        Args:
            task_id: Unique identifier for the task
            task_type: Type of task
            details: Optional task details
        """
        # Create task info
        task_info = TaskInfo(
            task_type=task_type,
            status=TaskStatus.RUNNING,
            details=details
        )
        self.tasks[task_id] = task_info
        
        # Create task frame
        task_frame = ttk.Frame(self.task_frame)
        task_frame.pack(fill='x', padx=5, pady=2)
        
        # Add task info
        ttk.Label(
            task_frame,
            text=f'{task_type}...',
            font=('Segoe UI', 9, 'bold')
        ).pack(side='left')
        
        if details:
            ttk.Label(
                task_frame,
                text=details,
                font=('Segoe UI', 9)
            ).pack(side='left', padx=5)
    
    def update_task(self, task_id: str, status: TaskStatus, result: Optional[str] = None):
        """Update task status and optionally show result.
        
        Args:
            task_id: Task identifier
            status: New task status
            result: Optional task result
        """
        if task_id in self.tasks:
            task = self.tasks[task_id]
            task.status = status
            task.result = result
            
            # Update UI
            # In a real implementation, we would update the task's display
            # For now, we'll just remove completed tasks after a delay
            if status != TaskStatus.RUNNING:
                self.after(5000, lambda: self.remove_task(task_id))
    
    def remove_task(self, task_id: str):
        """Remove a task from the panel.
        
        Args:
            task_id: Task identifier
        """
        if task_id in self.tasks:
            del self.tasks[task_id]
            # In a real implementation, we would remove the task's frame
    
    def _on_mousewheel(self, event):
        """Handle mouse wheel scrolling."""
        self.canvas.yview_scroll(-1 * (event.delta // 120), 'units')
