#!/bin/bash
# Script para descargar el modelo Qwen
# Usage: docker exec -it dune-ollama ollama pull qwen2.5-7b-instruct

echo "Pulling Qwen 2.5 7B Instruct model..."
docker exec -it dune-ollama ollama pull qwen2.5-7b-instruct

echo "Verifying model..."
docker exec -it dune-ollama ollama list