"""
Arthur Pipeline - Pipeline de procesamiento de Arthur
===========================================
Maneja consultas con personalidad, contexto y modos.
"""

import os
import json
import logging
from typing import Dict, Any, Optional, List
from dataclasses import dataclass

from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer
from qdrant_client import QdrantClient
import httpx

from ingest.personality import (
    build_arthur_system_prompt,
    ARTHUR_RULES,
    ARTHUR_MODES
)

# Importar sistema de aprendizaje (sin romper nada si no existe)
try:
    from ingest.arthur_learner import learn_from_chat, get_learned_context
    LEARNING_ENABLED = True
except ImportError:
    LEARNING_ENABLED = False
    def learn_from_chat(*args, **kwargs): pass
    def get_learned_context(*args, **kwargs): return ""

load_dotenv()

logger = logging.getLogger(__name__)


@dataclass
class ArthurConfig:
    """Configuración del pipeline de Arthur"""
    top_k: int = 5
    qdrant_url: str = "http://localhost:6333"
    qdrant_collection: str = "dune_knowledge"
    ollama_url: str = "http://localhost:11434"
    ollama_model: str = "qwen2.5:3b"
    sbert_model: str = "all-MiniLM-L6-v2"
    max_context_length: int = 3000
    temperature: float = 0.2
    max_tokens: int = 600
    default_mode: str = "contextual"


@dataclass
class ArthurQueryRequest:
    """Request para query de Arthur"""
    question: str
    mode: str = "contextual"
    game_state: Optional[Dict] = None
    player_history: Optional[Dict] = None
    player_id: Optional[str] = None


@dataclass
class ArthurResponse:
    """Response de Arthur"""
    answer: str
    sources: List[Dict[str, Any]]
    mode_used: str
    arthur_tone: bool = True
    success: bool = True
    error: Optional[str] = None


class ArthurPipeline:
    """
    Pipeline principal de Arthur.
    
    Maneja:
    - Consultas con personalidad
    - Múltiples modos (contextual, strategic, narrative, etc.)
    - Contexto de juego y jugador
    - Personalización
    """
    
    def __init__(self, config: ArthurConfig = None):
        self.config = config or ArthurConfig()
        self.embedder = None
        self.qdrant_client = None
        self._initialized = False
    
    def initialize(self):
        """Inicializa componentes del pipeline."""
        if self._initialized:
            return
        
        logger.info("Inicializando Arthur Pipeline...")
        
        # Cargar embedder
        logger.info(f"Cargando embedder: {self.config.sbert_model}")
        self.embedder = SentenceTransformer(self.config.sbert_model)
        
        # Conectar a Qdrant
        url = self.config.qdrant_url
        if "://" in url:
            host = url.split("://")[1].split(":")[0]
            port = int(url.split(":")[-1]) if ":" in url else 6333
            self.qdrant_client = QdrantClient(host=host, port=port)
        else:
            self.qdrant_client = QdrantClient(host=self.config.qdrant_url)
        
        self._initialized = True
        logger.info("Arthur Pipeline inicializado")
    
    def query(self, request: ArthurQueryRequest) -> ArthurResponse:
        """
        Procesa una consulta a través de Arthur.
        
        Args:
            request: ArthurQueryRequest con pregunta, modo, estado, etc.
            
        Returns:
            ArthurResponse con respuesta personalidada
        """
        import time
        start = time.time()
        
        try:
            self.initialize()
            
            # Verificar modo válido
            mode = request.mode if request.mode in ARTHUR_MODES else self.config.default_mode
            
            # Buscar contexto en Qdrant
            context, sources = self._retrieve_context(request.question)
            
            # AÑADIR contexto aprendido previamente (autoaprendizaje)
            if LEARNING_ENABLED:
                learned = get_learned_context(request.question)
                if learned:
                    context = learned + "\n\n" + context
            
            # Construir system prompt de Arthur
            system_prompt = build_arthur_system_prompt(
                game_state=request.game_state,
                player_history=request.player_history,
                context=f"Modo: {mode}"
            )
            
            # Generar respuesta con Ollama
            answer = self._generate(
                question=request.question,
                context=context,
                system_prompt=system_prompt,
                mode=mode
            )
            
            # Post-procesar para asegurar calidad
            answer = self._apply_arthur_rules(answer)
            
            # GUARDAR aprendizaje (si respuesta exitosa)
            if LEARNING_ENABLED and len(answer) > 50:
                learn_from_chat(request.question, answer, request.player_id or "default")
            
            latency = (time.time() - start) * 1000
            
            return ArthurResponse(
                answer=answer,
                sources=sources[:3],
                mode_used=mode,
                arthur_tone=True,
                success=True
            )
            
        except Exception as e:
            logger.error(f"Arthur query error: {e}")
            latency = (time.time() - start) * 1000
            
            return ArthurResponse(
                answer=self._fallback_response(),
                sources=[],
                mode_used=request.mode or self.config.default_mode,
                arthur_tone=False,
                success=False,
                error=str(e)
            )
    
    def _retrieve_context(self, question: str) -> tuple:
        """Recupera contexto relevante de Qdrant."""
        try:
            query_embedding = self.embedder.encode(question).tolist()
            
            results = self.qdrant_client.query_points(
                collection_name=self.config.qdrant_collection,
                query=query_embedding,
                limit=self.config.top_k
            )
            
            points = results.points if hasattr(results, 'points') else results
            
            contexts = []
            sources = []
            
            for result in points:
                payload = result.payload
                contexts.append(payload.get("text", ""))
                sources.append({
                    "text": payload.get("text", "")[:200] + "...",
                    "source": payload.get("source", "unknown"),
                    "title": payload.get("title", ""),
                    "score": result.score
                })
            
            context = "\n\n".join(contexts[:3])
            return context, sources
            
        except Exception as e:
            logger.error(f"Context retrieval error: {e}")
            return "", []
    
    def _generate(self, question: str, context: str, system_prompt: str, mode: str) -> str:
        """Genera respuesta usando Ollama."""
        
        # Prompt optimizado
        prompt_text = f"""Eres Arthur, el Custodio del Desierto.

Responde en ESPAÑOL a esta pregunta sobre Dune: {question}

Contexto: {context[:2500]}

Responde de forma clara:"""

        try:
            response = httpx.post(
                self.config.ollama_url + "/api/generate",
                json={
                    "model": self.config.ollama_model, 
                    "prompt": prompt_text, 
                    "stream": False, 
                    "options": {
                        "temperature": 0.3, 
                        "num_predict": 600,
                        "top_p": 0.85
                    }
                },
                timeout=90
            )
            response.raise_for_status()
            result = response.json()
            answer = result.get("response", "").strip()
            
            answer = self._clean_response(answer)
            return answer[:2000] if answer else "Sin respuesta."
            
        except Exception as e:
            logger.error(f"Ollama error: {e}")
            return context[:300] if context else "Error."
    
    def _clean_response(self, text: str) -> str:
        """Limpia respuesta - elimina repeticiones y texto copiado."""
        if not text:
            return ""
        
        lines = text.split('\n')
        cleaned = []
        prev = ""
        
        for line in lines:
            line = line.strip()
            # Eliminar líneas duplicadas o muy cortas
            if line and line != prev and len(line) > 15:
                # Eliminar si parece copia de la enciclopedia
                if not line.startswith('#') and not line.startswith('##'):
                    cleaned.append(line)
                    prev = line
        
        result = '\n'.join(cleaned)
        
        # Limitar si es muy largo
        if len(result) > 3000:
            return result[:3000] + "\n\n[respuesta truncada]"
        return result
    
    def _fix_repetition(self, text: str) -> str:
        """Elimina repeticiones en el texto."""
        lines = text.split('\n')
        unique_lines = []
        prev_line = ""
        
        for line in lines:
            line = line.strip()
            # Skip líneas duplicadas o muy similares
            if line and line != prev_line and len(line) > 10:
                unique_lines.append(line)
                prev_line = line
        
        result = '\n'.join(unique_lines)
        
        # Si todo repetido, tomar solo la primera parte
        if len(result) < 50:
            # Tomar primeros 500 chars
            return text[:500] + "..."
        
        # Limitar longitud final
        if len(result) > 2000:
            return result[:2000] + "..."
        
        return result
    
    def _summarize_context(self, context: str, question: str) -> str:
        """Resume el contexto cuando hay timeout."""
        # Tomar solo el contenido relevante
        relevant = context[:800]
        return f"Información encontrada: {relevant}\n\nPregunta: {question}\n\nNo pude generar una respuesta completa por límite de tiempo."
    
    def _apply_arthur_rules(self, answer: str) -> str:
        """Aplica reglas de calidad de Arthur."""
        # Reemplazar respuestas genéricas
        for never, always in ARTHUR_RULES["always_do"].items():
            if never.lower() in answer.lower():
                import random
                replacement = random.choice(always)
                answer = answer.replace(never, replacement)
        
        # Asegurar que no está vacío
        if not answer or len(answer.strip()) < 10:
            return self._fallback_response()
        
        return answer
    
    def _fallback_response(self) -> str:
        """Respuesta cuando todo falla."""
        return (
            "Las arenas de Arrakis son misteriosas, y en este momento "
            "mis palabras se pierden en la tormenta. ¿Podrías reformular tu pregunta? "
            "Estoy aquí para guiarte, pero necesito entender qué deseas saber."
        )
    
    def get_stats(self) -> Dict[str, Any]:
        """Obtiene estadísticas del pipeline."""
        if not self._initialized:
            self.initialize()
        
        try:
            info = self.qdrant_client.get_collection(self.config.qdrant_collection)
            return {
                "collection": self.config.qdrant_collection,
                "points": info.points_count,
                "model": self.config.ollama_model,
                "embedder": self.config.sbert_model,
                "modes": list(ARTHUR_MODES.keys())
            }
        except Exception as e:
            return {"error": str(e)}