#!/usr/bin/env python3
"""Index complete lore document"""
import sys
sys.path.insert(0, '.')

from ingest import Embedder, QdrantIndexer, TextChunker
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams

print('Indexing complete_lore.md...')
embedder = Embedder()
indexer = QdrantIndexer()

# Create collection
c = QdrantClient(host='localhost', port=6333)
try:
    c.create_collection('dune_knowledge', vectors_config=VectorParams(size=384, distance=Distance.COSINE))
except:
    pass

indexer.initialize(embedding_dim=384)
chunker = TextChunker()

# Read and chunk
with open('data/complete_lore.md', 'r', encoding='utf-8') as f:
    text = f.read()

chunks = chunker.chunk(text=text, source='data/complete_lore.md', title='Historia Completa de Dune')
print('Created', len(chunks), 'chunks')

# Index
chunk_dicts = [{'text': c.text, 'metadata': c.metadata, 'char_count': c.char_count} for c in chunks]
chunk_dicts = embedder.encode_chunks(chunk_dicts)
stats = indexer.index_chunks(chunk_dicts)
print('Indexed', stats['indexed'], 'chunks')

# Get stats
print('Stats:', indexer.get_stats())