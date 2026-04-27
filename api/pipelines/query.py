"""
Query Pipeline - RAG query processing using Haystack patterns
"""

import os
import json
import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer
from qdrant_client import QdrantClient
import httpx

load_dotenv()

logger = logging.getLogger(__name__)

@dataclass
class QueryConfig:
    """Configuration for query pipeline"""
    top_k: int = 10  # MORE documents
    qdrant_url: str = "http://localhost:6333"
    qdrant_collection: str = "dune_knowledge"
    ollama_url: str = "http://localhost:11434"
    ollama_model: str = "qwen2.5:3b"
    sbert_model: str = "all-MiniLM-L6-v2"
    max_context_length: int = 4000  # Big context
    temperature: float = 0.2
    max_tokens: int = 800  # Longer but not too long

@dataclass
class QueryResult:
    """Result of a query"""
    answer: str
    sources: List[Dict[str, Any]]
    query: str
    latency_ms: float
    success: bool
    error: Optional[str] = None

class QueryPipeline:
    """
    Complete RAG query pipeline:
    1. Embed query
    2. Retrieve from Qdrant
    3. Build context
    4. Generate with Ollama
    5. Return with sources
    """
    
    def __init__(self, config: QueryConfig = None):
        self.config = config or QueryConfig()
        self.embedder = None
        self.qdrant_client = None
        self._initialized = False
    
    def initialize(self):
        """Initialize pipeline components"""
        if self._initialized:
            return
        
        logger.info("Initializing query pipeline...")
        
        # Load embedder
        logger.info(f"Loading embedder: {self.config.sbert_model}")
        self.embedder = SentenceTransformer(self.config.sbert_model)
        
        # Connect to Qdrant
        logger.info(f"Connecting to Qdrant: {self.config.qdrant_url}")
        url = self.config.qdrant_url
        if "://" in url:
            host = url.split("://")[1].split(":")[0]
            port = int(url.split(":")[-1]) if ":" in url else 6333
            self.qdrant_client = QdrantClient(host=host, port=port)
        else:
            self.qdrant_client = QdrantClient(host=url)
        
        self._initialized = True
        logger.info("Query pipeline initialized")
    
    def query(self, question: str) -> QueryResult:
        """
        Process a query through the RAG pipeline.
        
        Args:
            question: User question
            
        Returns:
            QueryResult with answer and sources
        """
        import time
        start = time.time()
        
        try:
            self.initialize()
            
            # Step 1: Embed query
            query_embedding = self.embedder.encode(question).tolist()
            
            # Step 2: Retrieve from Qdrant
            results = self.qdrant_client.query_points(
                collection_name=self.config.qdrant_collection,
                query=query_embedding,
                limit=self.config.top_k
            )
            
            # Extract points from QueryResponse
            points = results.points if hasattr(results, 'points') else results
            
            if not points:
                return QueryResult(
                    answer="No tengo información relevante para responder a esa pregunta. ¿Puedes reformular tu consulta?",
                    sources=[],
                    query=question,
                    latency_ms=(time.time() - start) * 1000,
                    success=True
                )
            
            # Step 3: Extract contexts
            contexts = []
            sources = []
            
            for i, result in enumerate(points):
                payload = result.payload
                contexts.append(payload.get("text", ""))
                sources.append({
                    "text": payload.get("text", "")[:200] + "...",
                    "source": payload.get("source", "unknown"),
                    "title": payload.get("title", ""),
                    "score": result.score
                })
            
            # Step 4: Build context
            context = self._build_context(contexts)
            
            # Step 5: Generate with Ollama
            answer = self._generate(question, context)
            
            latency = (time.time() - start) * 1000
            
            return QueryResult(
                answer=answer,
                sources=sources,
                query=question,
                latency_ms=latency,
                success=True
            )
            
        except Exception as e:
            logger.error(f"Query error: {e}")
            latency = (time.time() - start) * 1000
            
            return QueryResult(
                answer="Disculpa, tuve un problema al procesar tu pregunta. Por favor, intenta de nuevo.",
                sources=[],
                query=question,
                latency_ms=latency,
                success=False,
                error=str(e)
            )
    
    def _build_context(self, contexts: List[str]) -> str:
        """Build context string from retrieved documents"""
        full_context = "\n\n".join(contexts)
        
        # Truncate if too long
        if len(full_context) > self.config.max_context_length:
            full_context = full_context[:self.config.max_context_length] + "..."
        
        return full_context
    
    def _generate(self, question: str, context: str) -> str:
        """Generate answer using Ollama"""
        
        system_prompt = """Eres el experto definitivo en Dune. Responde deforma completa y detallada en español."""

        user_prompt = f"Contexto: {context}\n\nPregunta: {question}\n\nRespuesta:"
        
        try:
            response = httpx.post(
                f"{self.config.ollama_url}/api/generate",
                json={
                    "model": self.config.ollama_model,
                    "prompt": f"Instrucciones: {system_prompt}\n\n{user_prompt}",
                    "stream": False,
                    "options": {
                        "temperature": self.config.temperature,
                        "num_predict": self.config.max_tokens
                    }
                },
                timeout=300  # Longer timeout for long responses
            )
            response.raise_for_status()
            
            # Parse streaming response
            lines = response.text.strip().split('\n')
            result_text = ""
            for line in lines:
                if line.strip():
                    try:
                        data = json.loads(line)
                        result_text += data.get("response", "")
                        if data.get("done"):
                            break
                    except:
                        continue
            
            return result_text.strip()
            
        except Exception as e:
            logger.error(f"Ollama error: {e}")
            if context:
                return f"Según la documentación: {context[:500]}..."
            return "Lo siento, no tengo información suficiente."
    
    def _fallback_answer(self, question: str, context: str) -> str:
        """Fallback answer when LLM is unavailable"""
        if context:
            # Use context directly
            return f"Según la documentación: {context[:500]}..."
        else:
            return "Lo siento, no tengo suficiente información para responder a esa pregunta sobre Dune."

    def _fast_answer(self, question: str, context: str) -> str:
        """Fast answer using context directly - no LLM needed"""
        if not context:
            return "No tengo información relevante para esa pregunta. Intenta reformular tu consulta."
        
        # Clean and summarize context
        lines = [l.strip() for l in context.split('\n') if l.strip()]
        summary = '\n'.join(lines[:6])
        
        return summary[:800] + "..."

    def get_stats(self) -> Dict[str, Any]:
        """Get pipeline statistics"""
        if not self._initialized:
            self.initialize()
        
        try:
            info = self.qdrant_client.get_collection(self.config.qdrant_collection)
            return {
                "collection": self.config.qdrant_collection,
                "points": info.points_count,
                "vectors": info.vectors_count,
                "top_k": self.config.top_k,
                "embedder": self.config.sbert_model,
                "llm": self.config.ollama_model
            }
        except Exception as e:
            return {"error": str(e)}