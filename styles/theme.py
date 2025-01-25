import tkinter as tk
from tkinter import ttk

class Theme:
    def __init__(self):
        self.colors = {
            'background': '#1e1e1e',
            'text': '#ffffff',
            'accent': '#007acc',
            'error': '#f44336',
            'comment': '#6a9955',
            'button': '#3c3c3c',
            'button_active': '#4c4c4c',
            'input_bg': '#3c3c3c',
            'input_fg': '#ffffff',
            'scrollbar': '#3c3c3c',
            'scrollbar_active': '#4c4c4c',
            'tooltip_bg': '#2d2d2d',
            'tooltip_fg': '#ffffff',
            'link': '#0078d4'
        }
    
    def get_scrollbar_style(self):
        """Get scrollbar style configuration"""
        return {
            'background': self.colors['scrollbar'],
            'troughcolor': self.colors['background'],
            'bordercolor': self.colors['background'],
            'arrowcolor': self.colors['text'],
            'relief': 'flat'
        }

THEME = Theme()

def apply_dark_theme(root):
    """Apply dark theme to the application"""
    style = ttk.Style(root)
    style.theme_use('clam')
    
    # Configure colors
    colors = {
        'bg': THEME.colors['background'],
        'fg': THEME.colors['text'],
        'select_bg': THEME.colors['accent'],
        'select_fg': THEME.colors['text'],
        'button': THEME.colors['button'],
        'button_active': THEME.colors['button_active'],
        'input_bg': THEME.colors['input_bg'],
        'input_fg': THEME.colors['input_fg']
    }
    
    # Configure common styles
    style.configure(".",
                   background=colors['bg'],
                   foreground=colors['fg'],
                   selectbackground=colors['select_bg'],
                   selectforeground=colors['select_fg'])
    
    # Configure Button
    style.configure("Custom.TButton",
                   background=colors['button'],
                   foreground=colors['fg'],
                   padding=5,
                   relief='flat',
                   font=('Segoe UI', 9))
    style.map("Custom.TButton",
             background=[('active', colors['button_active'])],
             foreground=[('active', colors['fg'])])
    
    # Configure Entry
    style.configure("Custom.TEntry",
                   fieldbackground=colors['input_bg'],
                   foreground=colors['input_fg'],
                   padding=5,
                   relief='flat',
                   font=('Segoe UI', 10))
    
    # Configure Frame styles
    style.configure("Main.TFrame",
                   background=colors['bg'])
    
    style.configure("Sidebar.TFrame",
                   background=colors['bg'])
    
    style.configure("Content.TFrame",
                   background=colors['bg'])
    
    style.configure("Chat.TFrame",
                   background=colors['bg'])
    
    style.configure("Input.TFrame",
                   background=colors['bg'])
    
    # Configure Label styles
    style.configure("TLabel",
                   background=colors['bg'],
                   foreground=colors['fg'],
                   font=('Segoe UI', 10))
    
    style.configure("Status.TLabel",
                   background=colors['bg'],
                   foreground=colors['fg'],
                   font=('Segoe UI', 9))
    
    # Configure Scrollbar
    style.configure("Custom.Vertical.TScrollbar",
                   background=THEME.colors['scrollbar'],
                   troughcolor=colors['bg'],
                   bordercolor=colors['bg'],
                   arrowcolor=colors['fg'],
                   relief='flat')
    style.map("Custom.Vertical.TScrollbar",
             background=[('active', THEME.colors['scrollbar_active'])])
    
    # Configure root window
    root.configure(bg=colors['bg'])
    
    return style

def apply_dark_theme(style):
    """Apply dark theme styles"""
    style.configure('Main.TFrame', background=THEME.colors['background'])
    style.configure('Sidebar.TFrame', background=THEME.colors['background'])
    style.configure('Custom.TButton',
                   background=THEME.colors['button'],
                   foreground=THEME.colors['text'])
    style.configure('Status.TLabel',
                   background=THEME.colors['background'],
                   foreground=THEME.colors['text'])
    style.configure('TEntry',
                   fieldbackground=THEME.colors['input_bg'],
                   foreground=THEME.colors['text'])
    style.configure('Chat.TFrame',
                   background=THEME.colors['background'])

def apply_light_theme(style):
    """Apply light theme styles"""
    style.configure('Main.TFrame', background=THEME.colors['background'])
    style.configure('Sidebar.TFrame', background=THEME.colors['background'])
    style.configure('Custom.TButton',
                   background=THEME.colors['button'],
                   foreground=THEME.colors['text'])
    style.configure('Status.TLabel',
                   background=THEME.colors['background'],
                   foreground=THEME.colors['text'])
    style.configure('TEntry',
                   fieldbackground=THEME.colors['input_bg'],
                   foreground=THEME.colors['text'])
    style.configure('Chat.TFrame',
                   background=THEME.colors['background'])
