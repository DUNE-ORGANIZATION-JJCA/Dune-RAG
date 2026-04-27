"""
Dune RAG API Server
FastAPI server for RAG system
"""

import os
import logging
from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from dotenv import load_dotenv

from .routes import health, ingest, query, arthur
from .routes.arthur_simulation import router as sim_router
from .schemas import ingest as ingest_schemas
from .pipelines import IngestionPipeline, QueryPipeline

load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


# Lifespan for startup/shutdown
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events"""
    logger.info("Starting Dune RAG API Server...")
    logger.info(f"QDRANT_URL: {os.getenv('QDRANT_URL', 'http://localhost:6333')}")
    logger.info(f"OLLAMA_URL: {os.getenv('OLLAMA_URL', 'http://localhost:11434')}")
    logger.info(f"SBERT_MODEL: {os.getenv('SBERT_MODEL', 'all-MiniLM-L6-v2')}")
    logger.info(f"QWEN_MODEL: {os.getenv('QWEN_MODEL', 'qwen2.5-7b-instruct')}")
    
    # Initialize pipelines on startup
    app.state.query_pipeline = QueryPipeline()
    app.state.ingestion_pipeline = IngestionPipeline()
    
    logger.info("Dune RAG API Server started successfully!")
    
    yield
    
    logger.info("Shutting down Dune RAG API Server...")


# Create FastAPI app
app = FastAPI(
    title="Dune RAG API",
    description="Retrieval Augmented Generation API for Dune: Arrakis Dominion",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Request logging middleware
@app.middleware("http")
async def log_requests(request, call_next):
    """Log all requests"""
    start_time = datetime.now()
    
    response = await call_next(request)
    
    duration = (datetime.now() - start_time).total_seconds() * 1000
    
    logger.info(
        f"{request.method} {request.url.path} - "
        f"Status: {response.status_code} - "
        f"Duration: {duration:.0f}ms"
    )
    
    return response


# Include routers
app.include_router(health.router, prefix="/api/v1")
app.include_router(ingest.router, prefix="/api/v1")
app.include_router(query.router, prefix="/api/v1")
app.include_router(arthur.router, prefix="/api/v1/arthur")
app.include_router(sim_router, prefix="/api/v1/simulation")


# Root endpoint
@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "name": "Dune RAG API",
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs"
    }


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Handle unexpected exceptions"""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "detail": str(exc),
            "path": str(request.url.path)
        }
    )


if __name__ == "__main__":
    import uvicorn
    
    host = os.getenv("API_HOST", "0.0.0.0")
    port = int(os.getenv("API_PORT", "8000"))
    
    uvicorn.run(
        "main:app",
        host=host,
        port=port,
        reload=True,
        log_level="info"
    )