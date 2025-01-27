"""Compression utilities for memory service."""
import zstandard as zstd
import json
from typing import Dict, Any, Union, Optional
import base64
import threading
from datetime import datetime

class MemoryCompressor:
    """Handles compression of memory data."""
    
    def __init__(self, compression_level: int = 3):
        """Initialize the compressor.
        
        Args:
            compression_level: Zstandard compression level (1-22)
        """
        self.compression_level = compression_level
        self.compressor = zstd.ZstdCompressor(level=compression_level)
        self.decompressor = zstd.ZstdDecompressor()
        self.compression_stats = CompressionStats()
        self.lock = threading.Lock()
    
    def compress_memory(self, memory_data: Dict[str, Any]) -> bytes:
        """Compress memory data.
        
        Args:
            memory_data: Memory data to compress
            
        Returns:
            Compressed data
        """
        with self.lock:
            # Convert to JSON string
            json_data = json.dumps(memory_data)
            original_size = len(json_data.encode())
            
            # Compress
            compressed = self.compressor.compress(json_data.encode())
            compressed_size = len(compressed)
            
            # Update stats
            self.compression_stats.update(
                original_size,
                compressed_size
            )
            
            return compressed
    
    def decompress_memory(self, compressed_data: bytes) -> Dict[str, Any]:
        """Decompress memory data.
        
        Args:
            compressed_data: Compressed memory data
            
        Returns:
            Decompressed memory data
        """
        with self.lock:
            # Decompress
            decompressed = self.decompressor.decompress(compressed_data)
            
            # Parse JSON
            return json.loads(decompressed.decode())
    
    def compress_file(self, input_path: str, output_path: str) -> None:
        """Compress an entire file.
        
        Args:
            input_path: Path to input file
            output_path: Path to output file
        """
        with self.lock:
            with open(input_path, 'rb') as input_file:
                with open(output_path, 'wb') as output_file:
                    self.compressor.copy_stream(input_file, output_file)
    
    def decompress_file(self, input_path: str, output_path: str) -> None:
        """Decompress an entire file.
        
        Args:
            input_path: Path to compressed file
            output_path: Path for decompressed output
        """
        with self.lock:
            with open(input_path, 'rb') as input_file:
                with open(output_path, 'wb') as output_file:
                    self.decompressor.copy_stream(input_file, output_file)
    
    def get_stats(self) -> 'CompressionStats':
        """Get compression statistics.
        
        Returns:
            Compression statistics
        """
        return self.compression_stats

class CompressionStats:
    """Track compression statistics."""
    
    def __init__(self):
        """Initialize compression stats."""
        self.total_original_size: int = 0
        self.total_compressed_size: int = 0
        self.compression_count: int = 0
        self.last_compression: Optional[datetime] = None
        self.compression_history: Dict[str, Dict[str, int]] = {}
        self.lock = threading.Lock()
    
    def update(self, original_size: int, compressed_size: int):
        """Update compression statistics.
        
        Args:
            original_size: Size before compression
            compressed_size: Size after compression
        """
        with self.lock:
            self.total_original_size += original_size
            self.total_compressed_size += compressed_size
            self.compression_count += 1
            self.last_compression = datetime.now()
            
            # Store in history
            date_key = self.last_compression.strftime('%Y-%m-%d')
            if date_key not in self.compression_history:
                self.compression_history[date_key] = {
                    'original_size': 0,
                    'compressed_size': 0,
                    'count': 0
                }
            
            self.compression_history[date_key]['original_size'] += original_size
            self.compression_history[date_key]['compressed_size'] += compressed_size
            self.compression_history[date_key]['count'] += 1
    
    @property
    def compression_ratio(self) -> float:
        """Calculate compression ratio.
        
        Returns:
            Compression ratio (compressed size / original size)
        """
        if self.total_original_size == 0:
            return 0.0
        return self.total_compressed_size / self.total_original_size
    
    @property
    def space_saved(self) -> int:
        """Calculate space saved in bytes.
        
        Returns:
            Number of bytes saved
        """
        return self.total_original_size - self.total_compressed_size
    
    def get_daily_stats(self, days: int = 7) -> Dict[str, Dict[str, Union[int, float]]]:
        """Get daily compression statistics.
        
        Args:
            days: Number of days to return
            
        Returns:
            Dictionary of daily statistics
        """
        with self.lock:
            # Sort dates and get last 'days' entries
            dates = sorted(self.compression_history.keys(), reverse=True)[:days]
            
            return {
                date: {
                    **self.compression_history[date],
                    'ratio': (self.compression_history[date]['compressed_size'] /
                             self.compression_history[date]['original_size']
                             if self.compression_history[date]['original_size'] > 0
                             else 0.0)
                }
                for date in dates
            }
