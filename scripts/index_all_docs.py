#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Index all Dune documentation into Qdrant
"""
import sys
import os

# Add parent to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ingest import Embedder, QdrantIndexer, TextChunker
from qdrant_client.models import Distance, VectorParams
from qdrant_client import QdrantClient
import logging
import warnings
warnings.filterwarnings('ignore')

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def main():
    print("=" * 50)
    print("INDEXING DUNE DOCUMENTATION")
    print("=" * 50)
    
    # Initialize components
    print("\n[1/4] Initializing components...")
    embedder = Embedder()
    indexer = QdrantIndexer()
    chunker = TextChunker()
    
    # Embedding dimension
    embedder.initialize()
    embedding_dim = embedder.embedding_dim
    print(f"   Embedding dimension: {embedding_dim}")
    
    # Create collection
    print("\n[2/4] Creating Qdrant collection...")
    qdrant = QdrantClient(host='localhost', port=6333)
    try:
        qdrant.create_collection(
            'dune_knowledge',
            vectors_config=VectorParams(size=embedding_dim, distance=Distance.COSINE)
        )
        print("   Collection created")
    except Exception as e:
        print(f"   Collection exists: {e}")
    
    # Initialize indexer
    indexer.initialize(embedding_dim=embedding_dim)
    
    # Absolute paths for data
    chat_root = r"C:\Users\A8-16t\Desktop\Chatbot"
    data_path = os.path.join(chat_root, r"Dune-RAG\data")
    docs_path = os.path.join(chat_root, r"Dune-Documentacion")
    
    # Define documents to index (relative paths work too now)
    docs_to_index = [
        # Pre-processed lore in data folder
        (os.path.join(data_path, "complete_lore.md"), "Lore Completo"),
        (os.path.join(data_path, "rules.md"), "Reglas"),
        (os.path.join(data_path, "units.md"), "Unidades"),
        # Main documentation
        (os.path.join(docs_path, "Dune_Arrakis_Dominion_Storytelling.md"), "Storytelling"),
        (os.path.join(docs_path, "Dune_Arrakis_Dominion_Manual_Tecnico.md"), "Manual Tecnico"),
        (os.path.join(docs_path, "Dune_Arrakis_Dominion_GDD_Recursos.md"), "GDD Recursos"),
    ]
    
    print("\n[3/4] Processing documents...")
    total_indexed = 0
    
    for file_path, doc_title in docs_to_index:
        if not os.path.exists(file_path):
            print(f"   [SKIP] Not found: {file_path}")
            continue
            
        print(f"\n   [FILE] Processing: {doc_title}")
        print(f"         Path: {file_path}")
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                text = f.read()
            
            print(f"         Size: {len(text):,} chars")
            
            # Chunk text
            chunks = chunker.chunk(text=text, source=file_path, title=doc_title)
            print(f"         Chunks: {len(chunks)}")
            
            if not chunks:
                continue
            
            # Convert to dict format
            chunk_dicts = [
                {
                    'text': chunk.text,
                    'metadata': chunk.metadata,
                    'char_count': chunk.char_count
                }
                for chunk in chunks
            ]
            
            # Generate embeddings
            print(f"         Embedding...")
            chunk_dicts = embedder.encode_chunks(chunk_dicts)
            
            # Index to Qdrant
            print(f"         Indexing...")
            result = indexer.index_chunks(chunk_dicts)
            
            print(f"         [OK] Indexed: {result['indexed']} chunks")
            total_indexed += result['indexed']
            
        except Exception as e:
            print(f"         [ERROR] {e}")
            continue
    
    print("\n[4/4] Verifying index...")
    stats = indexer.get_stats()
    print(f"   Collection: {stats.get('collection', 'N/A')}")
    print(f"   Vectors: {stats.get('vectors_count', 0):,}")
    print(f"   Points: {stats.get('points_count', 0):,}")
    
    print("\n" + "=" * 50)
    print(f"[DONE] Total indexed: {total_indexed:,} chunks")
    print("=" * 50)
    
    print("\nChatbot: http://localhost:7860")
    print("API docs: http://localhost:8000/docs")

if __name__ == "__main__":
    main()