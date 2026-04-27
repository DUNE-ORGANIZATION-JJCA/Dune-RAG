#!/usr/bin/env python3
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ingest import Embedder, QdrantIndexer, TextChunker

embedder = Embedder()
indexer = QdrantIndexer()
chunker = TextChunker()

embedder.initialize()
indexer.initialize(embedding_dim=384)

with open('../data/encyclopedia.md', 'r', encoding='utf-8') as f:
    text = f.read()

chunks = chunker.chunk(text=text, source='encyclopedia.md', title='Enciclopedia Dune')
chunk_dicts = [{'text': c.text, 'metadata': c.metadata, 'char_count': c.char_count} for c in chunks]
chunk_dicts = embedder.encode_chunks(chunk_dicts)
result = indexer.index_chunks(chunk_dicts)

print(f'Indexed: {result["indexed"]} new chunks')