"""
Ingest schemas for API
"""

from pydantic import BaseModel, Field
from typing import List, Optional


class IngestRequest(BaseModel):
    """Request schema for /ingest endpoint"""
    sources: List[str] = Field(description="List of file paths or URLs to ingest")
    
    class Config:
        json_schema_extra = {
            "example": {
                "sources": [
                    "https://example.com/docs/article1",
                    "/path/to/document.pdf"
                ]
            }
        }


class IngestResult(BaseModel):
    """Result of ingesting a single source"""
    source: str = Field(description="Source (file path or URL)")
    type: str = Field(description="Source type: 'file' or 'url'")
    success: bool = Field(description="Whether ingestion succeeded")
    chunks_indexed: int = Field(description="Number of chunks indexed")
    message: str = Field(default="", description="Error message if failed")


class IngestResponse(BaseModel):
    """Response schema for /ingest endpoint"""
    total_chunks: int = Field(description="Total chunks indexed")
    total_sources: int = Field(description="Total sources processed")
    success_count: int = Field(description="Number of successful ingestions")
    error_count: int = Field(description="Number of failed ingestions")
    results: List[IngestResult] = Field(description="Detailed results per source")

    class Config:
        json_schema_extra = {
            "example": {
                "total_chunks": 45,
                "total_sources": 2,
                "success_count": 2,
                "error_count": 0,
                "results": [
                    {
                        "source": "/path/to/doc.pdf",
                        "type": "file",
                        "success": True,
                        "chunks_indexed": 30,
                        "message": ""
                    },
                    {
                        "source": "https://example.com/article",
                        "type": "url",
                        "success": True,
                        "chunks_indexed": 15,
                        "message": ""
                    }
                ]
            }
        }