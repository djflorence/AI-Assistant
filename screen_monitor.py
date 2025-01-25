"""Independent screen monitoring process that runs continuously."""
import os
import sys
import time
import mss
import numpy as np
from PIL import Image
import multiprocessing
from multiprocessing import Process, Queue, Event
import traceback
import json
import signal

class ScreenMonitor(Process):
    def __init__(self, state_file='monitor_state.json'):
        super().__init__()
        self.state_file = state_file
        self.stop_event = Event()
        self.daemon = False  # Make it a non-daemon process so it keeps running
        
    def run(self):
        """Main monitoring loop that keeps running no matter what."""
        signal.signal(signal.SIGTERM, self.handle_signal)
        signal.signal(signal.SIGINT, self.handle_signal)
        
        while not self.stop_event.is_set():
            try:
                self.monitor_screen()
            except Exception as e:
                self.log_error(f"Error in monitor: {str(e)}\n{traceback.format_exc()}")
                time.sleep(1)  # Brief pause before restarting
                
    def monitor_screen(self):
        """Monitor the screen and save state."""
        with mss.mss() as sct:
            while not self.stop_event.is_set():
                try:
                    # Capture screen
                    screenshot = sct.grab(sct.monitors[1])
                    
                    # Convert to format suitable for saving
                    img = Image.frombytes('RGB', screenshot.size, screenshot.rgb)
                    
                    # Save state
                    state = {
                        'timestamp': time.time(),
                        'screen_size': screenshot.size,
                        'is_monitoring': True
                    }
                    
                    self.save_state(state)
                    time.sleep(0.1)  # Small delay between captures
                    
                except Exception as e:
                    self.log_error(f"Error capturing screen: {str(e)}")
                    time.sleep(1)  # Brief pause before retrying
                    
    def save_state(self, state):
        """Save monitor state to file."""
        try:
            with open(self.state_file, 'w') as f:
                json.dump(state, f)
        except Exception as e:
            self.log_error(f"Error saving state: {str(e)}")
            
    def log_error(self, error):
        """Log error to file."""
        try:
            with open('monitor_error.log', 'a') as f:
                f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')}: {error}\n")
        except:
            pass  # If we can't log, just continue
            
    def handle_signal(self, signum, frame):
        """Handle shutdown signals gracefully."""
        self.cleanup()
        
    def cleanup(self):
        """Clean up resources."""
        try:
            # Save final state
            state = {
                'timestamp': time.time(),
                'is_monitoring': False,
                'shutdown': 'graceful'
            }
            self.save_state(state)
        except:
            pass
        finally:
            self.stop_event.set()

def start_monitor():
    """Start the monitor process."""
    monitor = ScreenMonitor()
    monitor.start()
    return monitor

def stop_monitor(monitor):
    """Stop the monitor process gracefully."""
    if monitor and monitor.is_alive():
        monitor.stop_event.set()
        monitor.join(timeout=5)
        if monitor.is_alive():
            monitor.terminate()

if __name__ == '__main__':
    try:
        monitor = start_monitor()
        
        # Keep the main process running
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        stop_monitor(monitor)
    except Exception as e:
        print(f"Error: {e}")
        stop_monitor(monitor)
