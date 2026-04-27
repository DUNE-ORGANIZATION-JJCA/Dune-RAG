# Dune RAG - Retrieval Augmented Generation

RAG system for Dune: Arrakis Dominion using Qwen + Ollama + Haystack + Qdrant.

## Quick Start

### 1. Start Services

```bash
cd rag-rack
docker-compose up -d
```

### 2. Pull Model

```bash
docker exec dune-ollama ollama pull qwen2.5-7b-instruct
```

### 3. Create Collection

```bash
docker exec dune-api python scripts/create_collection.py
```

### 4. Test

```bash
# Health check
curl http://localhost:8000/api/v1/health

# Query
curl -X POST http://localhost:8000/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{"question": "¿De qué trata el juego?"}'
```

## Architecture

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Frontend  │────▶│  FastAPI    │────▶│  Haystack   │
│   (React)   │     │  (API)      │     │  Pipelines  │
└─────────────┘     └─────────────┘     └─────────────┘
                                              │
                    ┌─────────────────────────┼─────────────────────────┐
                    │                         │                         │
              ┌─────▼─────┐           ┌──────▼──────┐          ┌──────▼──────┐
              │  Qdrant   │           │   Ollama    │          │   SBERT     │
              │ (Vectors) │           │   (Qwen)    │          │ (Embeddings)│
              └───────────┘           └─────────────┘          └─────────────┘
```

## Project Structure

```
rag-rack/
├── api/                  # FastAPI application
│   ├── routes/          # API endpoints
│   ├── schemas/         # Pydantic models
│   └── pipelines/       # RAG pipelines
├── ingest/              # Document ingestion
│   ├── docling_worker.py
│   ├── crawl4ai_worker.py
│   ├── chunking.py
│   ├── embedding.py
│   └── indexer.py
├── frontend/            # React UI
├── scripts/             # CLI tools
│   ├── create_collection.py
│   ├── ingest_folder.py
│   ├── test_query.py
│   └── run_eval.py
└── data/                # Data directories
    ├── raw/             # Raw documents
    ├── chunks/          # Processed chunks
    └── eval/            # Evaluation datasets
```

## Environment Variables

See `.env` file for configuration.

## Development

### Run API locally

```bash
cd api
pip install -r requirements.txt
uvicorn main:app --reload
```

### Run frontend locally

```bash
cd frontend
npm install
npm run dev
```

### Run evaluation

```bash
python scripts/run_eval.py
```

## Documentation

- [API Documentation](http://localhost:8000/docs)
- [Evaluation Guide](data/eval/README.md)