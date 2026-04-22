"""
Dune-RAG - API de Retrieval Augmented Generation
Sirve como biblioteca para el chatbot
"""

# Este archivo está vacío intencionalmente
# El RAG se importa como paquete desde otros módulos

# Pero puede servir para inicializar y probar
if __name__ == "__main__":
    from rag import VectorRetriever, RetrieverConfig
    
    print("Inicializando Dune-RAG...")
    retriever = VectorRetriever(RetrieverConfig())
    retriever.initialize()
    
    stats = retriever.get_stats()
    print(f"Estado: {stats}")
    
    # Test de retrieval
    docs = retriever.retrieve("¿De qué trata el juego?", n_results=3)
    print(f"\nResultados: {len(docs)} documentos")
    for i, doc in enumerate(docs, 1):
        print(f"{i}. {doc.get('source', 'unknown')}")