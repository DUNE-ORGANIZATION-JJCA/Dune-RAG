"""
Módulo de generación de respuestas - LLM + Prompt Engineering
"""

import os
import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

from langchain_huggingface import HuggingFaceEndpoint
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser

logger = logging.getLogger(__name__)


# ============================================
# CONFIGURACIÓN
# ============================================

@dataclass
class GeneratorConfig:
    """Configuración del generador"""
    model_id: str = "meta-llama/Llama-3.1-8B-Instruct"  # Modelo principal
    model_quantized: str = "meta-llama/Llama-3.1-8B-Instruct-Q4_K_M"  # Quantized (más rápido)
    use_quantized: bool = True  # Usar versión quantizada
    max_tokens: int = 1024  # Máximo de tokens en respuesta
    temperature: float = 0.7  # Creatividad (0.0 = preciso, 1.0 = creativo)
    top_p: float = 0.9  # Nucleus sampling
    huggingface_token: str = None  # Token de HF (se puede pasar como env var)


# ============================================
# PROMPT TEMPLATES
# ============================================

SYSTEM_PROMPT = """Eres DUNE BOT, el asistente oficial del juego "Dune: Arrakis Dominion Distributed".

TU rol:
- Conoces TODO sobre el universo Dune, el juego, la campaña y la tienda
- Respondes de forma clara, precisa y en español
- Usas el contexto proporcionado para dar respuestas fundamentadas
- Si no tienes suficiente información, lo admite honestamente

INSTRUCCIONES:
1. Utiliza siempre la información del contexto (documentos, base de datos)
2. Si la pregunta no tiene relación con Dune, responde que solo puede ayudar sobre Dune
3. Sé conciso pero completo en tus respuestas
4. Incluye fuentes cuando sea relevante

CONTEXTO DEL JUEGO:
- Juego de estrategia/gestión de recursos ambientado en Dune
- Controlas una Casa Menor en Arrakis
- Gestión de extracción de especia, construcción de enclaves
- Múltiples Casas: Atreides, Harkonnen, Corrino, etc.
- El recurso principal es la Melange (especia)
"""

# Template para el prompt final
QUESTION_TEMPLATE = """Basándote en el siguiente contexto, responde a la pregunta del usuario.

Contexto:
{context}

Pregunta: {question}

Respuesta:"""


# ============================================
# GENERADOR PRINCIPAL
# ============================================

class ResponseGenerator:
    """
    Genera respuestas usando LLM de HuggingFace con contexto del RAG
    """
    
    def __init__(self, config: GeneratorConfig = None):
        self.config = config or GeneratorConfig()
        self.llm = None
        self.prompt_template = None
        self._initialized = False
    
    def initialize(self):
        """Inicializa el LLM"""
        if self._initialized:
            return
        
        logger.info("Inicializando generador...")
        
        # Obtener token
        token = self.config.huggingface_token or os.getenv("HF_TOKEN")
        
        if not token:
            logger.warning("No se encontró HF_TOKEN. Define HF_TOKEN o pasa el token.")
        
        # Seleccionar modelo
        model_name = self.config.model_quantized if self.config.use_quantized else self.config.model_id
        logger.info(f"Usando modelo: {model_name}")
        
        try:
            # Crear LLM con HuggingFace Endpoint
            self.llm = HuggingFaceEndpoint(
                endpoint_url=f"https://api-inference.huggingface.co/models/{model_name}",
                huggingfacehub_api_token=token,
                max_new_tokens=self.config.max_tokens,
                temperature=self.config.temperature,
                top_p=self.config.top_p,
                repo_id=model_name,
                task="text-generation"
            )
            
            # Crear prompt template
            self.prompt_template = PromptTemplate(
                template=QUESTION_TEMPLATE,
                input_variables=["context", "question"]
            )
            
            self._initialized = True
            logger.info("Generador inicializado correctamente")
            
        except Exception as e:
            logger.error(f"Error inicializando generador: {e}")
            raise
    
    def generate(
        self, 
        question: str, 
        context_text: str = None,
        documents: List[Dict[str, Any]] = None
    ) -> str:
        """
        Genera una respuesta
        
        Args:
            question: Pregunta del usuario
            context_text: Contexto directo (string)
            documents: Lista de documentos del retriever
            
        Returns:
            Respuesta generada
        """
        if not self._initialized:
            self.initialize()
        
        # Preparar contexto
        if context_text:
            context = context_text
        elif documents:
            context = self._format_documents(documents)
        else:
            context = "No hay información de contexto disponible."
        
        # Verificar si hay contexto útil
        if not context or context == "No hay información de contexto disponible.":
            return "Lo siento, no tengo información suficiente para responder a esa pregunta sobre Dune. ¿Puedes preguntarme sobre otro aspecto del juego?"
        
        try:
            # Generar respuesta
            chain = self.prompt_template | self.llm | StrOutputParser()
            
            response = chain.invoke({
                "context": context,
                "question": question
            })
            
            return response.strip()
            
        except Exception as e:
            logger.error(f"Error generando respuesta: {e}")
            return f"Disculpa, tuve un problema al generar la respuesta. Error: {str(e)}"
    
    def _format_documents(self, documents: List[Dict[str, Any]]) -> str:
        """Formatea documentos para el prompt"""
        if not documents:
            return ""
        
        formatted = []
        
        for i, doc in enumerate(documents, 1):
            source = doc.get("source", "desconocido")
            title = doc.get("title", "")[:100]
            text = doc.get("text", "")
            
            # Limitar longitud
            if len(text) > 1500:
                text = text[:1500] + "..."
            
            formatted.append(
                f"[Documento {i}] {source}\n"
                f"Título: {title}\n"
                f"Contenido: {text}"
            )
        
        return "\n\n".join(formatted)


# ============================================
# FACTORY
# ============================================

def create_generator(config: GeneratorConfig = None) -> ResponseGenerator:
    """Crea y retorna un generador inicializado"""
    generator = ResponseGenerator(config)
    generator.initialize()
    return generator