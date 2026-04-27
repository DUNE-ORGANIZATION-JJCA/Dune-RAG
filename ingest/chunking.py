"""
Text Chunker - Splits text into chunks for embedding
"""

import re
import os
import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

@dataclass
class ChunkConfig:
    """Configuration for chunking"""
    chunk_size: int = int(os.getenv("CHUNK_SIZE", "500"))  # Characters
    chunk_overlap: int = int(os.getenv("CHUNK_OVERLAP", "50"))  # Characters
    min_chunk_size: int = 100  # Minimum characters to keep
    separator: str = "\n\n"  # Paragraph separator

@dataclass
class Chunk:
    """A text chunk with metadata"""
    text: str
    metadata: Dict[str, Any]
    chunk_index: int
    char_count: int

class TextChunker:
    """
    Splits documents into optimal chunks for embedding.
    Uses sentence-aware splitting with overlap.
    """
    
    def __init__(self, config: ChunkConfig = None):
        self.config = config or ChunkConfig()
    
    def chunk(self, text: str, source: str = "unknown", title: str = "") -> List[Chunk]:
        """
        Split text into chunks.
        
        Args:
            text: Text to chunk
            source: Document source (file path or URL)
            title: Document title
            
        Returns:
            List of Chunk objects
        """
        if not text or len(text.strip()) < self.config.min_chunk_size:
            logger.warning(f"Text too short from {source}, skipping")
            return []
        
        # Clean text first
        text = self._clean_text(text)
        
        # Split into paragraphs
        paragraphs = self._split_paragraphs(text)
        
        chunks = []
        current_chunk = ""
        chunk_index = 0
        
        for para in paragraphs:
            # If paragraph is too large, split it
            if len(para) > self.config.chunk_size:
                if current_chunk:
                    chunks.append(self._create_chunk(
                        current_chunk, source, title, chunk_index
                    ))
                    chunk_index += 1
                    current_chunk = ""
                
                # Split large paragraph by sentences
                sub_chunks = self._split_by_sentences(para)
                for sub in sub_chunks:
                    chunks.append(self._create_chunk(sub, source, title, chunk_index))
                    chunk_index += 1
                continue
            
            # Check if paragraph fits in current chunk
            if len(current_chunk) + len(para) + 2 <= self.config.chunk_size:
                current_chunk += self.config.separator + para
            else:
                # Save current chunk if it has enough content
                if len(current_chunk) >= self.config.min_chunk_size:
                    chunks.append(self._create_chunk(
                        current_chunk, source, title, chunk_index
                    ))
                    chunk_index += 1
                else:
                    # Small chunk - merge with next
                    para = current_chunk + self.config.separator + para if current_chunk else para
                
                current_chunk = para
        
        # Don't forget the last chunk
        if current_chunk and len(current_chunk) >= self.config.min_chunk_size:
            chunks.append(self._create_chunk(current_chunk, source, title, chunk_index))
        
        logger.info(f"Created {len(chunks)} chunks from {source}")
        return chunks
    
    def _clean_text(self, text: str) -> str:
        """Clean and normalize text"""
        # Normalize line endings
        text = text.replace("\r\n", "\n").replace("\r", "\n")
        
        # Remove excessive newlines
        text = re.sub(r'\n{3,}', '\n\n', text)
        
        # Remove trailing whitespace from lines
        lines = [line.rstrip() for line in text.split('\n')]
        text = '\n'.join(lines)
        
        return text.strip()
    
    def _split_paragraphs(self, text: str) -> List[str]:
        """Split text into paragraphs"""
        paragraphs = text.split('\n\n')
        return [
            para.strip() for para in paragraphs
            if para.strip() and len(para.strip()) > 20
        ]
    
    def _split_by_sentences(self, text: str) -> List[str]:
        """Split large text by sentences"""
        # Simple sentence splitting
        sentence_endings = r'(?<=[.!?])\s+'
        sentences = re.split(sentence_endings, text)
        
        chunks = []
        current = ""
        
        for sentence in sentences:
            if len(current) + len(sentence) + 1 <= self.config.chunk_size:
                current += " " + sentence if current else sentence
            else:
                if current:
                    chunks.append(current.strip())
                current = sentence
        
        if current:
            chunks.append(current.strip())
        
        return chunks
    
    def _create_chunk(self, text: str, source: str, title: str, index: int) -> Chunk:
        """Create a chunk with metadata"""
        # Extract section from beginning of text
        section = text.split('\n')[0][:80]
        
        return Chunk(
            text=text.strip(),
            metadata={
                "source": source,
                "title": title or section,
                "chunk_index": index,
                "source_type": self._detect_source_type(source)
            },
            chunk_index=index,
            char_count=len(text)
        )
    
    def _detect_source_type(self, source: str) -> str:
        """Detect the type of source"""
        if source.startswith("http"):
            return "web"
        elif source.endswith(".pdf"):
            return "pdf"
        elif source.endswith(".docx"):
            return "docx"
        elif source.endswith(".pptx"):
            return "pptx"
        else:
            return "document"