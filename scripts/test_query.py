#!/usr/bin/env python3
"""
Test the query pipeline.
Usage: python scripts/test_query.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from api.pipelines import QueryPipeline

def main():
    print("Testing Query Pipeline...")
    
    pipeline = QueryPipeline()
    pipeline.initialize()
    
    # Test questions
    questions = [
        "¿De qué trata el juego Dune: Arrakis Dominion?",
        "¿Qué es la especia Melange?",
        "¿Cómo funciona el sistema de casas?",
    ]
    
    for question in questions:
        print(f"\n{'='*60}")
        print(f"Q: {question}")
        print(f"{'='*60}")
        
        result = pipeline.query(question)
        
        print(f"\n✅ Answer: {result.answer[:300]}...")
        print(f"\n📊 Latency: {result.latency_ms:.0f}ms")
        print(f"\n📚 Sources ({len(result.sources)}):")
        for i, source in enumerate(result.sources, 1):
            print(f"  {i}. {source['source']} (score: {source['score']:.2f})")

if __name__ == "__main__":
    main()