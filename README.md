# Dune-RAG

Retrieval Augmented Generation para el chatbot de Dune: Arrakis Dominion.

## Uso como biblioteca

```python
from rag import VectorRetriever, ResponseGenerator, RetrieverConfig, GeneratorConfig

# Inicializar retriever
retriever = VectorRetriever()
retriever.initialize()

# Buscar documentos
docs = retriever.retrieve("¿De qué trata el juego?", n_results=5)

# Generar respuesta
generator = ResponseGenerator()
generator.initialize()
response = generator.generate("¿Cómo se juega?", documents=docs)
```

## Despliegue

Este repositorio se despliega en HuggingFace Spaces y se consume desde Dune-Chatbot.
