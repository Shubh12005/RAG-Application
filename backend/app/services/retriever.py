from typing import List, Dict, Any, Optional, Tuple
from pydantic import BaseModel
from .embeddings import get_embedding_service, EmbeddingService
from .vector_store import get_vector_store, VectorStoreService
from ..config import settings
import logging

logger = logging.getLogger(__name__)

class RetrievedSource(BaseModel):
    chunk_id: str
    document_id: str
    document_name: str
    page: Optional[int] = None
    section: Optional[str] = None
    chunk_index: int
    text: str
    similarity_score: float

class RetrieverService:
    """
    Coordinates query embedding and vector store similarity search.
    Constructs clean, annotated context for LLM prompt generation.
    """

    def __init__(
        self,
        embedding_service: Optional[EmbeddingService] = None,
        vector_store: Optional[VectorStoreService] = None
    ):
        self.embedding_service = embedding_service or get_embedding_service()
        self.vector_store = vector_store or get_vector_store()

    def retrieve(
        self,
        query: str,
        top_k: Optional[int] = None,
        document_ids: Optional[List[str]] = None
    ) -> Tuple[List[RetrievedSource], str]:
        """
        Retrieves the top-k most relevant chunks for a question.
        Returns:
            Tuple of (List[RetrievedSource], formatted_context_str)
        """
        if not query or not query.strip():
            raise ValueError("Query string cannot be empty.")

        k = top_k if top_k and top_k > 0 else settings.TOP_K

        # 1. Convert question to embedding vector
        query_embedding = self.embedding_service.embed_query(query.strip())

        # 2. Similarity search in vector store
        raw_results = self.vector_store.search(
            query_embedding=query_embedding,
            top_k=k,
            document_ids=document_ids
        )

        sources: List[RetrievedSource] = []
        context_blocks: List[str] = []

        for idx, item in enumerate(raw_results, start=1):
            source = RetrievedSource(
                chunk_id=item["chunk_id"],
                document_id=item["document_id"],
                document_name=item["document_name"],
                page=item["page"],
                section=item["section"],
                chunk_index=item["chunk_index"],
                text=item["text"],
                similarity_score=item["similarity_score"]
            )
            sources.append(source)

            page_info = f"Page {source.page}" if source.page else f"Section: {source.section or 'General'}"
            context_blocks.append(
                f"--- SOURCE [{idx}] ---\n"
                f"Document: {source.document_name} ({page_info})\n"
                f"Content:\n{source.text.strip()}\n"
            )

        formatted_context = "\n".join(context_blocks)
        return sources, formatted_context

_retriever_instance = None

def get_retriever() -> RetrieverService:
    global _retriever_instance
    if _retriever_instance is None:
        _retriever_instance = RetrieverService()
    return _retriever_instance
