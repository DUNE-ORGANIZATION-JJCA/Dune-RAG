"""
Módulo de retrieval - recuperación de documentos relevantes usando ChromaDB
"""

import os
import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)


# ============================================
# CONFIGURACIÓN
# ============================================

@dataclass
class RetrieverConfig:
    """Configuración del retriever"""
    collection_name: str = "dune_knowledge"
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"  # Rápido y efectivo
    n_results: int = 5  # Número de resultados a recuperar
    persist_directory: str = "./chroma_db"


# ============================================
# RETRIEVER PRINCIPAL
# ============================================

class VectorRetriever:
    """
    Sistema de retrieval semántico usando ChromaDB + sentence-transformers
    """
    
    def __init__(self, config: RetrieverConfig = None):
        self.config = config or RetrieverConfig()
        self.embeddings = None
        self.collection = None
        self.client = None
        self._initialized = False
    
    def initialize(self, force_recreate: bool = False):
        """Inicializa el retriever"""
        if self._initialized and not force_recreate:
            return
        
        logger.info("Inicializando retriever...")
        
        try:
            # Cargar modelo de embeddings
            logger.info(f"Cargando modelo: {self.config.embedding_model}")
            self.embeddings = SentenceTransformer(self.config.embedding_model)
            
            # Inicializar ChromaDB
            self.client = chromadb.Client(Settings(
                persist_directory=self.config.persist_directory,
                anonymized_telemetry=False
            ))
            
            # Crear o obtener colección
            try:
                self.collection = self.client.get_collection(
                    name=self.config.collection_name
                )
                logger.info(f"Colección '{self.config.collection_name}' obtenida")
            except Exception:
                self.collection = self.client.create_collection(
                    name=self.config.collection_name,
                    metadata={"description": "Base de conocimiento de Dune"}
                )
                logger.info(f"Colección '{self.config.collection_name}' creada")
            
            self._initialized = True
            logger.info("Retriever inicializado correctamente")
            
        except Exception as e:
            logger.error(f"Error inicializando retriever: {e}")
            raise
    
    def add_documents(self, chunks: List[Dict[str, Any]]) -> bool:
        """
        Añade documentos al vector store
        
        Args:
            chunks: Lista de chunks con keys: text, source, title
            
        Returns:
            True si éxito
        """
        if not self._initialized:
            self.initialize()
        
        if not chunks:
            logger.warning("No hay chunks para añadir")
            return False
        
        logger.info(f"Añadiendo {len(chunks)} documentos...")
        
        try:
            # Preparar datos
            texts = [chunk["text"] for chunk in chunks]
            ids = [f"doc_{i}" for i in range(len(chunks))]
            metadatas = [
                {
                    "source": chunk.get("source", "unknown"),
                    "title": chunk.get("title", "")[:200],
                    "char_count": chunk.get("char_count", 0)
                }
                for chunk in chunks
            ]
            
            # Generar embeddings
            logger.info("Generando embeddings...")
            embeddings = self.embeddings.encode(
                texts, 
                show_progress_bar=True,
                convert_to_numpy=True
            )
            
            # Añadir a ChromaDB
            self.collection.add(
                documents=texts,
                ids=ids,
                metadatas=metadatas,
                embeddings=embeddings.tolist()
            )
            
            logger.info(f"Añadidos {len(chunks)} documentos")
            return True
            
        except Exception as e:
            logger.error(f"Error añadiendo documentos: {e}")
            return False
    
    def retrieve(
        self, 
        query: str, 
        n_results: int = None,
        filters: Dict[str, str] = None
    ) -> List[Dict[str, Any]]:
        """
        Recupera documentos relevantes para una query
        
        Args:
            query: Pregunta del usuario
            n_results: Número de resultados
            filters: Filtros por metadatos (ej: {"source": "storytelling"})
            
        Returns:
            Lista de documentos relevantes
        """
        if not self._initialized:
            self.initialize()
        
        n_results = n_results or self.config.n_results
        
        try:
            # Generate query embedding
            query_embedding = self.embeddings.encode(
                query, 
                convert_to_numpy=True
            ).tolist()
            
            # Buscar en ChromaDB
            where = filters or None
            
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=n_results,
                where=where,
                include=["documents", "metadatas", "distances"]
            )
            
            # Formatear resultados
            documents = []
            if results.get("documents") and results["documents"][0]:
                for i, doc in enumerate(results["documents"][0]):
                    documents.append({
                        "text": doc,
                        "source": results["metadatas"][0][i].get("source", "unknown"),
                        "title": results["metadatas"][0][i].get("title", ""),
                        "distance": results["distances"][0][i]
                    })
            
            return documents
            
        except Exception as e:
            logger.error(f"Error en retrieval: {e}")
            return []
    
    def get_stats(self) -> Dict[str, Any]:
        """Obtiene estadísticas de la colección"""
        if not self._initialized:
            self.initialize()
        
        try:
            count = self.collection.count()
            return {
                "collection": self.config.collection_name,
                "document_count": count,
                "embedding_model": self.config.embedding_model,
                "persist_directory": self.config.persist_directory
            }
        except Exception as e:
            return {"error": str(e)}


# ============================================
# HYBRID RETRIEVER
# ============================================

class HybridRetriever:
    """
    Combina búsqueda vectorial + búsqueda exacta
    """
    
    def __init__(self, vector_retriever: VectorRetriever):
        self.vector = vector_retriever
    
    def retrieve(
        self,
        query: str,
        n_results: int = 5,
        use_hybrid: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Retrieval híbrido
        
        1. Búsqueda vectorial principal
        2. Si use_hybrid=True, añade búsqueda por palabras clave
        """
        # Búsqueda vectorial
        results = self.vector.retrieve(query, n_results=n_results)
        
        if not use_hybrid or len(results) >= n_results:
            return results
        
        # Añadir búsqueda por keywords en fuentes específicas
        keywords = self._extract_keywords(query)
        
        for kw in keywords:
            filtered = self.vector.retrieve(
                kw, 
                n_results=3,
                filters={"source": "storytelling"}
            )
            
            # Combinar sin duplicados
            existing_ids = {r["text"][:100] for r in results}
            for doc in filtered:
                if doc["text"][:100] not in existing_ids:
                    results.append(doc)
                    if len(results) >= n_results:
                        break
        
        return results
    
    def _extract_keywords(self, query: str) -> List[str]:
        """Extrae palabras clave de la query"""
        import re
        
        # Limpiar y dividir
        words = re.findall(r'\b\w{4,}\b', query.lower())
        
        # Palabras a ignorar
        stopwords = {
            "como", "para", "esto", "esa", "este", "que", "donde",
            "cuando", "cual", "cuales", "quien", "como", "hacer",
            "tengo", "hay", "puede", "ser", "sobre", "entre"
        }
        
        keywords = [w for w in words if w not in stopwords]
        return keywords[:5]


# ============================================
# FACTORY
# ============================================

def create_retriever(config: RetrieverConfig = None) -> VectorRetriever:
    """Crea y retorna un retriever inicializado"""
    retriever = VectorRetriever(config)
    retriever.initialize()
    return retriever