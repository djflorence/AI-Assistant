"""Dependency Injection Container for the application."""
from dependency_injector import containers, providers
from src.core.services.chat.chat_service import ChatService
from src.core.services.memory.memory_service import MemoryService
from src.core.services.voice.voice_service import VoiceService
from src.ui.views.main_window import MainWindow
from src.core.event_bus import EventBus

class Container(containers.DeclarativeContainer):
    """Application container."""
    
    config = providers.Configuration()
    
    # Core infrastructure
    event_bus = providers.Singleton(EventBus)
    
    # Services
    chat_service = providers.Singleton(
        ChatService,
        event_bus=event_bus
    )
    
    memory_service = providers.Singleton(
        MemoryService,
        event_bus=event_bus
    )
    
    voice_service = providers.Singleton(
        VoiceService,
        event_bus=event_bus
    )
    
    # UI Components
    main_window = providers.Singleton(
        MainWindow,
        chat_service=chat_service,
        memory_service=memory_service,
        voice_service=voice_service,
        event_bus=event_bus
    )
