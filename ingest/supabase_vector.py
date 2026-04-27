"""
Supabase Vector Store
RAG using Supabase pgvector
"""

import os
import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

import psycopg2
from psycopg2 import sql
import numpy as np
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)


@dataclass
class SearchResult:
    """Vector search result"""
    text: str
    metadata: dict
    score: float


class SupabaseVectorStore:
    """
    Vector store using Supabase pgvector.
    Uses cosine similarity search.
    """
    
    def __init__(
        self,
        conn_str: str = None,
        table_name: str = "dune_knowledge"
    ):
        self.conn_str = conn_str or os.getenv(
            "NEON_CONN",
            os.getenv("SUPABASE_DB", "")
        )
        self.table_name = table_name
        self._conn = None
    
    @property
    def connection(self):
        """Get database connection"""
        if self._conn is None or self._conn.closed:
            self._conn = psycopg2.connect(self.conn_str)
        return self._conn
    
    def initialize(self):
        """Create table if not exists"""
        with self.connection.cursor() as cur:
            # Check if table exists
            cur.execute(f"""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = '{self.table_name}'
                );
            """)
            exists = cur.fetchone()[0]
            
            if not exists:
                # Create table with vector
                cur.execute(f"""
                    CREATE TABLE {self.table_name} (
                        id SERIAL PRIMARY KEY,
                        text TEXT NOT NULL,
                        metadata JSONB DEFAULT '{}',
                        embedding vector(384)
                    );
                """)
                
                # Create HNSW index
                cur.execute(f"""
                    CREATE INDEX {self.table_name}_embedding_idx 
                    ON {self.table_name} 
                    USING hnsw (embedding vector_cosine_ops);
                """)
                
                self.connection.commit()
                logger.info(f"Created table: {self.table_name}")
            else:
                logger.info(f"Table {self.table_name} already exists")
    
    def add_texts(
        self,
        texts: List[str],
        embeddings: List[List[float]],
        metadata: List[Dict[str, Any]] = None
    ):
        """Add texts with embeddings"""
        if not texts:
            return
        
        metadata = metadata or [{}] * len(texts)
        
        with self.connection.cursor() as cur:
            for text, emb, meta in zip(texts, embeddings, metadata):
                cur.execute(f"""
                    INSERT INTO {self.table_name} (text, metadata, embedding)
                    VALUES (%s, %s, %s)
                """, (text, meta, emb))
            
            self.connection.commit()
        logger.info(f"Added {len(texts)} texts to {self.table_name}")
    
    def search(
        self,
        query_embedding: List[float],
        top_k: int = 5,
        filter_meta: Dict[str, Any] = None
    ) -> List[SearchResult]:
        """
        Search similar texts.
        
        Args:
            query_embedding: Query embedding
            top_k: Number of results
            filter_meta: Optional metadata filter
            
        Returns:
            List of SearchResult
        """
        emb_array = np.array(query_embedding)
        # Normalize for cosine similarity
        emb_array = emb_array / np.linalg.norm(emb_array)
        
        with self.connection.cursor() as cur:
            cur.execute(f"""
                SELECT text, metadata, 
                       1 - (embedding <=> %s::vector) as similarity
                FROM {self.table_name}
                ORDER BY embedding <=> %s::vector
                LIMIT %s;
            """, (emb_array.tolist(), emb_array.tolist(), top_k))
            
            results = []
            for row in cur.fetchall():
                results.append(SearchResult(
                    text=row[0],
                    metadata=row[1] or {},
                    score=float(row[2])
                ))
        
        return results
    
    def delete_all(self):
        """Delete all texts"""
        with self.connection.cursor() as cur:
            cur.execute(f"DELETE FROM {self.table_name};")
            self.connection.commit()
        logger.info(f"Cleared {self.table_name}")
    
    def close(self):
        """Close connection"""
        if self._conn:
            self._conn.close()
            self._conn = None