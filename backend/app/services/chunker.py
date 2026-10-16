from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
import re
from .document_loader import ExtractedSegment

class DocumentChunk(BaseModel):
    chunk_id: str
    document_id: str
    document_name: str
    text: str
    page: Optional[int] = None
    section: Optional[str] = None
    chunk_index: int
    char_count: int
    metadata: Dict[str, Any] = Field(default_factory=dict)

class TextChunker:
    """
    Splits text segments into semantically meaningful chunks with configurable
    size and overlap, preserving page and section provenance.
    """

    def __init__(self, chunk_size: int = 800, chunk_overlap: int = 100):
        if chunk_size <= 0:
            raise ValueError("chunk_size must be positive")
        if chunk_overlap < 0 or chunk_overlap >= chunk_size:
            raise ValueError("chunk_overlap must be non-negative and smaller than chunk_size")

        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.separators = ["\n\n", "\n", ". ", "? ", "! ", "; ", " ", ""]

    def _split_text(self, text: str, separators: List[str]) -> List[str]:
        """Recursively splits text into chunks under self.chunk_size with overlap."""
        final_chunks: List[str] = []
        separator = separators[-1]
        new_separators: List[str] = []

        for i, sep in enumerate(separators):
            if sep == "":
                separator = ""
                break
            if sep in text:
                separator = sep
                new_separators = separators[i + 1:]
                break

        splits = text.split(separator) if separator else list(text)

        current_doc: List[str] = []
        total_len = 0

        for s in splits:
            s_len = len(s) + (len(separator) if current_doc else 0)
            if total_len + s_len > self.chunk_size and current_doc:
                chunk_str = separator.join(current_doc).strip()
                if chunk_str:
                    final_chunks.append(chunk_str)

                # Overlap calculation: keep tail elements whose total length fits chunk_overlap
                while current_doc and total_len > self.chunk_overlap:
                    popped = current_doc.pop(0)
                    total_len -= len(popped) + len(separator)

            current_doc.append(s)
            total_len += s_len

        if current_doc:
            chunk_str = separator.join(current_doc).strip()
            if chunk_str:
                final_chunks.append(chunk_str)

        # Post-process: If any chunk is still larger than chunk_size and we have deeper separators, subdivide it
        refined_chunks: List[str] = []
        for c in final_chunks:
            if len(c) > self.chunk_size and new_separators:
                sub_chunks = self._split_text(c, new_separators)
                refined_chunks.extend(sub_chunks)
            else:
                refined_chunks.append(c)

        return refined_chunks

    def chunk_segments(
        self,
        document_id: str,
        document_name: str,
        segments: List[ExtractedSegment]
    ) -> List[DocumentChunk]:
        """
        Takes extracted segments (each tied to a page/section) and chunks them,
        generating unique chunk IDs and accurate metadata.
        """
        chunks: List[DocumentChunk] = []
        chunk_idx = 0

        for segment in segments:
            text = segment.text.strip()
            if not text:
                continue

            if len(text) <= self.chunk_size:
                text_splits = [text]
            else:
                text_splits = self._split_text(text, self.separators)

            for split_text in text_splits:
                split_text = split_text.strip()
                if not split_text or len(split_text) < 15:
                    # Ignore tiny noise fragments
                    continue

                chunk_id = f"{document_id}_chunk_{chunk_idx:04d}"
                doc_chunk = DocumentChunk(
                    chunk_id=chunk_id,
                    document_id=document_id,
                    document_name=document_name,
                    text=split_text,
                    page=segment.page,
                    section=segment.section,
                    chunk_index=chunk_idx,
                    char_count=len(split_text),
                    metadata={
                        **segment.metadata,
                        "document_id": document_id,
                        "document_name": document_name,
                        "page": segment.page or 0,
                        "section": segment.section or "General",
                    }
                )
                chunks.append(doc_chunk)
                chunk_idx += 1

        return chunks
