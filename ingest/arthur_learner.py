"""
Arthur Auto-Learning System
=========================
Sistema de aprendizaje automático para Arthur.
1. Aprendizaje Pasivo: Guarda preguntas/respuestas exitosas
2. Base Creciente: Indexa nuevo conocimiento
3. Simulación: Aprende jugando (FASE 2)
"""

import os
import json
import logging
from datetime import datetime
from typing import Dict, List, Any

from dotenv import load_dotenv
from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct

load_dotenv()
logger = logging.getLogger(__name__)


class ArthurLearner:
    """
    Sistema de auto-aprendizaje de Arthur.
    Guarda conocimiento de cada interacción exitosa.
    """
    
    def __init__(self):
        self.qdrant_url = os.getenv("QDRANT_URL", "http://localhost:6333")
        self.collection = "arthur_learnings"
        self.client = None
        self._initialized = False
    
    def initialize(self):
        """Inicializa la conexión a Qdrant."""
        if self._initialized:
            return
        
        url = self.qdrant_url
        if "://" in url:
            host = url.split("://")[1].split(":")[0]
            port = int(url.split(":")[-1]) if ":" in url else 6333
            self.client = QdrantClient(host=host, port=port)
        
        # Crear colección de aprendizajes si no existe
        try:
            from qdrant_client.models import Distance, VectorParams
            self.client.create_collection(
                self.collection,
                vectors_config=VectorParams(size=384, distance=Distance.COSINE)
            )
            logger.info(f"Created collection: {self.collection}")
        except:
            pass  # Ya existe
        
        self._initialized = True
        logger.info("ArthurLearner initialized")
    
    def learn_from_interaction(
        self,
        question: str,
        answer: str,
        player_id: str = "anonymous",
        rating: float = 1.0
    ):
        """
        Guarda una interacción exitosa para aprendizaje.
        
        Args:
            question: Pregunta del usuario
            answer: Respuesta dada
            player_id: ID del jugador
            rating: Rating de la respuesta (0-1)
        """
        if not question or len(answer) < 50:
            return  # No aprender de respuestas muy cortas
        
        try:
            self.initialize()
            
            # Crear embedding simple de la pregunta
            from sentence_transformers import SentenceTransformer
            embedder = SentenceTransformer("all-MiniLM-L6-v2")
            embedding = embedder.encode(question).tolist()
            
            # Crear punto para Qdrant
            point = PointStruct(
                id=hash(question) % 1000000,
                vector=embedding,
                payload={
                    "type": "interaction",
                    "question": question,
                    "answer": answer[:2000],  # Limitar tamaño
                    "player_id": player_id,
                    "rating": rating,
                    "learned_at": datetime.now().isoformat(),
                    "source": "user_interaction"
                }
            )
            
            self.client.upsert(
                collection_name=self.collection,
                points=[point]
            )
            logger.info(f"Learned from interaction: {question[:50]}...")
            
        except Exception as e:
            logger.error(f"Learning error: {e}")
    
    def get_learned_context(self, question: str) -> str:
        """Obtiene contexto de interacciones pasadas similares."""
        try:
            self.initialize()
            
            from sentence_transformers import SentenceTransformer
            embedder = SentenceTransformer("all-MiniLM-L6-v2")
            embedding = embedder.encode(question).tolist()
            
            results = self.client.query_points(
                collection_name=self.collection,
                query=embedding,
                limit=3
            )
            
            points = results.points if hasattr(results, 'points') else results
            if not points:
                return ""
            
            # Extraer respuestas previas
            learned = []
            for p in points:
                if p.payload.get("rating", 0) > 0.5:  # Solo respuestas bien rating
                    learned.append(p.payload.get("answer", ""))
            
            return "\n\n".join(learned)
            
        except Exception as e:
            logger.error(f"Get learned error: {e}")
            return ""
    
    def get_stats(self) -> Dict[str, Any]:
        """Obtiene estadísticas de aprendizaje."""
        try:
            self.initialize()
            info = self.client.get_collection(self.collection)
            return {
                "collection": self.collection,
                "points": info.points_count,
                "status": "learning"
            }
        except:
            return {"collection": self.collection, "points": 0}


# Sistema de indexación automática de conocimiento
class KnowledgeIndexer:
    """Indexa nuevo conocimiento automáticamente."""
    
    def __init__(self):
        self.docs_folder = "data"
        self.docs_already_indexed_file = ".indexed_docs.json"
    
    def get_pending_docs(self) -> List[str]:
        """Obtiene documentos pendientes de indexar."""
        docs_folder = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            self.docs_folder
        )
        
        if not os.path.exists(docs_folder):
            return []
        
        # Cargar ya indexados
        indexed = []
        if os.path.exists(self.docs_already_indexed_file):
            with open(self.docs_already_indexed_file, 'r') as f:
                indexed = json.load(f)
        
        # Buscar nuevos .md
        pending = []
        for f in os.listdir(docs_folder):
            if f.endswith('.md') and f not in indexed:
                pending.append(f)
        
        return pending
    
    def index_new_docs(self) -> Dict[str, Any]:
        """Indexa documentos nuevos."""
        from ingest import Embedder, QdrantIndexer, TextChunker
        
        pending = self.get_pending_docs()
        if not pending:
            return {"indexed": 0, "pending": 0}
        
        embedder = Embedder()
        indexer = QdrantIndexer()
        chunker = TextChunker()
        
        embedder.initialize()
        indexer.initialize(embedding_dim=384)
        
        total = 0
        for doc in pending:
            try:
                path = os.path.join(self.docs_folder, doc)
                with open(path, 'r', encoding='utf-8') as f:
                    text = f.read()
                
                chunks = chunker.chunk(text=text, source=doc, title=doc)
                chunk_dicts = [
                    {'text': c.text, 'metadata': c.metadata, 'char_count': c.char_count}
                    for c in chunks
                ]
                chunk_dicts = embedder.encode_chunks(chunk_dicts)
                result = indexer.index_chunks(chunk_dicts)
                total += result['indexed']
                
                # Guardar como indexado
                indexed.append(doc)
            except Exception as e:
                logger.error(f"Error indexing {doc}: {e}")
        
        # Guardar lista actualizada
        with open(self.docs_already_indexed_file, 'w') as f:
            json.dump(indexed, f)
        
        return {"indexed": total, "pending": len(pending) - total}


# Instancia global
learner = ArthurLearner()
indexer = KnowledgeIndexer()


def learn_from_chat(question: str, answer: str, player_id: str = "default"):
    """ función para llamar desde el chat - guarda aprendizaje """
    try:
        learner.learn_from_interaction(question, answer, player_id)
    except:
        pass  # Silencioso


def get_learned_context(question: str) -> str:
    """ función para obtener contexto aprendido """
    try:
        return learner.get_learned_context(question)
    except:
        return ""