"""
Query Pipeline - Cloud Version
Uses HuggingFace Inference + Supabase pgvector
"""

import os
import json
import logging
import time
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer
import httpx

# Cloud clients
from ingest.hf_inference import HFInferenceClient
from ingest.supabase_vector import SupabaseVectorStore

load_dotenv()

logger = logging.getLogger(__name__)


@dataclass
class CloudQueryConfig:
    """Configuration for cloud query pipeline"""
    top_k: int = 10
    supabase_url: str = None
    supabase_key: str = None
    supabase_table: str = "dune_knowledge"
    hf_token: str = None
    hf_model: str = "Qwen/Qwen2.5-7B-Instruct"
    sbert_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    max_context_length: int = 4000
    temperature: float = 0.2
    max_tokens: int = 800


@dataclass
class QueryResult:
    """Result of a query"""
    answer: str
    sources: List[Dict[str, Any]]
    query: str
    latency_ms: float
    success: bool
    error: Optional[str] = None


class CloudQueryPipeline:
    """
    Cloud RAG pipeline:
    1. Embed query (Sentence Transformers local)
    2. Retrieve from Supabase pgvector
    3. Build context
    4. Generate with HF Inference API
    5. Return with sources
    """
    
    def __init__(self, config: CloudQueryConfig = None):
        self.config = config or CloudQueryConfig()
        self.embedder = None
        self.vector_store = None
        self.llm = None
        self._initialized = False
    
    def initialize(self):
        """Initialize pipeline components"""
        if self._initialized:
            return
        
        logger.info("Initializing cloud query pipeline...")
        
        # Load embedder (local)
        logger.info(f"Loading embedder: {self.config.sbert_model}")
        self.embedder = SentenceTransformer(self.config.sbert_model)
        
        # Connect to Supabase
        logger.info("Connecting to Supabase...")
        conn_str = os.getenv("NEON_CONN") or os.getenv("SUPABASE_DB")
        self.vector_store = SupabaseVectorStore(
            conn_str=conn_str,
            table_name=self.config.supabase_table
        )
        self.vector_store.initialize()
        
        # Connect to HF
        logger.info(f"Connecting to HF: {self.config.hf_model}")
        self.llm = HFInferenceClient(
            api_token=self.config.hf_token,
            model=self.config.hf_model
        )
        self.llm.initialize()
        
        self._initialized = True
        logger.info("Cloud query pipeline initialized")
    
    def query(self, question: str) -> QueryResult:
        """
        Process a query through the cloud RAG pipeline.
        """
        start = time.time()
        
        try:
            self.initialize()
            
            # Step 1: Embed query
            query_embedding = self.embedder.encode(question).tolist()
            
            # Step 2: Retrieve from Supabase
            results = self.vector_store.search(
                query_embedding=query_embedding,
                top_k=self.config.top_k
            )
            
            if not results:
                return QueryResult(
                    answer="No tengo información relevante para responder a esa pregunta. ¿Puedes reformular tu consulta?",
                    sources=[],
                    query=question,
                    latency_ms=(time.time() - start) * 1000,
                    success=True
                )
            
            # Step 3: Build context
            context_parts = []
            sources = []
            
            for i, result in enumerate(results):
                context_parts.append(f"[{i+1}] {result.text}")
                sources.append({
                    "text": result.text[:200] + "...",
                    "score": result.score,
                    "metadata": result.metadata
                })
            
            context = "\n\n".join(context_parts)
            
            # Truncate if too long
            if len(context) > self.config.max_context_length:
                context = context[:self.config.max_context_length] + "..."
            
            # Step 4: Generate with HF
            system_prompt = """Eres Arthur, el Custodio del Desierto.
Respondes preguntas sobre el juego Dune: Arrakis Dominion basándote en el siguiente contexto.
Sé detallado pero conciso. Si no tienes información, dilo."""

            prompt = f"""Basándote en este contexto:
{context}

Pregunta: {question}

Responde usando EXCLUSIVAMENTE la información del contexto выше. 
Si la respuesta no está en el contexto, indica que no tienes esa información."""

            answer = self.llm.generate(
                prompt=prompt,
                system_prompt=system_prompt,
                max_tokens=self.config.max_tokens,
                temperature=self.config.temperature
            )
            
            return QueryResult(
                answer=answer,
                sources=sources,
                query=question,
                latency_ms=(time.time() - start) * 1000,
                success=True
            )
            
        except Exception as e:
            logger.error(f"Query error: {e}")
            return QueryResult(
                answer="Lo apologies, tengo闹 un problema técnico. Intenta de nuevo.",
                sources=[],
                query=question,
                latency_ms=(time.time() - start) * 1000,
                success=False,
                error=str(e)
            )
    
    def close(self):
        """Close connections"""
        if self.vector_store:
            self.vector_store.close()
        if self.llm:
            self.llm.close()
        self._initialized = False