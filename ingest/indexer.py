"""
Qdrant Indexer - Indexes chunks to Qdrant vector database
"""

import os
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

from dotenv import load_dotenv
from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct, Vector, Distance

load_dotenv()

logger = logging.getLogger(__name__)

class QdrantIndexer:
    """
    Indexes document chunks into Qdrant.
    """
    
    def __init__(
        self,
        collection_name: str = None,
        host: str = None,
        port: int = None
    ):
        self.collection_name = collection_name or os.getenv("QDRANT_COLLECTION", "dune_knowledge")
        self.host = host or os.getenv("QDRANT_URL", "http://localhost:6333").replace("http://", "").split(":")[0]
        self.port = port or int(os.getenv("QDRANT_PORT", "6333"))
        
        self.client = None
        self._embedding_dim = None
    
    def initialize(self, embedding_dim: int = 384):
        """Connect to Qdrant"""
        self._embedding_dim = embedding_dim
        
        logger.info(f"Connecting to Qdrant at {self.host}:{self.port}...")
        
        # Parse host from URL if needed
        url = os.getenv("QDRANT_URL", "http://localhost:6333")
        if "://" in url:
            host_only = url.split("://")[1].split(":")[0] if ":" in url else url.split("://")[1]
            port_only = int(url.split(":")[-1]) if ":" in url else 6333
            self.client = QdrantClient(host=host_only, port=port_only)
        else:
            self.client = QdrantClient(host=self.host, port=self.port)
        
        logger.info("Connected to Qdrant")
    
    def index_chunks(
        self,
        chunks: List[Dict[str, Any]],
        batch_size: int = 100
    ) -> Dict[str, Any]:
        """
        Index chunks into Qdrant.
        
        Args:
            chunks: List of chunks with 'text', 'embedding', 'metadata'
            batch_size: Number of points per batch
            
        Returns:
            Indexing stats
        """
        if not self.client:
            self.initialize()
        
        if not chunks:
            return {"indexed": 0, "errors": 0}
        
        logger.info(f"Indexing {len(chunks)} chunks...")
        
        indexed = 0
        errors = 0
        
        for i in range(0, len(chunks), batch_size):
            batch = chunks[i:i + batch_size]
            
            points = []
            for j, chunk in enumerate(batch):
                try:
                    # Generate unique integer ID
                    point_id = i + j  # Must be integer or UUID

                    point = PointStruct(
                        id=point_id,
                        vector=chunk["embedding"],
                        payload={
                            "text": chunk["text"],
                            "source": chunk["metadata"].get("source", "unknown"),
                            "title": chunk["metadata"].get("title", ""),
                            "source_type": chunk["metadata"].get("source_type", "document"),
                            "chunk_index": chunk["metadata"].get("chunk_index", j),
                            "char_count": chunk.get("char_count", len(chunk["text"])),
                            "indexed_at": datetime.now().isoformat()
                        }
                    )
                    points.append(point)
                    
                except Exception as e:
                    logger.error(f"Error creating point: {e}")
                    errors += 1
            
            if points:
                try:
                    self.client.upsert(
                        collection_name=self.collection_name,
                        points=points
                    )
                    indexed += len(points)
                    logger.info(f"Indexed batch: {len(points)} points ({indexed}/{len(chunks)})")
                except Exception as e:
                    logger.error(f"Error upserting batch: {e}")
                    errors += len(points)
        
        logger.info(f"Indexing complete: {indexed} indexed, {errors} errors")
        
        return {
            "indexed": indexed,
            "errors": errors,
            "collection": self.collection_name
        }
    
    def get_stats(self) -> Dict[str, Any]:
        """Get collection statistics"""
        if not self.client:
            self.initialize()
        
        try:
            info = self.client.get_collection(self.collection_name)
            return {
                "collection": self.collection_name,
                "vectors_count": info.indexed_vectors_count,
                "points_count": info.points_count,
                "status": info.status
            }
        except Exception as e:
            logger.error(f"Error getting stats: {e}")
            return {"error": str(e)}
    
    def delete_all(self) -> bool:
        """Delete all points in collection"""
        if not self.client:
            self.initialize()
        
        try:
            self.client.delete_collection(self.collection_name)
            logger.info(f"Deleted collection: {self.collection_name}")
            return True
        except Exception as e:
            logger.error(f"Error deleting collection: {e}")
            return False