#!/usr/bin/env python3
"""Quick index script for testing"""
import sys
sys.path.insert(0, '.')

from ingest import Embedder, QdrantIndexer, TextChunker
from qdrant_client.models import Distance, VectorParams
from qdrant_client import QdrantClient
import os

# Initialize
print('Initializing...')
embedder = Embedder()
indexer = QdrantIndexer()

# Create collection if needed
c = QdrantClient(host='localhost', port=6333)
try:
    c.create_collection('dune_knowledge', vectors_config=VectorParams(size=384, distance=Distance.COSINE))
    print('Collection created')
except:
    pass

# Initialize
indexer.initialize(embedding_dim=384)
chunker = TextChunker()

# Process files
files = ['data/rules.md', 'data/units.md']

total = 0
for f in files:
    if not os.path.exists(f):
        continue
    print(f'Processing: {f}')
    with open(f, 'r', encoding='utf-8') as file:
        text = file.read()
    
    chunks = chunker.chunk(text=text, source=f, title=f.split('/')[-1])
    print(f'  Created {len(chunks)} chunks')
    
    chunk_dicts = [
        {'text': c.text, 'metadata': c.metadata, 'char_count': c.char_count}
        for c in chunks
    ]
    chunk_dicts = embedder.encode_chunks(chunk_dicts)
    stats = indexer.index_chunks(chunk_dicts)
    print(f'  Indexed {stats["indexed"]} chunks')
    total += stats['indexed']

print(f'Total indexed: {total}')
print(f'Stats: {indexer.get_stats()}')