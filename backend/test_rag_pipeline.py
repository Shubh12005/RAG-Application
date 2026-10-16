import os
import sys
from pathlib import Path

# Add backend directory to path
backend_dir = Path(__file__).resolve().parent
sys.path.insert(0, str(backend_dir))

from app.config import settings
from app.services.document_loader import DocumentLoader
from app.services.chunker import TextChunker
from app.services.embeddings import get_embedding_service
from app.services.vector_store import get_vector_store
from app.services.retriever import get_retriever
from app.services.llm_service import get_llm_service

def test_pipeline():
    sample_dir = backend_dir.parent / "sample_documents"
    pdf_file = sample_dir / "Research_Paper.pdf"
    
    print("=" * 60)
    print("1. TESTING DOCUMENT LOADER (PDF)...")
    print("=" * 60)
    segments = DocumentLoader.load(pdf_file)
    print(f"Extracted {len(segments)} page segments from {pdf_file.name}:")
    for s in segments:
        print(f" - Page {s.page}: {len(s.text)} chars | Excerpt: {s.text[:75]}...")
    assert len(segments) >= 3, f"Expected at least 3 pages, got {len(segments)}"

    print("\n" + "=" * 60)
    print("2. TESTING CHUNKER...")
    print("=" * 60)
    chunker = TextChunker(chunk_size=800, chunk_overlap=100)
    chunks = chunker.chunk_segments("test_doc_001", pdf_file.name, segments)
    print(f"Generated {len(chunks)} chunks:")
    for c in chunks[:3]:
        print(f" - Chunk ID: {c.chunk_id} | Page: {c.page} | Len: {c.char_count} chars")
    assert len(chunks) > 0, "No chunks generated!"

    print("\n" + "=" * 60)
    print("3. TESTING EMBEDDINGS (SentenceTransformers)...")
    print("=" * 60)
    embedder = get_embedding_service()
    embeddings = embedder.embed_documents([c.text for c in chunks])
    print(f"Generated {len(embeddings)} vectors. Embedding dimension: {len(embeddings[0])}")
    assert len(embeddings) == len(chunks)
    assert len(embeddings[0]) == 384, f"Expected 384 dims for MiniLM, got {len(embeddings[0])}"

    print("\n" + "=" * 60)
    print("4. TESTING VECTOR STORE (Chroma)...")
    print("=" * 60)
    vstore = get_vector_store()
    vstore.clear_all()
    vstore.add_chunks(chunks, embeddings)
    print(f"Chroma collection count: {vstore.count()} chunks stored.")
    assert vstore.count() == len(chunks)

    print("\n" + "=" * 60)
    print("5. TESTING RETRIEVAL (Semantic Search)...")
    print("=" * 60)
    retriever = get_retriever()
    query = "What is the main objective of this project?"
    sources, context_str = retriever.retrieve(query, top_k=3)
    print(f"Query: '{query}'")
    print(f"Retrieved {len(sources)} sources:")
    for s in sources:
        print(f" -> [{s.document_name} Page {s.page}] Score: {s.similarity_score} | Excerpt: {s.text[:100]}...")
    
    assert len(sources) > 0, "Retrieval returned 0 chunks!"
    assert any(s.page == 1 for s in sources), "Expected Page 1 in top retrieved sources!"
    print("✓ Retrieval accurately identified Page 1 as relevant source!")

    print("\n" + "=" * 60)
    print("6. TESTING LLM SERVICE & PROMPT CONSTRUCTION...")
    print("=" * 60)
    llm = get_llm_service()
    answer = llm.generate_answer(query, sources, context_str)
    print(f"Answer generated:\n{answer}\n")
    assert answer, "Answer was empty"

    print("\n" + "=" * 60)
    print("7. TESTING MULTI-FORMAT LOADERS (DOCX, CSV, MD)...")
    print("=" * 60)
    docx_file = sample_dir / "Project_Specifications.docx"
    docx_segs = DocumentLoader.load(docx_file)
    print(f"DOCX loaded successfully: {len(docx_segs)} sections.")

    csv_file = sample_dir / "benchmarks_dataset.csv"
    csv_segs = DocumentLoader.load(csv_file)
    print(f"CSV loaded successfully: {len(csv_segs)} row batches.")

    md_file = sample_dir / "anti_hallucination_guidelines.md"
    md_segs = DocumentLoader.load(md_file)
    print(f"Markdown loaded successfully: {len(md_segs)} sections.")

    print("\n" + "=" * 60)
    print("✅ ENTIRE RAG PIPELINE TEST PASSED WITH 100% SUCCESS!")
    print("=" * 60)

if __name__ == "__main__":
    test_pipeline()
