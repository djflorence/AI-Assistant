"""Chat service for handling message processing and responses."""
from typing import Optional, Dict, Any
from datetime import datetime
import asyncio
import json

from src.core.interfaces.service import Service, MessageHandler
from src.core.event_bus import EventBus, MessageSent, MessageReceived

class ChatService(Service, MessageHandler):
    """Service for handling chat functionality."""
    
    def __init__(self, event_bus: EventBus, config: Dict[str, Any]):
        """Initialize the chat service.
        
        Args:
            event_bus: Application event bus
            config: Configuration dictionary
        """
        self.event_bus = event_bus
        self.config = config
        self.chat_config = config['services']['chat']
        self.message_history = []
        self.is_processing = False
        
        # Subscribe to events
        self.event_bus.subscribe(MessageSent, self._on_message_sent)
    
    def initialize(self) -> None:
        """Initialize the service."""
        # Load any saved state or initialize connections
        pass
    
    def cleanup(self) -> None:
        """Clean up resources."""
        # Save state and close connections
        pass
    
    async def handle_message(self, message: str, context: Optional[dict] = None) -> Any:
        """Handle an incoming message.
        
        Args:
            message: The message to process
            context: Optional context for the message
            
        Returns:
            The response to the message
        """
        if self.is_processing:
            return None
        
        self.is_processing = True
        try:
            # Add message to history
            self.message_history.append({
                'role': 'user',
                'content': message,
                'timestamp': datetime.now().isoformat()
            })
            
            # Trim history if needed
            if len(self.message_history) > self.chat_config['max_history']:
                self.message_history = self.message_history[-self.chat_config['max_history']:]
            
            # Process message and get response
            response = await self._process_message(message, context)
            
            # Add response to history
            self.message_history.append({
                'role': 'assistant',
                'content': response,
                'timestamp': datetime.now().isoformat()
            })
            
            # Publish response event
            self.event_bus.publish(MessageReceived(
                content=response,
                assistant_id='assistant'
            ))
            
            return response
            
        finally:
            self.is_processing = False
    
    async def _process_message(self, message: str, context: Optional[dict] = None) -> str:
        """Process a message and generate a response.
        
        Args:
            message: The message to process
            context: Optional context for the message
            
        Returns:
            The generated response
        """
        # TODO: Implement actual message processing
        # For now, just echo the message
        await asyncio.sleep(1)  # Simulate processing
        return f"Echo: {message}"
    
    def _on_message_sent(self, event: MessageSent):
        """Handle message sent event."""
        asyncio.create_task(self.handle_message(event.content))
