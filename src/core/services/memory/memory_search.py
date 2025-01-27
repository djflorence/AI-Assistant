"""Advanced search capabilities for memory service."""
from typing import List, Dict, Any, Optional, Tuple
from rapidfuzz import fuzz, process
from sentence_transformers import SentenceTransformer
import numpy as np
from dataclasses import dataclass
import threading

@dataclass
class SearchResult:
    """Search result with relevance score."""
    memory_id: str
    content: str
    score: float
    memory_type: str
    importance: float

class MemorySearch:
    """Advanced search capabilities for memories."""
    
    def __init__(self, model_name: str = 'all-MiniLM-L6-v2'):
        """Initialize search engine.
        
        Args:
            model_name: Name of the sentence transformer model
        """
        self.model = None
        self.model_name = model_name
        self.embeddings: Dict[str, np.ndarray] = {}
        self.embedding_lock = threading.Lock()
        
    def initialize(self):
        """Initialize the search engine."""
        if self.model is None:
            self.model = SentenceTransformer(self.model_name)
    
    def fuzzy_search(self, query: str, memories: Dict[str, Any],
                    min_score: int = 60) -> List[SearchResult]:
        """Perform fuzzy string matching.
        
        Args:
            query: Search query
            memories: Dictionary of memories
            min_score: Minimum matching score (0-100)
            
        Returns:
            List of search results
        """
        results = []
        
        # Get all memory contents
        choices = [(mid, m.content) for mid, m in memories.items()]
        
        # Perform fuzzy matching
        matches = process.extract(
            query,
            choices,
            scorer=fuzz.token_ratio,
            limit=None
        )
        
        for (memory_id, content), score in matches:
            if score >= min_score:
                memory = memories[memory_id]
                results.append(SearchResult(
                    memory_id=memory_id,
                    content=content,
                    score=score / 100.0,
                    memory_type=memory.memory_type,
                    importance=memory.importance
                ))
        
        return sorted(results, key=lambda x: x.score, reverse=True)
    
    def semantic_search(self, query: str, memories: Dict[str, Any],
                       top_k: int = 5) -> List[SearchResult]:
        """Perform semantic search using embeddings.
        
        Args:
            query: Search query
            memories: Dictionary of memories
            top_k: Number of top results to return
            
        Returns:
            List of search results
        """
        self.initialize()  # Ensure model is loaded
        
        # Get query embedding
        query_embedding = self.model.encode(query, convert_to_numpy=True)
        
        # Update embeddings for memories
        self._update_embeddings(memories)
        
        results = []
        for memory_id, memory in memories.items():
            if memory_id in self.embeddings:
                # Calculate cosine similarity
                similarity = self._cosine_similarity(
                    query_embedding,
                    self.embeddings[memory_id]
                )
                
                results.append(SearchResult(
                    memory_id=memory_id,
                    content=memory.content,
                    score=float(similarity),
                    memory_type=memory.memory_type,
                    importance=memory.importance
                ))
        
        # Sort by score and return top_k
        results.sort(key=lambda x: x.score, reverse=True)
        return results[:top_k]
    
    def hybrid_search(self, query: str, memories: Dict[str, Any],
                     fuzzy_weight: float = 0.3,
                     semantic_weight: float = 0.7,
                     top_k: int = 5) -> List[SearchResult]:
        """Combine fuzzy and semantic search.
        
        Args:
            query: Search query
            memories: Dictionary of memories
            fuzzy_weight: Weight for fuzzy search scores
            semantic_weight: Weight for semantic search scores
            top_k: Number of top results to return
            
        Returns:
            List of search results
        """
        # Get both fuzzy and semantic results
        fuzzy_results = {
            r.memory_id: r for r in self.fuzzy_search(query, memories)
        }
        semantic_results = {
            r.memory_id: r for r in self.semantic_search(query, memories)
        }
        
        # Combine results
        combined_results = {}
        all_ids = set(fuzzy_results.keys()) | set(semantic_results.keys())
        
        for memory_id in all_ids:
            fuzzy_score = fuzzy_results[memory_id].score if memory_id in fuzzy_results else 0
            semantic_score = semantic_results[memory_id].score if memory_id in semantic_results else 0
            
            # Calculate combined score
            combined_score = (fuzzy_score * fuzzy_weight +
                            semantic_score * semantic_weight)
            
            # Use either result object, preferring semantic
            result = semantic_results.get(memory_id) or fuzzy_results[memory_id]
            result.score = combined_score
            combined_results[memory_id] = result
        
        # Sort and return top_k
        results = list(combined_results.values())
        results.sort(key=lambda x: x.score, reverse=True)
        return results[:top_k]
    
    def _update_embeddings(self, memories: Dict[str, Any]):
        """Update embeddings for memories.
        
        Args:
            memories: Dictionary of memories
        """
        with self.embedding_lock:
            # Find memories without embeddings
            new_memories = {
                mid: m.content for mid, m in memories.items()
                if mid not in self.embeddings
            }
            
            if new_memories:
                # Generate embeddings in batches
                contents = list(new_memories.values())
                embeddings = self.model.encode(contents, convert_to_numpy=True)
                
                # Store new embeddings
                for (mid, _), embedding in zip(new_memories.items(), embeddings):
                    self.embeddings[mid] = embedding
    
    def _cosine_similarity(self, a: np.ndarray, b: np.ndarray) -> float:
        """Calculate cosine similarity between vectors.
        
        Args:
            a: First vector
            b: Second vector
            
        Returns:
            Similarity score
        """
        return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))
