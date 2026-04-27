"""
Embedding Generator - Generates embeddings using SBERT
"""

import os
import logging
from typing import List, Dict, Any
import numpy as np

from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer

load_dotenv()

logger = logging.getLogger(__name__)

class Embedder:
    """
    Generates embeddings using Sentence Transformers.
    Uses all-MiniLM-L6-v2 by default (384 dimensions, fast).
    """
    
    def __init__(
        self,
        model_name: str = None,
        device: str = None,
        batch_size: int = 32
    ):
        self.model_name = model_name or os.getenv("SBERT_MODEL", "all-MiniLM-L6-v2")
        self.device = device or ("cuda" if os.path.exists("/proc/driver/nvidia") else "cpu")
        self.batch_size = batch_size
        
        self.model = None
        self._embedding_dim = None
    
    def initialize(self):
        """Load the embedding model"""
        if self.model is not None:
            return
        
        logger.info(f"Loading embedding model: {self.model_name}")
        self.model = SentenceTransformer(self.model_name, device=self.device)
        self._embedding_dim = self.model.get_sentence_embedding_dimension()
        logger.info(f"Model loaded. Embedding dimension: {self._embedding_dim}")
    
    @property
    def embedding_dim(self) -> int:
        """Get embedding dimension"""
        if self._embedding_dim is None:
            self.initialize()
        return self._embedding_dim
    
    def encode(self, texts: List[str], normalize: bool = True) -> np.ndarray:
        """
        Generate embeddings for texts.
        
        Args:
            texts: List of text strings
            normalize: Whether to normalize embeddings (L2)
            
        Returns:
            numpy array of shape (n_texts, embedding_dim)
        """
        self.initialize()
        
        if not texts:
            return np.array([])
        
        logger.info(f"Generating embeddings for {len(texts)} texts...")
        
        embeddings = self.model.encode(
            texts,
            batch_size=self.batch_size,
            show_progress_bar=len(texts) > 10,
            normalize_embeddings=normalize,
            convert_to_numpy=True
        )
        
        return embeddings
    
    def encode_single(self, text: str, normalize: bool = True) -> np.ndarray:
        """Encode a single text"""
        return self.encode([text], normalize=normalize)[0]
    
    def encode_chunks(self, chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Encode a list of chunks and add embeddings.
        
        Args:
            chunks: List of chunk dicts with 'text' key
            
        Returns:
            List of chunks with added 'embedding' key
        """
        if not chunks:
            return []
        
        texts = [chunk["text"] for chunk in chunks]
        embeddings = self.encode(texts)
        
        for i, chunk in enumerate(chunks):
            chunk["embedding"] = embeddings[i].tolist()
        
        return chunks