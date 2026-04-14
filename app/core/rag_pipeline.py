"""RAG pipeline: ingest PDFs, embed chunks, retrieve relevant context."""

import logging
from pathlib import Path

logger = logging.getLogger(__name__)

try:
    import chromadb
    from app.ingestion.pdf_loader import extract_text_from_pdf
    from app.ingestion.chunker import chunk_text
    from app.ingestion.embedder import get_embedding_function
    CHROMADB_AVAILABLE = True
except ImportError:
    CHROMADB_AVAILABLE = False
    logger.warning("ChromaDB not installed — RAG pipeline disabled. Install with: pip install chromadb")

from app.config import get_settings


class RAGPipeline:
    """Retrieval-Augmented Generation pipeline for service manuals."""

    def __init__(self):
        settings = get_settings()
        persist_dir = settings.chroma_persist_dir
        collection_name = settings.chroma_collection_name

        self.chroma_client = chromadb.PersistentClient(path=persist_dir)
        self.embedding_fn = get_embedding_function()
        self.collection = self.chroma_client.get_or_create_collection(
            name=collection_name,
            embedding_function=self.embedding_fn,
            metadata={"hnsw:space": "cosine"},
        )

    def ingest_pdf(self, pdf_path: str | Path, metadata: dict | None = None) -> int:
        """Ingest a PDF into the vector store.

        Returns the number of chunks created.
        """
        pdf_path = Path(pdf_path)
        text = extract_text_from_pdf(pdf_path)
        chunks = chunk_text(text, source=pdf_path.name)

        if not chunks:
            return 0

        ids = [f"{pdf_path.stem}_{i}" for i in range(len(chunks))]
        documents = [c["text"] for c in chunks]
        metadatas = []
        for c in chunks:
            meta = {
                "source": c["source"],
                "chunk_index": c["chunk_index"],
            }
            if metadata:
                meta.update(metadata)
            metadatas.append(meta)

        self.collection.upsert(ids=ids, documents=documents, metadatas=metadatas)
        return len(chunks)

    def retrieve(self, query: str, n_results: int = 5) -> list[dict]:
        """Retrieve relevant chunks for a query.

        Returns list of dicts with 'content', 'source', and 'relevance_score'.
        """
        if self.collection.count() == 0:
            return []

        results = self.collection.query(
            query_texts=[query],
            n_results=min(n_results, self.collection.count()),
        )

        retrieved = []
        for i in range(len(results["documents"][0])):
            retrieved.append(
                {
                    "content": results["documents"][0][i],
                    "source": results["metadatas"][0][i].get("source", "unknown"),
                    "relevance_score": 1 - results["distances"][0][i],  # cosine: lower distance = higher relevance
                }
            )

        return retrieved

    def build_context_string(self, query: str, n_results: int = 5) -> str | None:
        """Retrieve and format context for injection into a Claude prompt.

        Returns None if no relevant context is found.
        """
        results = self.retrieve(query, n_results)
        if not results:
            return None

        context_parts = []
        sources_seen = set()
        for r in results:
            source = r["source"]
            score = r["relevance_score"]
            if score < 0.3:  # Skip low-relevance results
                continue
            context_parts.append(f"[Source: {source} | Relevance: {score:.2f}]\n{r['content']}")
            sources_seen.add(source)

        if not context_parts:
            return None

        return "\n\n---\n\n".join(context_parts)

    def get_stats(self) -> dict:
        """Get collection statistics."""
        return {
            "total_chunks": self.collection.count(),
            "collection_name": self.collection.name,
        }


# Singleton
_pipeline: RAGPipeline | None = None


def get_rag_pipeline() -> RAGPipeline | None:
    """Get the RAG pipeline singleton. Returns None if ChromaDB is not installed."""
    global _pipeline
    if not CHROMADB_AVAILABLE:
        return None
    if _pipeline is None:
        _pipeline = RAGPipeline()
    return _pipeline
