"""
Test script for Ollama endpoint.
Usage: python scripts/test_ollama.py
"""

import requests
import json

OLLAMA_URL = "http://localhost:11434"


def test_ollama():
    print("Testing Ollama connection...")

    # 1. Check if Ollama is running
    try:
        response = requests.get(f"{OLLAMA_URL}/api/tags", timeout=5)
        response.raise_for_status()
        models = response.json()
        print(f"✅ Ollama is running")
        print(f"   Available models: {[m['name'] for m in models.get('models', [])]}")
    except Exception as e:
        print(f"❌ Ollama not responding: {e}")
        return False

    # 2. Test generation with a simple prompt
    print("\nTesting generation...")
    try:
        response = requests.post(
            f"{OLLAMA_URL}/api/generate",
            json={
                "model": "qwen2.5-7b-instruct",
                "prompt": "Hello, respond with 'OK' if you can read this.",
                "stream": False
            },
            timeout=60
        )
        response.raise_for_status()
        result = response.json()
        print(f"✅ Generation works")
        print(f"   Response: {result.get('response', '')[:100]}")
        return True
    except Exception as e:
        print(f"❌ Generation failed: {e}")
        return False


if __name__ == "__main__":
    test_ollama()