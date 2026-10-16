import json
import os
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
from pydantic import BaseModel, Field
import logging
from ..config import settings

logger = logging.getLogger(__name__)

class DocumentRecord(BaseModel):
    document_id: str
    filename: str
    file_type: str
    file_size_bytes: int
    file_size_formatted: str
    file_path: str
    uploaded_at: str
    page_count: int = 1
    chunk_count: int = 0
    status: str = "ready"  # "ready", "processing", "error"
    error_message: Optional[str] = None
    summary_preview: Optional[str] = None

class DocumentManager:
    """
    Manages document metadata persistence on disk (JSON file).
    Allows state recovery across application restarts.
    """

    def __init__(self, metadata_path: Optional[Path] = None):
        self.metadata_file = metadata_path or settings.METADATA_FILE
        self._cache: Dict[str, DocumentRecord] = {}
        self._load()

    def _load(self):
        if self.metadata_file.exists():
            try:
                with open(self.metadata_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self._cache = {
                        item["document_id"]: DocumentRecord(**item)
                        for item in data
                    }
                logger.info(f"Loaded {len(self._cache)} documents from {self.metadata_file.name}")
            except Exception as e:
                logger.error(f"Failed to read metadata file {self.metadata_file}: {e}")
                self._cache = {}
        else:
            self._cache = {}

    def _save(self):
        try:
            temp_path = self.metadata_file.with_suffix(".tmp")
            data = [doc.model_dump() for doc in self._cache.values()]
            with open(temp_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            temp_path.replace(self.metadata_file)
        except Exception as e:
            logger.error(f"Failed to save document metadata: {e}")

    def list_all(self) -> List[DocumentRecord]:
        return sorted(list(self._cache.values()), key=lambda d: d.uploaded_at, reverse=True)

    def get(self, document_id: str) -> Optional[DocumentRecord]:
        return self._cache.get(document_id)

    def save(self, record: DocumentRecord) -> None:
        self._cache[record.document_id] = record
        self._save()

    def delete(self, document_id: str) -> bool:
        if document_id in self._cache:
            record = self._cache.pop(document_id)
            self._save()
            # Also remove physical file if it exists
            try:
                p = Path(record.file_path)
                if p.exists():
                    p.unlink()
            except Exception as e:
                logger.warning(f"Failed to remove file {record.file_path}: {e}")
            return True
        return False

    def clear_all(self) -> None:
        for record in self._cache.values():
            try:
                p = Path(record.file_path)
                if p.exists():
                    p.unlink()
            except Exception:
                pass
        self._cache = {}
        self._save()

_doc_manager_instance = None

def get_document_manager() -> DocumentManager:
    global _doc_manager_instance
    if _doc_manager_instance is None:
        _doc_manager_instance = DocumentManager()
    return _doc_manager_instance
