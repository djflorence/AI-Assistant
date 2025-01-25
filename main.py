import tkinter as tk
from src.core.chat_interface import ChatInterface
import logging
import sys

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    stream=sys.stdout
)

def main():
    logging.debug("Starting application...")
    try:
        root = tk.Tk()
        logging.debug("Created Tk root window")
        
        root.title("AI Assistant")
        logging.debug("Set window title")
        
        # Set window size and position
        window_width = 1200
        window_height = 800
        screen_width = root.winfo_screenwidth()
        screen_height = root.winfo_screenheight()
        center_x = int(screen_width/2 - window_width/2)
        center_y = int(screen_height/2 - window_height/2)
        root.geometry(f'{window_width}x{window_height}+{center_x}+{center_y}')
        logging.debug("Set window geometry")
        
        # Configure window
        root.minsize(800, 600)
        root.configure(bg="#1e1e1e")
        logging.debug("Configured window properties")
        
        # Create and pack the chat interface
        logging.debug("Creating ChatInterface...")
        chat = ChatInterface(root)
        logging.debug("Created ChatInterface")
        chat.pack(fill="both", expand=True, padx=2, pady=2)
        logging.debug("Packed ChatInterface")
        
        # Start the application
        logging.debug("Starting mainloop...")
        root.mainloop()
        
    except Exception as e:
        logging.error(f"Error in main: {str(e)}", exc_info=True)
        raise

if __name__ == "__main__":
    main()
