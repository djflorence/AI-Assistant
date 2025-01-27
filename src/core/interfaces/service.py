"""Base interfaces for services."""
from abc import ABC, abstractmethod
from typing import Any, Optional

class Service(ABC):
    """Base interface for all services."""
    
    @abstractmethod
    def initialize(self) -> None:
        """Initialize the service."""
        pass
    
    @abstractmethod
    def cleanup(self) -> None:
        """Clean up resources used by the service."""
        pass

class MessageHandler(ABC):
    """Interface for components that handle messages."""
    
    @abstractmethod
    async def handle_message(self, message: str, context: Optional[dict] = None) -> Any:
        """Handle an incoming message.
        
        Args:
            message: The message to handle
            context: Optional context for the message
            
        Returns:
            The response to the message
        """
        pass

class Storage(ABC):
    """Interface for storage components."""
    
    @abstractmethod
    async def save(self, key: str, data: Any) -> None:
        """Save data.
        
        Args:
            key: The key to save under
            data: The data to save
        """
        pass
    
    @abstractmethod
    async def load(self, key: str) -> Any:
        """Load data.
        
        Args:
            key: The key to load
            
        Returns:
            The loaded data
        """
        pass
    
    @abstractmethod
    async def delete(self, key: str) -> None:
        """Delete data.
        
        Args:
            key: The key to delete
        """
        pass
