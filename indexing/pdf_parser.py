"""PDF parsing for the offline indexing pipeline: PyMuPDF first, falling back
to Docling only when PyMuPDF's output looks poor (scanned/table-heavy PDFs).

Docling is imported lazily, inside _parse_with_docling(), so a normal
PyMuPDF-only run never pays its heavy OCR/layout-model import and
initialization cost - Docling is a rare fallback, not the common path.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from indexing.chunker import SourceDocument

# Below this many extracted characters per page, PyMuPDF's output is treated
# as too poor to trust (likely a scanned page with little/no embedded text
# layer), and the Docling fallback is tried instead.
MIN_CHARS_PER_PAGE = 40


def _parse_with_pymupdf(path: Path) -> tuple[str, int]:
    import pymupdf

    with pymupdf.open(path) as doc:
        text = "\n\n".join(page.get_text() for page in doc)
        return text, doc.page_count


def _parse_with_docling(path: Path) -> str:
    from docling.document_converter import DocumentConverter  # heavy import, lazy on purpose

    converter = DocumentConverter()
    result = converter.convert(str(path))
    return result.document.export_to_markdown()


def _looks_poor(text: str, page_count: int) -> bool:
    if page_count == 0:
        return True
    return (len(text.strip()) / page_count) < MIN_CHARS_PER_PAGE


def parse_pdf(path: Path) -> SourceDocument:
    """Parse one PDF into a SourceDocument, using PyMuPDF unless its output
    looks poor, in which case Docling (OCR/layout-aware) is used instead.
    """
    text, page_count = _parse_with_pymupdf(path)

    if _looks_poor(text, page_count):
        print(
            f"[pdf_parser] '{path.name}' looks poor via PyMuPDF "
            f"({len(text)} chars / {page_count} pages) - trying Docling fallback"
        )
        try:
            text = _parse_with_docling(path)
        except ImportError:
            print(f"[pdf_parser] Docling not installed - keeping PyMuPDF output for '{path.name}'")

    return SourceDocument(
        text=text,
        source=path.stem,
        url_or_filename=path.name,
        doc_type="pdf",
        crawl_or_parse_date=datetime.now(timezone.utc).isoformat(),
    )
