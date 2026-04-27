#!/usr/bin/env python3
"""
Create Qdrant Collection

Creates a vector collection in Qdrant for storing RAG chunks.
"""
import os
import sys
from pathlib import Path

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams

COLLECTION_NAME = os.getenv("QDRANT_COLLECTION", "dune_knowledge")
VECTOR_SIZE = 384  # all-MiniLM-L6-v2


def create_collection(client: QdrantClient):
    """Create collection if it doesn't exist."""
    collections = client.get_collections().collections
    collection_names = [c.name for c in collections]
    
    if COLLECTION_NAME in collection_names:
        print(f"Collection '{COLLECTION_NAME}' already exists")
        return
    
    client.create_collection(
        collection_name=COLLECTION_NAME,
        vectors_config=VectorParams(
            size=VECTOR_SIZE,
            distance=Distance.COSINE
        )
    )
    print(f"Created collection '{COLLECTION_NAME}' with vector size {VECTOR_SIZE}")


if __name__ == "__main__":
    qdrant_url = os.getenv("QDRANT_URL", "http://localhost:6333")
    client = QdrantClient(url=qdrant_url)
    create_collection(client)