"""
Ingest routes - Document and URL ingestion endpoints
"""

import os
import logging
import tempfile
from pathlib import Path
from typing import List

from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from pydantic import BaseModel

from ..schemas.ingest import IngestResponse, IngestResult
from ..pipelines import IngestionPipeline

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ingest", tags=["Ingestion"])

# Initialize pipeline
ingestion_pipeline = IngestionPipeline()


class IngestURLRequest(BaseModel):
    """Request to ingest a URL"""
    url: str
    title: str = ""


class IngestURLResponse(BaseModel):
    """Response from URL ingestion"""
    success: bool
    chunks_indexed: int
    url: str
    message: str = ""


@router.post("", response_model=IngestResponse)
async def ingest(
    files: List[UploadFile] = File(...),
    urls: str = Form(default="", description="Comma-separated URLs")
) -> IngestResponse:
    """
    Ingest documents and/or URLs into the RAG system.
    
    Supports:
    - PDF files
    - DOCX files
    - PPTX files
    - Plain text files
    - URLs (comma-separated in the urls field)
    
    Files are uploaded as multipart/form-data.
    """
    logger.info(f"Ingest request received: {len(files)} files, {len(urls.split(',')) if urls else 0} URLs")
    
    results = []
    total_chunks = 0
    errors = 0
    
    # Process uploaded files
    for file in files:
        logger.info(f"Processing file: {file.filename}")
        
        try:
            # Save uploaded file temporarily
            with tempfile.NamedTemporaryFile(
                delete=False,
                suffix=Path(file.filename).suffix
            ) as tmp:
                content = await file.read()
                tmp.write(content)
                tmp_path = tmp.name
            
            # Ingest file
            result = ingestion_pipeline.ingest_file(tmp_path)
            
            if result["success"]:
                total_chunks += result["chunks_indexed"]
                results.append(IngestResult(
                    source=file.filename,
                    type="file",
                    success=True,
                    chunks_indexed=result["chunks_indexed"],
                    message=""
                ))
            else:
                errors += 1
                results.append(IngestResult(
                    source=file.filename,
                    type="file",
                    success=False,
                    chunks_indexed=0,
                    message=result.get("error", "Unknown error")
                ))
            
            # Clean up temp file
            os.unlink(tmp_path)
            
        except Exception as e:
            logger.error(f"Error processing {file.filename}: {e}")
            errors += 1
            results.append(IngestResult(
                source=file.filename,
                type="file",
                success=False,
                chunks_indexed=0,
                message=str(e)
            ))
    
    # Process URLs
    if urls:
        url_list = [u.strip() for u in urls.split(",") if u.strip()]
        
        for url in url_list:
            logger.info(f"Processing URL: {url}")
            
            try:
                result = ingestion_pipeline.ingest_url(url)
                
                if result["success"]:
                    total_chunks += result["chunks_indexed"]
                    results.append(IngestResult(
                        source=url,
                        type="url",
                        success=True,
                        chunks_indexed=result["chunks_indexed"],
                        message=""
                    ))
                else:
                    errors += 1
                    results.append(IngestResult(
                        source=url,
                        type="url",
                        success=False,
                        chunks_indexed=0,
                        message=result.get("error", "Unknown error")
                    ))
                    
            except Exception as e:
                logger.error(f"Error processing URL {url}: {e}")
                errors += 1
                results.append(IngestResult(
                    source=url,
                    type="url",
                    success=False,
                    chunks_indexed=0,
                    message=str(e)
                ))
    
    logger.info(f"Ingest complete: {total_chunks} chunks indexed, {errors} errors")
    
    return IngestResponse(
        total_chunks=total_chunks,
        total_sources=len(results),
        success_count=len(results) - errors,
        error_count=errors,
        results=results
    )


@router.post("/url", response_model=IngestURLResponse)
async def ingest_url(request: IngestURLRequest) -> IngestURLResponse:
    """
    Ingest a single URL into the RAG system.
    """
    logger.info(f"Ingesting URL: {request.url}")
    
    try:
        result = ingestion_pipeline.ingest_url(request.url)
        
        if result["success"]:
            return IngestURLResponse(
                success=True,
                chunks_indexed=result["chunks_indexed"],
                url=request.url,
                message="URL ingested successfully"
            )
        else:
            raise HTTPException(status_code=400, detail=result.get("error", "Ingestion failed"))
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"URL ingestion error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/file", response_model=IngestResponse)
async def ingest_file(file: UploadFile = File(...)) -> IngestResponse:
    """
    Ingest a single file into the RAG system.
    """
    return await ingest(files=[file], urls="")