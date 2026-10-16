import os
import shutil
import uuid
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any

from fastapi import APIRouter, UploadFile, File, HTTPException, status
from pydantic import BaseModel, Field

from ..config import settings
from ..services.document_loader import DocumentLoader, DocumentLoaderError
from ..services.chunker import TextChunker
from ..services.embeddings import get_embedding_service
from ..services.vector_store import get_vector_store
from ..services.retriever import get_retriever
from ..services.llm_service import get_llm_service
from ..services.document_manager import get_document_manager, DocumentRecord

router = APIRouter(prefix="", tags=["RAG"])

# Pydantic models for request/response
class AskRequest(BaseModel):
    question: str = Field(..., min_length=1, description="Question about the uploaded document(s)")
    document_ids: Optional[List[str]] = Field(None, description="Optional list of document IDs to search within")
    top_k: Optional[int] = Field(None, ge=1, le=20, description="Number of chunks to retrieve")

class SourceResponse(BaseModel):
    document: str
    document_id: str
    page: Optional[int] = None
    section: Optional[str] = None
    chunk_id: str
    chunk_index: int
    text: str
    similarity_score: float

class AskResponse(BaseModel):
    answer: str
    sources: List[SourceResponse]
    retrieved_count: int
    llm_provider: str

class SettingsUpdateRequest(BaseModel):
    chunk_size: Optional[int] = Field(None, ge=100, le=4000)
    chunk_overlap: Optional[int] = Field(None, ge=0, le=1000)
    top_k: Optional[int] = Field(None, ge=1, le=20)
    llm_provider: Optional[str] = None
    gemini_api_key: Optional[str] = None
    openai_api_key: Optional[str] = None

def format_file_size(size_bytes: int) -> str:
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    else:
        return f"{size_bytes / (1024 * 1024):.2f} MB"

@router.get("/health")
def health_check():
    """Returns application health status, vector count, and model diagnostics."""
    vstore = get_vector_store()
    doc_manager = get_document_manager()
    llm = get_llm_service()

    return {
        "status": "healthy",
        "app_name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "vector_count": vstore.count(),
        "document_count": len(doc_manager.list_all()),
        "embedding_model": settings.EMBEDDING_MODEL,
        "llm": llm.get_status(),
        "config": {
            "chunk_size": settings.CHUNK_SIZE,
            "chunk_overlap": settings.CHUNK_OVERLAP,
            "top_k": settings.TOP_K,
        }
    }

@router.post("/upload")
async def upload_document(file: UploadFile = File(...)):
    """
    Uploads a document, extracts text, chunks it, generates embeddings,
    and stores them in the local vector database.
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file selected for upload.")

    filename = Path(file.filename).name
    ext = Path(filename).suffix.lower()

    if ext not in settings.ALLOWED_EXTENSIONS:
        allowed = ", ".join(sorted(settings.ALLOWED_EXTENSIONS))
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file format '{ext}'. Supported formats: {allowed}"
        )

    # Generate document ID and destination path
    doc_id = f"doc_{int(datetime.now().timestamp())}_{uuid.uuid4().hex[:6]}"
    safe_stored_filename = f"{doc_id}_{filename}"
    file_path = settings.UPLOADS_DIR / safe_stored_filename

    # Save uploaded bytes to local disk
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save file: {str(e)}")

    file_size = file_path.stat().st_size
    if file_size == 0:
        file_path.unlink(missing_ok=True)
        raise HTTPException(status_code=400, detail=f"The uploaded file '{filename}' is empty (0 bytes).")

    # Step 1 & 2: Extract text and validate structure
    try:
        segments = DocumentLoader.load(file_path)
    except DocumentLoaderError as de:
        file_path.unlink(missing_ok=True)
        raise HTTPException(status_code=400, detail=str(de))
    except Exception as e:
        file_path.unlink(missing_ok=True)
        raise HTTPException(status_code=500, detail=f"Unexpected error while extracting text: {str(e)}")

    # Step 3: Chunking
    try:
        chunker = TextChunker(chunk_size=settings.CHUNK_SIZE, chunk_overlap=settings.CHUNK_OVERLAP)
        chunks = chunker.chunk_segments(doc_id, filename, segments)
    except Exception as ce:
        file_path.unlink(missing_ok=True)
        raise HTTPException(status_code=500, detail=f"Chunking failed: {str(ce)}")

    if not chunks:
        file_path.unlink(missing_ok=True)
        raise HTTPException(status_code=400, detail=f"No usable content could be extracted from '{filename}'.")

    # Step 4: Embedding generation
    try:
        embedder = get_embedding_service()
        chunk_texts = [c.text for c in chunks]
        embeddings = embedder.embed_documents(chunk_texts)
    except Exception as ee:
        file_path.unlink(missing_ok=True)
        raise HTTPException(status_code=500, detail=f"Local embedding generation failed: {str(ee)}")

    # Step 5: Store in Vector Database
    try:
        vstore = get_vector_store()
        vstore.add_chunks(chunks, embeddings)
    except Exception as ve:
        file_path.unlink(missing_ok=True)
        raise HTTPException(status_code=500, detail=f"Vector database storage failed: {str(ve)}")

    # Determine page count representation
    pages = [s.page for s in segments if s.page is not None]
    page_count = max(pages) if pages else 1

    # Save document record metadata
    doc_manager = get_document_manager()
    record = DocumentRecord(
        document_id=doc_id,
        filename=filename,
        file_type=ext.lstrip("."),
        file_size_bytes=file_size,
        file_size_formatted=format_file_size(file_size),
        file_path=str(file_path),
        uploaded_at=datetime.now().isoformat(),
        page_count=page_count,
        chunk_count=len(chunks),
        status="ready",
        summary_preview=chunks[0].text[:200] + "..." if chunks else None
    )
    doc_manager.save(record)

    return {
        "message": f"Document '{filename}' successfully processed and indexed.",
        "document": record
    }

@router.post("/ask", response_model=AskResponse)
async def ask_question(request: AskRequest):
    """
    Semantic retrieval-augmented question answering.
    Converts question to embedding, queries vector database, formats context,
    and prompts the LLM with anti-hallucination safeguards.
    """
    question = request.question.strip()
    if not question:
        raise HTTPException(status_code=400, detail="Question cannot be empty.")

    doc_manager = get_document_manager()
    if not doc_manager.list_all():
        raise HTTPException(
            status_code=400,
            detail="No documents have been uploaded yet. Please upload a document before asking questions."
        )

    # 1. Retrieve top relevant chunks from vector store
    retriever = get_retriever()
    try:
        sources, context_str = retriever.retrieve(
            query=question,
            top_k=request.top_k,
            document_ids=request.document_ids
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Retrieval error: {str(e)}")

    if not sources:
        return AskResponse(
            answer="I could not find this information in the uploaded document.",
            sources=[],
            retrieved_count=0,
            llm_provider=settings.LLM_PROVIDER
        )

    # 2. Call LLM Service
    llm = get_llm_service()
    try:
        answer = llm.generate_answer(
            question=question,
            retrieved_sources=sources,
            context_text=context_str
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"LLM generation failed: {str(e)}")

    # 3. Format structured sources
    formatted_sources = [
        SourceResponse(
            document=s.document_name,
            document_id=s.document_id,
            page=s.page,
            section=s.section,
            chunk_id=s.chunk_id,
            chunk_index=s.chunk_index,
            text=s.text,
            similarity_score=s.similarity_score
        )
        for s in sources
    ]

    return AskResponse(
        answer=answer,
        sources=formatted_sources,
        retrieved_count=len(formatted_sources),
        llm_provider=llm.get_status()["active_provider"]
    )

@router.get("/documents")
def list_documents():
    """Lists all uploaded documents with metadata."""
    doc_manager = get_document_manager()
    return {"documents": doc_manager.list_all()}

@router.get("/documents/{document_id}")
def get_document(document_id: str):
    """Retrieves metadata for a specific document."""
    doc_manager = get_document_manager()
    doc = doc_manager.get(document_id)
    if not doc:
        raise HTTPException(status_code=404, detail=f"Document '{document_id}' not found.")
    return {"document": doc}

@router.delete("/documents/{document_id}")
def delete_document(document_id: str):
    """Deletes a document from disk, removes its chunks from vector DB and metadata."""
    doc_manager = get_document_manager()
    doc = doc_manager.get(document_id)
    if not doc:
        raise HTTPException(status_code=404, detail=f"Document '{document_id}' not found.")

    # Remove from vector store
    vstore = get_vector_store()
    vstore.delete_document(document_id)

    # Remove from metadata & disk
    doc_manager.delete(document_id)

    return {"message": f"Document '{doc.filename}' was deleted successfully."}

@router.post("/documents/{document_id}/clear")
def clear_document_chunks(document_id: str):
    """Clears indexed chunks of a document from the vector store while retaining metadata."""
    doc_manager = get_document_manager()
    doc = doc_manager.get(document_id)
    if not doc:
        raise HTTPException(status_code=404, detail=f"Document '{document_id}' not found.")

    vstore = get_vector_store()
    vstore.delete_document(document_id)

    doc.chunk_count = 0
    doc_manager.save(doc)

    return {"message": f"Vector chunks cleared for '{doc.filename}'."}

@router.post("/clear-all")
def clear_all_documents():
    """Deletes all documents, uploaded files, and resets vector database."""
    vstore = get_vector_store()
    vstore.clear_all()

    doc_manager = get_document_manager()
    doc_manager.clear_all()

    return {"message": "All documents and vector embeddings have been cleared."}

@router.get("/settings")
def get_settings():
    llm = get_llm_service()
    return {
        "chunk_size": settings.CHUNK_SIZE,
        "chunk_overlap": settings.CHUNK_OVERLAP,
        "top_k": settings.TOP_K,
        "llm_provider": settings.LLM_PROVIDER,
        "llm_status": llm.get_status()
    }

@router.post("/settings")
def update_settings(req: SettingsUpdateRequest):
    if req.chunk_size is not None:
        settings.CHUNK_SIZE = req.chunk_size
    if req.chunk_overlap is not None:
        settings.CHUNK_OVERLAP = req.chunk_overlap
    if req.top_k is not None:
        settings.TOP_K = req.top_k
    if req.llm_provider is not None:
        settings.LLM_PROVIDER = req.llm_provider.lower()
    if req.gemini_api_key is not None:
        settings.GEMINI_API_KEY = req.gemini_api_key
        # Refresh LLM service
        llm = get_llm_service()
        llm.gemini_key = req.gemini_api_key
        llm._init_providers()
    if req.openai_api_key is not None:
        settings.OPENAI_API_KEY = req.openai_api_key
        # Refresh LLM service
        llm = get_llm_service()
        llm.openai_key = req.openai_api_key
        llm._init_providers()

    return {"message": "Settings updated successfully", "settings": get_settings()}
