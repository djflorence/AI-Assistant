"""Analytics module for memory service."""
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from dataclasses import dataclass
from collections import Counter

@dataclass
class MemoryStats:
    """Statistics about memories."""
    total_memories: int
    memories_by_type: Dict[str, int]
    avg_importance: float
    memory_age_distribution: Dict[str, int]
    top_contexts: List[str]
    total_size_bytes: int
    compression_ratio: float

@dataclass
class MemoryUsageMetrics:
    """Memory usage metrics."""
    read_count: Dict[str, int]
    write_count: Dict[str, int]
    last_accessed: Dict[str, datetime]
    access_patterns: Dict[str, List[datetime]]

class MemoryAnalytics:
    """Analytics for memory operations."""
    
    def __init__(self):
        """Initialize analytics."""
        self.usage_metrics = MemoryUsageMetrics(
            read_count={},
            write_count={},
            last_accessed={},
            access_patterns={}
        )
    
    def calculate_stats(self, memories: Dict[str, Any]) -> MemoryStats:
        """Calculate memory statistics.
        
        Args:
            memories: Dictionary of memories
            
        Returns:
            Memory statistics
        """
        if not memories:
            return MemoryStats(
                total_memories=0,
                memories_by_type={},
                avg_importance=0.0,
                memory_age_distribution={},
                top_contexts=[],
                total_size_bytes=0,
                compression_ratio=0.0
            )
        
        # Convert to DataFrame for analysis
        df = pd.DataFrame([{
            'id': k,
            'type': v.memory_type,
            'importance': v.importance,
            'timestamp': pd.to_datetime(v.timestamp),
            'context': str(v.context),
            'content_length': len(v.content)
        } for k, v in memories.items()])
        
        # Calculate memory age distribution
        now = pd.Timestamp.now()
        df['age'] = (now - df['timestamp']).dt.total_seconds()
        age_bins = [
            0,
            3600,           # 1 hour
            86400,          # 1 day
            604800,         # 1 week
            2592000,        # 1 month
            31536000        # 1 year
        ]
        age_labels = [
            '<1 hour',
            '1-24 hours',
            '1-7 days',
            '1-4 weeks',
            '1-12 months',
            '>1 year'
        ]
        df['age_group'] = pd.cut(df['age'], bins=age_bins, labels=age_labels)
        age_distribution = df['age_group'].value_counts().to_dict()
        
        # Calculate context statistics
        context_counts = Counter(df['context'])
        top_contexts = [context for context, _ in context_counts.most_common(5)]
        
        return MemoryStats(
            total_memories=len(memories),
            memories_by_type=df['type'].value_counts().to_dict(),
            avg_importance=df['importance'].mean(),
            memory_age_distribution=age_distribution,
            top_contexts=top_contexts,
            total_size_bytes=df['content_length'].sum(),
            compression_ratio=self._calculate_compression_ratio(df['content_length'].sum())
        )
    
    def track_access(self, memory_id: str, operation: str):
        """Track memory access.
        
        Args:
            memory_id: ID of accessed memory
            operation: Type of operation ('read' or 'write')
        """
        now = datetime.now()
        
        # Update access patterns
        if memory_id not in self.usage_metrics.access_patterns:
            self.usage_metrics.access_patterns[memory_id] = []
        self.usage_metrics.access_patterns[memory_id].append(now)
        
        # Update last accessed
        self.usage_metrics.last_accessed[memory_id] = now
        
        # Update operation counts
        if operation == 'read':
            self.usage_metrics.read_count[memory_id] = \
                self.usage_metrics.read_count.get(memory_id, 0) + 1
        elif operation == 'write':
            self.usage_metrics.write_count[memory_id] = \
                self.usage_metrics.write_count.get(memory_id, 0) + 1
    
    def get_access_patterns(self, memory_id: str) -> Dict[str, Any]:
        """Get access patterns for a memory.
        
        Args:
            memory_id: ID of memory
            
        Returns:
            Dictionary of access patterns
        """
        if memory_id not in self.usage_metrics.access_patterns:
            return {
                'total_reads': 0,
                'total_writes': 0,
                'last_accessed': None,
                'access_frequency': 0,
                'peak_usage_times': []
            }
        
        accesses = self.usage_metrics.access_patterns[memory_id]
        if not accesses:
            return {
                'total_reads': 0,
                'total_writes': 0,
                'last_accessed': None,
                'access_frequency': 0,
                'peak_usage_times': []
            }
        
        # Calculate access frequency (accesses per day)
        first_access = min(accesses)
        last_access = max(accesses)
        days_diff = (last_access - first_access).total_seconds() / 86400
        access_frequency = len(accesses) / (days_diff if days_diff > 0 else 1)
        
        # Find peak usage times
        df = pd.DataFrame({'timestamp': accesses})
        df['hour'] = df['timestamp'].dt.hour
        peak_hours = df['hour'].value_counts().head(3).index.tolist()
        
        return {
            'total_reads': self.usage_metrics.read_count.get(memory_id, 0),
            'total_writes': self.usage_metrics.write_count.get(memory_id, 0),
            'last_accessed': self.usage_metrics.last_accessed.get(memory_id),
            'access_frequency': access_frequency,
            'peak_usage_times': [f"{hour:02d}:00" for hour in peak_hours]
        }
    
    def _calculate_compression_ratio(self, total_size: int) -> float:
        """Calculate compression ratio.
        
        Args:
            total_size: Total size of uncompressed data
            
        Returns:
            Compression ratio
        """
        # This would be replaced with actual compression metrics
        # For now, return a placeholder value
        return 0.4  # Represents 60% compression
