"""
RAG package para Dune Chatbot
"""

from .loader import GitHubLoader, SupabaseLoader, NeonLoader, DuneConfig, REPO_FILES
from .chunker import TextChunker, HTMLChunker, process_documents
from .retriever import VectorRetriever, HybridRetriever, RetrieverConfig
from .generator import ResponseGenerator, GeneratorConfig

__all__ = [
    "GitHubLoader",
    "SupabaseLoader", 
    "NeonLoader",
    "DuneConfig",
    "TextChunker",
    "HTMLChunker",
    "process_documents",
    "VectorRetriever",
    "HybridRetriever",
    "RetrieverConfig",
    "ResponseGenerator",
    "GeneratorConfig",
    "REPO_FILES"
]