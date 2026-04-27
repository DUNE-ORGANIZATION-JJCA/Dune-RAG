"""
Health check routes
"""

import logging
import time
from datetime import datetime
from typing import Dict, Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import httpx

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/health", tags=["Health"])


class HealthResponse(BaseModel):
    """Health check response"""
    status: str
    timestamp: str
    services: Dict[str, Any]
    overall: str


class ServiceHealth(BaseModel):
    """Individual service health"""
    status: str
    latency_ms: float = 0
    message: str = ""


async def check_qdrant(url: str = "http://localhost:6333") -> ServiceHealth:
    """Check Qdrant service health"""
    start = time.time()
    
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{url}/collections")
            latency = (time.time() - start) * 1000
            
            if response.status_code == 200:
                return ServiceHealth(
                    status="healthy",
                    latency_ms=latency,
                    message="Qdrant is responding"
                )
            else:
                return ServiceHealth(
                    status="degraded",
                    latency_ms=latency,
                    message=f"Status code: {response.status_code}"
                )
    except httpx.TimeoutException:
        return ServiceHealth(
            status="unhealthy",
            latency_ms=(time.time() - start) * 1000,
            message="Qdrant timeout"
        )
    except Exception as e:
        return ServiceHealth(
            status="unhealthy",
            latency_ms=(time.time() - start) * 1000,
            message=str(e)
        )


async def check_ollama(url: str = "http://localhost:11434") -> ServiceHealth:
    """Check Ollama service health"""
    start = time.time()
    
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{url}/api/tags")
            latency = (time.time() - start) * 1000
            
            if response.status_code == 200:
                return ServiceHealth(
                    status="healthy",
                    latency_ms=latency,
                    message="Ollama is responding"
                )
            else:
                return ServiceHealth(
                    status="degraded",
                    latency_ms=latency,
                    message=f"Status code: {response.status_code}"
                )
    except httpx.TimeoutException:
        return ServiceHealth(
            status="unhealthy",
            latency_ms=(time.time() - start) * 1000,
            message="Ollama timeout"
        )
    except Exception as e:
        return ServiceHealth(
            status="unhealthy",
            latency_ms=(time.time() - start) * 1000,
            message=str(e)
        )


async def check_embeddings() -> ServiceHealth:
    """Check embeddings model availability"""
    start = time.time()
    
    try:
        from sentence_transformers import SentenceTransformer
        
        model = SentenceTransformer("all-MiniLM-L6-v2")
        # Quick test encoding
        model.encode("test")
        
        return ServiceHealth(
            status="healthy",
            latency_ms=(time.time() - start) * 1000,
            message="SBERT model loaded"
        )
    except Exception as e:
        return ServiceHealth(
            status="unhealthy",
            latency_ms=(time.time() - start) * 1000,
            message=str(e)
        )


@router.get("", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """
    Comprehensive health check of all services.
    
    Returns status of:
    - Qdrant (vector database)
    - Ollama (LLM runtime)
    - Embeddings model
    """
    import asyncio
    
    logger.info("Health check requested")
    
    # Run checks concurrently
    qdrant_task = asyncio.create_task(check_qdrant())
    ollama_task = asyncio.create_task(check_ollama())
    embeddings_task = asyncio.create_task(check_embeddings())
    
    qdrant, ollama, embeddings = await asyncio.gather(
        qdrant_task, ollama_task, embeddings_task
    )
    
    services = {
        "qdrant": qdrant.model_dump(),
        "ollama": ollama.model_dump(),
        "embeddings": embeddings.model_dump()
    }
    
    # Determine overall status
    statuses = [qdrant.status, ollama.status, embeddings.status]
    
    if all(s == "healthy" for s in statuses):
        overall = "healthy"
    elif any(s == "unhealthy" for s in statuses):
        overall = "unhealthy"
    else:
        overall = "degraded"
    
    return HealthResponse(
        status=overall,
        timestamp=datetime.now().isoformat(),
        services=services,
        overall=overall
    )


@router.get("/ready", response_model=Dict[str, str])
async def readiness_check() -> Dict[str, str]:
    """
    Simple readiness probe for Kubernetes/container orchestration.
    
    Returns 200 if the service is ready to handle requests.
    """
    return {"status": "ready"}


@router.get("/live", response_model=Dict[str, str])
async def liveness_check() -> Dict[str, str]:
    """
    Simple liveness probe for Kubernetes/container orchestration.
    
    Returns 200 if the service is alive.
    """
    return {"status": "alive"}