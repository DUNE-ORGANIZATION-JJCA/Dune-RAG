"""
Query schemas for API
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any

class QueryRequest(BaseModel):
    """Request schema for /query endpoint"""
    question: str = Field(..., min_length=1, max_length=1000, description="User question")
    top_k: Optional[int] = Field(default=5, ge=1, le=20, description="Number of documents to retrieve")
    
    class Config:
        json_schema_extra = {
            "example": {
                "question": "¿De qué trata el juego Dune: Arrakis Dominion?",
                "top_k": 5
            }
        }

class Source(BaseModel):
    """Source document reference"""
    text: str = Field(description="Document excerpt")
    source: str = Field(description="Document source (file path or URL)")
    title: Optional[str] = Field(default="", description="Document title")
    score: float = Field(description="Relevance score (0-1)")

class QueryResponse(BaseModel):
    """Response schema for /query endpoint"""
    answer: str = Field(description="Generated answer")
    sources: List[Source] = Field(description="Retrieved source documents")
    query: str = Field(description="Original user question")
    latency_ms: float = Field(description="Processing time in milliseconds")
    success: bool = Field(description="Whether the query succeeded")
    error: Optional[str] = Field(default=None, description="Error message if failed")

    class Config:
        json_schema_extra = {
            "example": {
                "answer": "Dune: Arrakis Dominion es un juego de estrategia...",
                "sources": [
                    {
                        "text": "Dune: Arrakis Dominion es un juego de...",
                        "source": "Dune-Documentacion/storytelling.md",
                        "title": "Storytelling",
                        "score": 0.92
                    }
                ],
                "query": "¿De qué trata el juego?",
                "latency_ms": 1250.5,
                "success": True
            }
        }

class StatsResponse(BaseModel):
    """Response schema for /stats endpoint"""
    collection: str = Field(description="Collection name")
    points: int = Field(description="Number of indexed documents")
    top_k: int = Field(description="Default retrieval count")
    embedder: str = Field(description="Embedding model")
    llm: str = Field(description="LLM model")
    status: str = Field(default="ok", description="System status")