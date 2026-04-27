#!/usr/bin/env python3
"""
Ingest documents from a folder into the RAG system.
Usage: python scripts/ingest_folder.py --path ./data/raw
"""

import os
import sys
import argparse
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from ingest import (
    DoclingWorker,
    Crawl4AIWorker,
    TextChunker,
    Embedder,
    QdrantIndexer
)

def main():
    parser = argparse.ArgumentParser(description="Ingest documents into RAG")
    parser.add_argument("--path", default="./data/raw", help="Path to documents")
    parser.add_argument("--recursive", action="store_true", help="Recurse subdirectories")
    parser.add_argument("--extensions", default=".pdf,.docx,.pptx,.txt,.md", help="File extensions to process")
    args = parser.parse_args()
    
    extensions = set(args.extensions.split(","))
    
    print(f"Starting ingestion from: {args.path}")
    
    # Initialize components
    doc_worker = DoclingWorker()
    web_worker = Crawl4AIWorker()
    chunker = TextChunker()
    embedder = Embedder()
    indexer = QdrantIndexer()
    indexer.initialize(embedding_dim=embedder.embedding_dim)
    
    # Find files
    path = Path(args.path)
    files = []
    
    if args.recursive:
        for ext in extensions:
            files.extend(path.rglob(f"*{ext}"))
    else:
        for ext in extensions:
            files.extend(path.glob(f"*{ext}"))
    
    print(f"Found {len(files)} files to process")
    
    # Process files
    total_chunks = 0
    errors = 0
    
    for file_path in files:
        print(f"\nProcessing: {file_path}")
        
        try:
            # Extract text
            result = doc_worker.extract(str(file_path))
            
            if not result.success:
                print(f"  ❌ Extraction failed: {result.error}")
                errors += 1
                continue
            
            # Chunk text
            chunks = chunker.chunk(
                text=result.text,
                source=str(file_path),
                title=result.metadata.get("file_name", file_path.name)
            )
            
            if not chunks:
                print(f"  ⚠️ No chunks created")
                continue
            
            # Generate embeddings
            chunk_dicts = [
                {
                    "text": c.text,
                    "metadata": c.metadata,
                    "char_count": c.char_count
                }
                for c in chunks
            ]
            chunk_dicts = embedder.encode_chunks(chunk_dicts)
            
            # Index to Qdrant
            stats = indexer.index_chunks(chunk_dicts)
            
            total_chunks += stats["indexed"]
            print(f"  ✅ Indexed {stats['indexed']} chunks")
            
        except Exception as e:
            print(f"  ❌ Error: {e}")
            errors += 1
    
    print(f"\n{'='*50}")
    print(f"Ingestion complete!")
    print(f"  Total chunks indexed: {total_chunks}")
    print(f"  Errors: {errors}")
    print(f"  Collection stats: {indexer.get_stats()}")

if __name__ == "__main__":
    main()