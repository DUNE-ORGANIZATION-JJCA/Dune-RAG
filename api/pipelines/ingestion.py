"""
Ingestion Pipeline - Document ingestion through the API
"""

import logging
from typing import List, Optional
from pathlib import Path

from ingest import (
    DoclingWorker,
    Crawl4AIWorker,
    TextChunker,
    Embedder,
    QdrantIndexer
)

logger = logging.getLogger(__name__)

class IngestionPipeline:
    """
    Pipeline for ingesting documents via the API.
    """
    
    def __init__(self):
        self.doc_worker = DoclingWorker()
        self.web_worker = Crawl4AIWorker()
        self.chunker = TextChunker()
        self.embedder = Embedder()
        self.indexer = QdrantIndexer()
        self._initialized = False
    
    def initialize(self):
        """Initialize pipeline components"""
        if self._initialized:
            return
        
        self.embedder.initialize()
        self.indexer.initialize(embedding_dim=self.embedder.embedding_dim)
        self._initialized = True
    
    def ingest_file(self, file_path: str) -> dict:
        """Ingest a single file"""
        self.initialize()
        
        logger.info(f"Ingesting file: {file_path}")
        
        # Extract text
        result = self.doc_worker.extract(file_path)
        
        if not result.success:
            return {"success": False, "error": result.error}
        
        # Chunk text
        chunks = self.chunker.chunk(
            text=result.text,
            source=file_path,
            title=result.metadata.get("file_name", Path(file_path).name)
        )
        
        if not chunks:
            return {"success": False, "error": "No chunks created (text too short)"}
        
        # Convert to dicts
        chunk_dicts = [
            {
                "text": c.text,
                "metadata": c.metadata,
                "char_count": c.char_count
            }
            for c in chunks
        ]
        
        # Embed and index
        chunk_dicts = self.embedder.encode_chunks(chunk_dicts)
        stats = self.indexer.index_chunks(chunk_dicts)
        
        return {
            "success": True,
            "chunks_indexed": stats["indexed"],
            "file": file_path
        }
    
    def ingest_url(self, url: str) -> dict:
        """Ingest content from a URL"""
        self.initialize()
        
        logger.info(f"Ingesting URL: {url}")
        
        # Crawl URL
        result = self.web_worker.crawl_sync(url)
        
        if not result.success:
            return {"success": False, "error": result.error}
        
        # Chunk text
        chunks = self.chunker.chunk(
            text=result.text,
            source=url,
            title=result.metadata.get("title", url)
        )
        
        if not chunks:
            return {"success": False, "error": "No chunks created (text too short)"}
        
        # Convert and index
        chunk_dicts = [
            {
                "text": c.text,
                "metadata": c.metadata,
                "char_count": c.char_count
            }
            for c in chunks
        ]
        
        chunk_dicts = self.embedder.encode_chunks(chunk_dicts)
        stats = self.indexer.index_chunks(chunk_dicts)
        
        return {
            "success": True,
            "chunks_indexed": stats["indexed"],
            "url": url
        }
    
    def ingest_batch(self, paths: List[str]) -> List[dict]:
        """Ingest multiple files/URLs"""
        results = []
        for path in paths:
            if path.startswith("http"):
                result = self.ingest_url(path)
            else:
                result = self.ingest_file(path)
            results.append(result)
        return results