"""
Módulo de chunking - divide documentos en fragmentos para embeddings
"""

import re
import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


# ============================================
# CONFIGURACIÓN DE CHUNKING
# ============================================

@dataclass
class ChunkConfig:
    """Configuración para el chunking"""
    chunk_size: int = 500          # Tamaño máximo del chunk (caracteres)
    chunk_overlap: int = 50         # Superposición entre chunks
    min_chunk_size: int = 100      # Tamaño mínimo para mantener
    separator: str = "\n\n"        # Separador de secciones


# ============================================
# CHUNKER PRINCIPAL
# ============================================

class TextChunker:
    """
    Divide texto en chunks óptimos para embeddings
    """
    
    def __init__(self, config: ChunkConfig = None):
        self.config = config or ChunkConfig()
    
    def chunk_text(self, text: str, source: str = "unknown") -> List[Dict[str, Any]]:
        """
        Divide un texto en chunks
        
        Args:
            text: Texto a dividir
            source: Origen del documento
            
        Returns:
            Lista de chunks con metadatos
        """
        if not text or len(text.strip()) < 50:
            logger.warning(f"Texto muy corto de {source}, ignorando")
            return []
        
        # Limpiar texto
        text = self._clean_text(text)
        
        # Estrategia: dividir por párrafos primero, luego recombinar
        chunks = []
        
        # Dividir por párrafos
        paragraphs = self._split_paragraphs(text)
        
        current_chunk = ""
        
        for para in paragraphs:
            # Si el párrafo es muy grande, dividirlo internamente
            if len(para) > self.config.chunk_size:
                if current_chunk:
                    chunks.append(self._create_chunk(current_chunk, source))
                    current_chunk = ""
                
                # Dividir párrafo grande
                sub_chunks = self._split_large_text(para, self.config.chunk_size)
                chunks.extend(sub_chunks)
                continue
            
            # Verificar si cabe en el chunk actual
            if len(current_chunk) + len(para) + 1 <= self.config.chunk_size:
                current_chunk += self.config.separator + para
            else:
                # Guardar chunk actual si tiene contenido suficiente
                if current_chunk and len(current_chunk) >= self.config.min_chunk_size:
                    chunks.append(self._create_chunk(current_chunk, source))
                elif current_chunk:
                    # Si es muy pequeño, añadir al siguiente
                    para = current_chunk + self.config.separator + para
                
                # Nuevo chunk
                current_chunk = para
        
        # Guardar el último chunk
        if current_chunk and len(current_chunk) >= self.config.min_chunk_size:
            chunks.append(self._create_chunk(current_chunk, source))
        
        logger.info(f"Creados {len(chunks)} chunks de {source}")
        return chunks
    
    def _clean_text(self, text: str) -> str:
        """Limpia el texto"""
        # Normalizar saltos de línea
        text = text.replace("\r\n", "\n").replace("\r", "\n")
        
        # Eliminar múltiples saltos de línea consecutivos
        text = re.sub(r'\n{3,}', '\n\n', text)
        
        # Eliminar espacios al final de línea
        lines = [line.rstrip() for line in text.split('\n')]
        text = '\n'.join(lines)
        
        return text.strip()
    
    def _split_paragraphs(self, text: str) -> List[str]:
        """Divide en párrafos"""
        # Usar doble salto de línea como separador de párrafo
        paragraphs = text.split('\n\n')
        
        # Limpiar cada párrafo
        result = []
        for para in paragraphs:
            para = para.strip()
            if para and len(para) > 20:  # Ignorar líneas muy cortas
                result.append(para)
        
        return result
    
    def _split_large_text(self, text: str, max_size: int) -> List[Dict[str, Any]]:
        """Divide texto muy grande en fragmentos más pequeños"""
        chunks = []
        
        # Dividir por oraciones (más limpio que por caracteres)
        sentences = re.split(r'(?<=[.!?])\s+', text)
        
        current = ""
        for sentence in sentences:
            if len(current) + len(sentence) + 1 <= max_size:
                current += " " + sentence
            else:
                if current:
                    chunks.append({"text": current.strip()})
                current = sentence
        
        if current:
            chunks.append({"text": current.strip()})
        
        return chunks
    
    def _create_chunk(self, text: str, source: str) -> Dict[str, Any]:
        """Crea un chunk con metadatos"""
        # Extraer tema/sección del inicio del texto
        title = self._extract_title(text)
        
        return {
            "text": text.strip(),
            "source": source,
            "title": title,
            "char_count": len(text)
        }
    
    def _extract_title(self, text: str) -> str:
        """Extrae el título/sección del inicio del chunk"""
        first_line = text.split('\n')[0].strip()
        
        # Limitar longitud
        if len(first_line) > 80:
            first_line = first_line[:77] + "..."
        
        return first_line


# ============================================
# HTML PARSER
# ============================================

class HTMLChunker(TextChunker):
    """Chunker especial para contenido HTML"""
    
    def chunk_html(self, html: str, url: str = "web") -> List[Dict[str, Any]]:
        """Procesa HTML y lo convierte en chunks de texto"""
        from bs4 import BeautifulSoup
        
        try:
            soup = BeautifulSoup(html, 'html.parser')
            
            # Extraer texto de elementos principales
            sections = []
            
            # Título
            if soup.title:
                sections.append(("title", soup.title.string or ""))
            
            # Headings
            for h in soup.find_all(['h1', 'h2', 'h3']):
                sections.append((h.name, h.get_text(strip=True)))
            
            # Párrafos principales
            for p in soup.find_all('p'):
                text = p.get_text(strip=True)
                if len(text) > 50:  # Solo párrafos con contenido
                    sections.append(("p", text))
            
            # Construir texto
            full_text = ""
            for section_type, content in sections:
                if section_type == "title":
                    full_text += f"# {content}\n\n"
                elif section_type in ["h1", "h2", "h3"]:
                    full_text += f"## {content}\n\n"
                else:
                    full_text += f"{content}\n\n"
            
            # Chunkear el resultado
            return self.chunk_text(full_text, source=url)
            
        except Exception as e:
            logger.error(f"Error parseando HTML: {e}")
            return []


# ============================================
# PROCESADOR DE DOCUMENTOS
# ============================================

def process_documents(
    documents: Dict[str, str],
    chunker: TextChunker = None
) -> List[Dict[str, Any]]:
    """
    Procesa múltiples documentos y los convierte en chunks
    
    Args:
        documents: {"nombre": "contenido"}
        chunker: Instancia de TextChunker
        
    Returns:
        Lista de todos los chunks
    """
    chunker = chunker or TextChunker()
    all_chunks = []
    
    for source, content in documents.items():
        # Detectar tipo de documento
        if source.endswith(".html") or "<html" in content.lower():
            html_chunker = HTMLChunker(chunker.config)
            chunks = html_chunker.chunk_html(content, source)
        else:
            chunks = chunker.chunk_text(content, source)
        
        # Añadir metadatos
        for chunk in chunks:
            chunk["source"] = source
        
        all_chunks.extend(chunks)
    
    logger.info(f"Total chunks creados: {len(all_chunks)}")
    return all_chunks