"""Memory service for handling persistent memory storage and retrieval."""
import os
import json
import shutil
from datetime import datetime
from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass, asdict
from dataclasses_json import dataclass_json
import threading
import time

from src.core.interfaces.service import Service, Storage
from src.core.event_bus import EventBus, MemoryStored
from src.core.services.memory.memory_search import MemorySearch, SearchResult
from src.core.services.memory.memory_compression import MemoryCompressor
from src.core.services.memory.memory_analytics import MemoryAnalytics, MemoryStats

@dataclass_json
@dataclass
class Memory:
    """Structure for storing memory entries."""
    content: str
    timestamp: str
    importance: float
    context: Optional[Dict[str, Any]] = None
    source: Optional[str] = None
    memory_type: str = "general"

class MemoryService(Service, Storage):
    """Service for handling memory operations."""
    
    def __init__(self, event_bus: EventBus, config: Dict[str, Any]):
        """Initialize the memory service.
        
        Args:
            event_bus: Application event bus
            config: Configuration dictionary
        """
        self.event_bus = event_bus
        self.config = config
        self.memory_config = config['services']['memory']
        
        # Set up paths
        self.base_path = os.path.join('runtime', 'memory')
        self.memory_file = os.path.join(self.base_path, 'memories.json')
        self.index_file = os.path.join(self.base_path, 'memory_index.json')
        self.backup_dir = os.path.join(self.base_path, 'backups')
        
        # Initialize components
        self.search_engine = MemorySearch()
        self.compressor = MemoryCompressor()
        self.analytics = MemoryAnalytics()
        
        # Initialize locks for thread safety
        self.memory_lock = threading.Lock()
        self.index_lock = threading.Lock()
        
        # Initialize memory cache
        self.memories: Dict[str, Memory] = {}
        self.memory_index: Dict[str, List[str]] = {}  # Type -> memory_ids
        
        # Start backup thread
        self.backup_thread = threading.Thread(target=self._backup_loop, daemon=True)
    
    def initialize(self) -> None:
        """Initialize the service."""
        # Create necessary directories
        os.makedirs(self.base_path, exist_ok=True)
        os.makedirs(self.backup_dir, exist_ok=True)
        
        # Initialize search engine
        self.search_engine.initialize()
        
        # Load existing memories
        self._load_memories()
        self._load_index()
        
        # Start backup thread
        self.backup_thread.start()
    
    async def save(self, content: str, importance: float = 0.5, 
                  context: Optional[Dict[str, Any]] = None,
                  memory_type: str = "general",
                  source: Optional[str] = None) -> str:
        """Save a new memory.
        
        Args:
            content: The memory content
            importance: Memory importance (0.0 to 1.0)
            context: Optional context dictionary
            memory_type: Type of memory
            source: Source of the memory
            
        Returns:
            Memory ID
        """
        memory = Memory(
            content=content,
            timestamp=datetime.now().isoformat(),
            importance=importance,
            context=context,
            source=source,
            memory_type=memory_type
        )
        
        # Generate memory ID
        memory_id = f"{memory_type}_{int(time.time()*1000)}"
        
        with self.memory_lock:
            # Compress memory before storing
            memory_data = asdict(memory)
            compressed_data = self.compressor.compress_memory(memory_data)
            
            # Add to memory cache
            self.memories[memory_id] = memory
            
            # Update index
            if memory_type not in self.memory_index:
                self.memory_index[memory_type] = []
            self.memory_index[memory_type].append(memory_id)
            
            # Track write operation
            self.analytics.track_access(memory_id, 'write')
            
            # Save to disk
            self._save_memories()
            self._save_index()
        
        # Publish event
        self.event_bus.publish(MemoryStored(
            content=content,
            memory_id=memory_id
        ))
        
        return memory_id
    
    async def load(self, memory_id: str) -> Optional[Memory]:
        """Load a specific memory.
        
        Args:
            memory_id: ID of the memory to load
            
        Returns:
            Memory object if found, None otherwise
        """
        with self.memory_lock:
            return self.memories.get(memory_id)
    
    async def delete(self, memory_id: str) -> None:
        """Delete a memory.
        
        Args:
            memory_id: ID of the memory to delete
        """
        with self.memory_lock:
            if memory_id in self.memories:
                memory = self.memories[memory_id]
                # Remove from cache
                del self.memories[memory_id]
                # Remove from index
                if memory.memory_type in self.memory_index:
                    self.memory_index[memory.memory_type].remove(memory_id)
                # Save changes
                self._save_memories()
                self._save_index()
    
    async def search(self, query: str, 
                    search_type: str = 'hybrid',
                    memory_type: Optional[str] = None,
                    min_importance: float = 0.0,
                    top_k: int = 5) -> List[SearchResult]:
        """Search memories using specified search type.
        
        Args:
            query: Search query
            search_type: Type of search ('fuzzy', 'semantic', or 'hybrid')
            memory_type: Optional type filter
            min_importance: Minimum importance threshold
            top_k: Number of top results to return
            
        Returns:
            List of search results
        """
        with self.memory_lock:
            # Filter memories by type and importance
            memories = {
                k: v for k, v in self.memories.items()
                if (memory_type is None or v.memory_type == memory_type) and
                v.importance >= min_importance
            }
            
            # Perform search based on type
            if search_type == 'fuzzy':
                results = self.search_engine.fuzzy_search(query, memories)
            elif search_type == 'semantic':
                results = self.search_engine.semantic_search(query, memories, top_k)
            else:  # hybrid
                results = self.search_engine.hybrid_search(query, memories, top_k=top_k)
            
            # Track read operations
            for result in results:
                self.analytics.track_access(result.memory_id, 'read')
            
            return results
    
    def get_stats(self) -> Dict[str, Any]:
        """Get memory statistics and analytics.
        
        Returns:
            Dictionary of statistics
        """
        with self.memory_lock:
            memory_stats = self.analytics.calculate_stats(self.memories)
            compression_stats = self.compressor.get_stats()
            
            return {
                'memory_stats': asdict(memory_stats),
                'compression': {
                    'ratio': compression_stats.compression_ratio,
                    'space_saved': compression_stats.space_saved,
                    'daily_stats': compression_stats.get_daily_stats()
                }
            }
    
    def get_memory_usage(self, memory_id: str) -> Dict[str, Any]:
        """Get usage statistics for a specific memory.
        
        Args:
            memory_id: ID of the memory
            
        Returns:
            Dictionary of usage statistics
        """
        return self.analytics.get_access_patterns(memory_id)
    
    def _save_memories(self) -> None:
        """Save memories to disk."""
        try:
            # Compress entire memory file
            temp_file = self.memory_file + '.tmp'
            with open(temp_file, 'w', encoding='utf-8') as f:
                json.dump({
                    k: asdict(v) for k, v in self.memories.items()
                }, f)
            
            self.compressor.compress_file(temp_file, self.memory_file)
            os.remove(temp_file)
            
        except Exception as e:
            print(f"Error saving memories: {e}")
    
    def _load_memories(self) -> None:
        """Load memories from disk."""
        if os.path.exists(self.memory_file):
            try:
                # Decompress memory file
                temp_file = self.memory_file + '.tmp'
                self.compressor.decompress_file(self.memory_file, temp_file)
                
                with open(temp_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.memories = {
                        k: Memory.from_dict(v) for k, v in data.items()
                    }
                
                os.remove(temp_file)
                
            except Exception as e:
                print(f"Error loading memories: {e}")
                # Create backup of corrupted file
                if os.path.exists(self.memory_file):
                    backup_path = os.path.join(
                        self.backup_dir,
                        f"memories_backup_{int(time.time())}.json"
                    )
                    shutil.copy2(self.memory_file, backup_path)
    
    def _load_index(self) -> None:
        """Load memory index from disk."""
        if os.path.exists(self.index_file):
            try:
                with open(self.index_file, 'r', encoding='utf-8') as f:
                    self.memory_index = json.load(f)
            except Exception as e:
                print(f"Error loading memory index: {e}")
                # Rebuild index from memories
                self._rebuild_index()
    
    def _save_index(self) -> None:
        """Save memory index to disk."""
        try:
            with open(self.index_file, 'w', encoding='utf-8') as f:
                json.dump(self.memory_index, f, indent=2)
        except Exception as e:
            print(f"Error saving memory index: {e}")
    
    def _rebuild_index(self) -> None:
        """Rebuild the memory index from memories."""
        self.memory_index = {}
        for memory_id, memory in self.memories.items():
            if memory.memory_type not in self.memory_index:
                self.memory_index[memory.memory_type] = []
            self.memory_index[memory.memory_type].append(memory_id)
    
    def _backup_loop(self) -> None:
        """Background thread for periodic backups."""
        while True:
            time.sleep(self.memory_config['backup_interval_hours'] * 3600)
            with self.memory_lock:
                # Create timestamped backup
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                backup_path = os.path.join(
                    self.backup_dir,
                    f"memories_backup_{timestamp}.json"
                )
                try:
                    shutil.copy2(self.memory_file, backup_path)
                    # Clean up old backups
                    self._cleanup_old_backups()
                except Exception as e:
                    print(f"Error creating backup: {e}")
    
    def _cleanup_old_backups(self) -> None:
        """Clean up old backup files."""
        try:
            backups = sorted([
                os.path.join(self.backup_dir, f)
                for f in os.listdir(self.backup_dir)
                if f.startswith('memories_backup_')
            ])
            
            # Keep only the last 5 backups
            while len(backups) > 5:
                os.remove(backups.pop(0))
        except Exception as e:
            print(f"Error cleaning up backups: {e}")
