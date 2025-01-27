"""Event bus for communication between components."""
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional
from datetime import datetime

@dataclass
class Event:
    """Base event class."""
    type: str
    metadata: Optional[Dict[str, Any]] = None
    timestamp: datetime = field(default_factory=datetime.now)

@dataclass
class MessageSent:
    """Event for when a message is sent."""
    type: str = "message_sent"
    metadata: Optional[Dict[str, Any]] = None
    timestamp: datetime = field(default_factory=datetime.now)
    sender: str = field(default="")
    recipient: str = field(default="")
    content: str = field(default="")

@dataclass
class MessageReceived:
    """Event for when a message is received."""
    type: str = "message_received"
    metadata: Optional[Dict[str, Any]] = None
    timestamp: datetime = field(default_factory=datetime.now)
    sender: str = field(default="")
    content: str = field(default="")

@dataclass
class MemoryStored:
    """Event for when a memory is stored."""
    type: str = "memory_stored"
    metadata: Optional[Dict[str, Any]] = None
    timestamp: datetime = field(default_factory=datetime.now)
    content: str = field(default="")
    memory_id: str = field(default="")

@dataclass
class VisionResult:
    """Vision processing result event."""
    type: str = "vision_result"
    metadata: Optional[Dict[str, Any]] = None
    timestamp: datetime = field(default_factory=datetime.now)
    tasks: List[str] = field(default_factory=list)
    results: Dict[str, Any] = field(default_factory=dict)
    content: Optional[Any] = None

@dataclass
class VoiceInputStarted:
    """Event for when voice input starts."""
    type: str = "voice_input_started"
    metadata: Optional[Dict[str, Any]] = None
    timestamp: datetime = field(default_factory=datetime.now)
    device_id: str = field(default="")

@dataclass
class VoiceInputEnded:
    """Event for when voice input ends."""
    type: str = "voice_input_ended"
    metadata: Optional[Dict[str, Any]] = None
    timestamp: datetime = field(default_factory=datetime.now)
    text: str = field(default="")
    device_id: str = field(default="")

class EventBus:
    """Event bus for communication between components."""
    
    def __init__(self):
        """Initialize event bus."""
        self.subscribers = {}
    
    def subscribe(self, event_type: str, callback):
        """Subscribe to event type.
        
        Args:
            event_type: Event type to subscribe to
            callback: Callback function
        """
        if event_type not in self.subscribers:
            self.subscribers[event_type] = []
        self.subscribers[event_type].append(callback)
    
    def unsubscribe(self, event_type: str, callback):
        """Unsubscribe from event type.
        
        Args:
            event_type: Event type to unsubscribe from
            callback: Callback function
        """
        if event_type in self.subscribers:
            self.subscribers[event_type].remove(callback)
    
    def publish(self, event):
        """Publish event.
        
        Args:
            event: Event to publish
        """
        if event.type in self.subscribers:
            for callback in self.subscribers[event.type]:
                callback(event)
