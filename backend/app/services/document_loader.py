import os
from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
import re

@dataclass
class ExtractedSegment:
    text: str
    page: Optional[int] = None
    section: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

class DocumentLoaderError(Exception):
    """Custom exception for document loading and parsing errors."""
    pass

class DocumentLoader:
    """
    Robust document loader supporting PDF, DOCX, TXT, CSV, and Markdown.
    Extracts text while preserving page numbers, section headers, and metadata.
    """

    SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".txt", ".csv", ".md", ".markdown"}

    @classmethod
    def validate_file(cls, file_path: Path) -> None:
        if not file_path.exists():
            raise DocumentLoaderError(f"File not found: {file_path.name}")
        
        if file_path.stat().st_size == 0:
            raise DocumentLoaderError(f"The uploaded file '{file_path.name}' is empty (0 bytes).")

        ext = file_path.suffix.lower()
        if ext not in cls.SUPPORTED_EXTENSIONS:
            supported = ", ".join(sorted(cls.SUPPORTED_EXTENSIONS))
            raise DocumentLoaderError(
                f"Unsupported file format '{ext}'. Supported formats: {supported}"
            )

    @classmethod
    def clean_text(cls, text: str) -> str:
        """Cleans extracted text by normalizing whitespace while preserving structure."""
        if not text:
            return ""
        # Replace carriage returns and excessive whitespace
        text = text.replace("\r\n", "\n").replace("\r", "\n")
        # Replace excessive tabs and strange control chars
        text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]", "", text)
        # Collapse more than 3 consecutive newlines to 2
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip()

    @classmethod
    def load(cls, file_path: Path) -> List[ExtractedSegment]:
        """Loads and extracts text segments from the specified file."""
        cls.validate_file(file_path)
        ext = file_path.suffix.lower()

        try:
            if ext == ".pdf":
                return cls._load_pdf(file_path)
            elif ext == ".docx":
                return cls._load_docx(file_path)
            elif ext == ".csv":
                return cls._load_csv(file_path)
            elif ext in {".txt", ".md", ".markdown"}:
                return cls._load_text(file_path)
            else:
                raise DocumentLoaderError(f"Unsupported extension: {ext}")
        except DocumentLoaderError:
            raise
        except Exception as e:
            raise DocumentLoaderError(f"Failed to process {file_path.name}: {str(e)}")

    @classmethod
    def _load_pdf(cls, file_path: Path) -> List[ExtractedSegment]:
        import pypdf

        segments: List[ExtractedSegment] = []
        try:
            reader = pypdf.PdfReader(str(file_path))
            if reader.is_encrypted:
                try:
                    # Attempt empty password decryption
                    reader.decrypt("")
                except Exception:
                    raise DocumentLoaderError(f"PDF '{file_path.name}' is encrypted or password-protected.")

            total_pages = len(reader.pages)
            if total_pages == 0:
                raise DocumentLoaderError(f"PDF '{file_path.name}' contains no readable pages.")

            extracted_any_text = False
            for page_idx, page in enumerate(reader.pages):
                page_num = page_idx + 1
                try:
                    page_text = page.extract_text() or ""
                except Exception as pe:
                    page_text = f"[Error extracting text from page {page_num}: {pe}]"

                cleaned = cls.clean_text(page_text)
                if cleaned:
                    extracted_any_text = True
                    segments.append(
                        ExtractedSegment(
                            text=cleaned,
                            page=page_num,
                            section=f"Page {page_num}",
                            metadata={"total_pages": total_pages}
                        )
                    )

            if not extracted_any_text:
                raise DocumentLoaderError(
                    f"PDF '{file_path.name}' has no extractable text (it might be a scanned image-only PDF)."
                )

            return segments

        except DocumentLoaderError:
            raise
        except Exception as e:
            raise DocumentLoaderError(f"Corrupted or invalid PDF file '{file_path.name}': {str(e)}")

    @classmethod
    def _load_docx(cls, file_path: Path) -> List[ExtractedSegment]:
        import docx

        try:
            doc = docx.Document(str(file_path))
            segments: List[ExtractedSegment] = []
            current_section = "Document Body"
            current_paras: List[str] = []
            section_page_approx = 1

            for p in doc.paragraphs:
                text = p.text.strip()
                if not text:
                    continue

                # Check if paragraph is a heading
                style_name = p.style.name if p.style else ""
                if "Heading" in style_name:
                    if current_paras:
                        combined = cls.clean_text("\n\n".join(current_paras))
                        if combined:
                            segments.append(
                                ExtractedSegment(
                                    text=combined,
                                    page=section_page_approx,
                                    section=current_section
                                )
                            )
                        current_paras = []
                        section_page_approx += 1
                    current_section = text
                else:
                    current_paras.append(text)

            # Also extract table text
            for table_idx, table in enumerate(doc.tables):
                table_rows = []
                for row in table.rows:
                    row_cells = [c.text.strip() for c in row.cells if c.text.strip()]
                    if row_cells:
                        table_rows.append(" | ".join(row_cells))
                if table_rows:
                    current_paras.append(f"Table {table_idx + 1}:\n" + "\n".join(table_rows))

            if current_paras:
                combined = cls.clean_text("\n\n".join(current_paras))
                if combined:
                    segments.append(
                        ExtractedSegment(
                            text=combined,
                            page=section_page_approx,
                            section=current_section
                        )
                    )

            if not segments:
                raise DocumentLoaderError(f"No readable text found in DOCX '{file_path.name}'.")

            return segments

        except DocumentLoaderError:
            raise
        except Exception as e:
            raise DocumentLoaderError(f"Corrupted or invalid DOCX file '{file_path.name}': {str(e)}")

    @classmethod
    def _load_csv(cls, file_path: Path) -> List[ExtractedSegment]:
        import pandas as pd

        try:
            df = pd.read_csv(str(file_path))
            if df.empty:
                raise DocumentLoaderError(f"CSV file '{file_path.name}' is empty.")

            columns = list(df.columns)
            total_rows = len(df)
            segments: List[ExtractedSegment] = []

            # Group rows into batches of 15 rows per segment for readable context
            batch_size = 15
            for i in range(0, total_rows, batch_size):
                batch = df.iloc[i : i + batch_size]
                batch_num = (i // batch_size) + 1
                row_start = i + 1
                row_end = min(i + batch_size, total_rows)

                lines = [f"Columns: {', '.join(str(c) for c in columns)}"]
                for row_idx, row in batch.iterrows():
                    row_desc = ", ".join(f"{col}: {val}" for col, val in row.items() if pd.notna(val))
                    lines.append(f"Row {row_idx + 1}: {row_desc}")

                segment_text = "\n".join(lines)
                segments.append(
                    ExtractedSegment(
                        text=segment_text,
                        page=batch_num,
                        section=f"Rows {row_start}-{row_end}",
                        metadata={"total_rows": total_rows, "columns": columns}
                    )
                )

            return segments

        except DocumentLoaderError:
            raise
        except Exception as e:
            raise DocumentLoaderError(f"Error parsing CSV '{file_path.name}': {str(e)}")

    @classmethod
    def _load_text(cls, file_path: Path) -> List[ExtractedSegment]:
        content = None
        for encoding in ("utf-8", "utf-8-sig", "latin-1", "cp1252"):
            try:
                with open(file_path, "r", encoding=encoding) as f:
                    content = f.read()
                break
            except (UnicodeDecodeError, LookupError):
                continue

        if content is None:
            raise DocumentLoaderError(f"Unable to decode text file '{file_path.name}' with supported encodings.")

        cleaned = cls.clean_text(content)
        if not cleaned:
            raise DocumentLoaderError(f"Text file '{file_path.name}' contains only whitespace.")

        # If markdown, split by major headers if available, or treat as multi-section
        is_md = file_path.suffix.lower() in {".md", ".markdown"}
        if is_md:
            header_pattern = re.compile(r"^(#{1,3}\s+.+)$", re.MULTILINE)
            parts = header_pattern.split(cleaned)
            segments: List[ExtractedSegment] = []
            current_section = "Introduction"
            page_counter = 1

            for part in parts:
                part = part.strip()
                if not part:
                    continue
                if part.startswith("#"):
                    current_section = part.lstrip("#").strip()
                else:
                    segments.append(
                        ExtractedSegment(
                            text=part,
                            page=page_counter,
                            section=current_section
                        )
                    )
                    page_counter += 1

            if segments:
                return segments

        # Plain text fallback
        return [
            ExtractedSegment(
                text=cleaned,
                page=1,
                section="Document Content"
            )
        ]
