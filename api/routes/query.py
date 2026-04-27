"""
Query routes - RAG query endpoints
"""

import logging
from fastapi import APIRouter, HTTPException

from ..schemas.query import QueryRequest, QueryResponse, StatsResponse
from ..pipelines import QueryPipeline, QueryConfig

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/query", tags=["Query"])

# Initialize pipeline
pipeline = QueryPipeline()

@router.post("/", response_model=QueryResponse)
async def query(request: QueryRequest) -> QueryResponse:
    """
    Ask a question to the RAG system.
    
    The query is processed through the RAG pipeline:
    1. Embed the question
    2. Retrieve relevant documents from Qdrant
    3. Generate an answer using the context
    4. Return the answer with source citations
    """
    logger.info(f"Query received: {request.question[:100]}...")
    
    # Override top_k if specified in request
    if request.top_k:
        pipeline.config.top_k = request.top_k
    
    try:
        result = pipeline.query(request.question)
        
        return QueryResponse(
            answer=result.answer,
            sources=result.sources,
            query=result.query,
            latency_ms=result.latency_ms,
            success=result.success,
            error=result.error
        )
    except Exception as e:
        logger.error(f"Query failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/stats", response_model=StatsResponse)
async def stats() -> StatsResponse:
    """
    Get RAG system statistics.
    
    Returns information about the vector store, models, and configuration.
    """
    try:
        stats = pipeline.get_stats()
        return StatsResponse(**stats)
    except Exception as e:
        logger.error(f"Stats failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))