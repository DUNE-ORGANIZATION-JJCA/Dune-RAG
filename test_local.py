#!/usr/bin/env python3
"""
Test script for Dune RAG - Local testing without Qdrant
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

print("=" * 60)
print("DUNE RAG - LOCAL TEST")
print("=" * 60)

# Test 1: Check environment
print("\n1. Checking environment...")
from dotenv import load_dotenv
load_dotenv()

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
MODEL = os.getenv("QWEN_MODEL", "qwen2.5:3b")
SBERT_MODEL = os.getenv("SBERT_MODEL", "all-MiniLM-L6-v2")

print(f"   Ollama URL: {OLLAMA_URL}")
print(f"   Model: {MODEL}")
print(f"   Embedder: {SBERT_MODEL}")

# Test 2: Ollama connection
print("\n2. Testing Ollama...")
import httpx

try:
    response = httpx.get(f"{OLLAMA_URL}/api/tags", timeout=10)
    response.raise_for_status()
    data = response.json()
    print(f"   [OK] Ollama running, {len(data.get('models', []))} models available")
except Exception as e:
    print(f"   [ERROR] Ollama not accessible: {e}")
    print("   Make sure Ollama is running: ollama serve")
    sys.exit(1)

# Test 3: Generate with Ollama
print(f"\n3. Testing generation with {MODEL}...")
try:
    response = httpx.post(
        f"{OLLAMA_URL}/api/generate",
        json={
            "model": MODEL,
            "prompt": "Respond with only: 'DUNE BOT OK'",
            "stream": False,
            "options": {"num_predict": 20}
        },
        timeout=60
    )
    response.raise_for_status()
    result = response.json()
    print(f"   [OK] Generated: {result.get('response', '')[:50]}")
except Exception as e:
    print(f"   [ERROR] Generation failed: {e}")
    print(f"   Model '{MODEL}' may not be downloaded.")
    sys.exit(1)

# Test 4: Test FastAPI
print("\n4. Testing FastAPI...")
try:
    from fastapi import FastAPI
    print("   [OK] FastAPI available")
except ImportError as e:
    print(f"   [WARNING] FastAPI not installed")
    print(f"   Run: pip install fastapi uvicorn")

# Summary
print("\n" + "=" * 60)
print("TEST SUMMARY")
print("=" * 60)
print("[OK] Ollama working")
print("[OK] Model loaded")
print("\nTo install full dependencies (when Python 3.12 ready):")
print("   pip install -r api/requirements.txt")
print("\nTo start API:")
print("   cd api && uvicorn main:app --reload --host 0.0.0.0 --port 8000")
print("=" * 60)