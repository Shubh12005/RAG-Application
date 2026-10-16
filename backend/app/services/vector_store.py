from typing import List, Dict, Any, Optional
import chromadb
from chromadb.config import Settings as ChromaSettings
import logging
from ..config import settings
from .chunker import DocumentChunk

logger = logging.getLogger(__name__)

class VectorStoreService:
    """
    Persistent Vector Store built on Chroma.
    Supports storing document chunks with embeddings and metadata,
    filtering by document IDs, and semantic similarity search.
    """

    COLLECTION_NAME = "rag_knowledge_base"

    def __init__(self, persist_directory: Optional[str] = None):
        self.persist_dir = persist_directory or str(settings.VECTOR_STORE_DIR)
        logger.info(f"Initializing Chroma persistent vector store at: {self.persist_dir}")
        self.client = chromadb.PersistentClient(
            path=self.persist_dir,
            settings=ChromaSettings(anonymized_telemetry=False)
        )
        self.collection = self.client.get_or_create_collection(
            name=self.COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"}
        )

    def add_chunks(self, chunks: List[DocumentChunk], embeddings: List[List[float]]) -> None:
        """Adds or updates chunks and their embeddings into Chroma."""
        if not chunks:
            return

        if len(chunks) != len(embeddings):
            raise ValueError(f"Chunk count ({len(chunks)}) does not match embeddings count ({len(embeddings)})")

        ids = [c.chunk_id for c in chunks]
        docs = [c.text for c in chunks]
        metadatas = [
            {
                "document_id": c.document_id,
                "document_name": c.document_name,
                "page": int(c.page) if c.page is not None else 0,
                "section": c.section or "General",
                "chunk_index": int(c.chunk_index),
                "char_count": int(c.char_count),
            }
            for c in chunks
        ]

        # Chroma handles batches nicely
        batch_size = 250
        for i in range(0, len(ids), batch_size):
            end_idx = i + batch_size
            self.collection.upsert(
                ids=ids[i:end_idx],
                embeddings=embeddings[i:end_idx],
                documents=docs[i:end_idx],
                metadatas=metadatas[i:end_idx]
            )

        logger.info(f"Successfully added/updated {len(chunks)} chunks in vector store.")

    def search(
        self,
        query_embedding: List[float],
        top_k: int = 5,
        document_ids: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Executes similarity search on the vector store.
        Optionally filters results to a subset of document_ids.
        """
        if self.collection.count() == 0:
            return []

        where_filter = None
        if document_ids:
            # Filter out empty or whitespace IDs
            valid_ids = [d.strip() for d in document_ids if d and d.strip()]
            if len(valid_ids) == 1:
                where_filter = {"document_id": valid_ids[0]}
            elif len(valid_ids) > 1:
                where_filter = {"document_id": {"$in": valid_ids}}

        total_available = self.collection.count()
        n_results = min(top_k, total_available)
        if n_results <= 0:
            return []

        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results,
            where=where_filter,
            include=["documents", "metadatas", "distances"]
        )

        retrieved: List[Dict[str, Any]] = []
        if not results or not results["ids"] or not results["ids"][0]:
            return []

        ids = results["ids"][0]
        documents = results["documents"][0] if results.get("documents") else []
        metadatas = results["metadatas"][0] if results.get("metadatas") else []
        distances = results["distances"][0] if results.get("distances") else []

        for i in range(len(ids)):
            meta = metadatas[i] if i < len(metadatas) else {}
            dist = distances[i] if i < len(distances) else 0.0
            # In Chroma cosine space, distance is 1 - cos_sim in range [0, 2]
            # Normalizing (2 - dist) / 2 gives intuitive [0, 1] similarity percentage
            sim_score = max(0.0, min(1.0, (2.0 - dist) / 2.0))

            retrieved.append({
                "chunk_id": ids[i],
                "text": documents[i] if i < len(documents) else "",
                "document_id": meta.get("document_id", "unknown"),
                "document_name": meta.get("document_name", "unknown"),
                "page": meta.get("page") if meta.get("page", 0) > 0 else None,
                "section": meta.get("section", "General"),
                "chunk_index": meta.get("chunk_index", 0),
                "distance": dist,
                "similarity_score": round(sim_score, 4)
            })

        return retrieved

    def delete_document(self, document_id: str) -> None:
        """Deletes all chunks belonging to a specific document."""
        try:
            self.collection.delete(where={"document_id": document_id})
            logger.info(f"Deleted vector chunks for document_id: {document_id}")
        except Exception as e:
            logger.warning(f"Error deleting chunks for document_id '{document_id}': {e}")

    def clear_all(self) -> None:
        """Clears all vectors from the database."""
        try:
            self.client.delete_collection(self.COLLECTION_NAME)
        except Exception:
            pass
        self.collection = self.client.get_or_create_collection(
            name=self.COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"}
        )
        logger.info("Cleared all vectors from collection.")

    def count(self) -> int:
        return self.collection.count()

_vector_store_instance = None

def get_vector_store() -> VectorStoreService:
    global _vector_store_instance
    if _vector_store_instance is None:
        _vector_store_instance = VectorStoreService()
    return _vector_store_instance
