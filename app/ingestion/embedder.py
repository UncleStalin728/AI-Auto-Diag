"""Embedding function for ChromaDB — uses sentence-transformers (free, local)."""

from chromadb.utils import embedding_functions


def get_embedding_function():
    """Return a ChromaDB-compatible embedding function.

    Uses the all-MiniLM-L6-v2 model from sentence-transformers.
    - Free, runs locally (no API key needed)
    - Good quality for technical/automotive text
    - Fast inference, small model (~80MB)

    To upgrade to Voyage AI (Anthropic partner) for better quality:
        from chromadb.utils.embedding_functions import OpenAIEmbeddingFunction
        # Or implement a custom VoyageAI embedding function
    """
    return embedding_functions.SentenceTransformerEmbeddingFunction(
        model_name="all-MiniLM-L6-v2"
    )
