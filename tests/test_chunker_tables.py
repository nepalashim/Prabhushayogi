"""Unit tests for the markdown-table-atomicity behavior of indexing/chunker.py."""

from __future__ import annotations

from indexing.chunker import SourceDocument, chunk_document


def _make_doc(text: str) -> SourceDocument:
    return SourceDocument(
        text=text,
        source="Test Doc",
        url_or_filename="test.md",
        doc_type="webpage",
        crawl_or_parse_date="2026-08-22T00:00:00Z",
    )


def test_table_stays_in_one_chunk() -> None:
    table = (
        "| Service | Fee |\n"
        "|---|---|\n"
        "| Demat Opening | NPR 500 |\n"
        "| Annual Renewal | NPR 300 |\n"
    )
    text = f"Some intro text before the table.\n\n{table}\nSome text after the table.\n"
    chunks = chunk_document(_make_doc(text))

    table_chunks = [c for c in chunks if c.is_table]
    assert len(table_chunks) == 1
    assert "Demat Opening" in table_chunks[0].text
    assert "Annual Renewal" in table_chunks[0].text


def test_prose_without_tables_has_no_table_chunks() -> None:
    text = "This is plain prose with no tables anywhere in it. " * 5
    chunks = chunk_document(_make_doc(text))
    assert all(not c.is_table for c in chunks)
    assert len(chunks) >= 1


def test_long_prose_is_split_into_multiple_chunks() -> None:
    text = "This is one sentence about Prabhu Capital's services. " * 200
    chunks = chunk_document(_make_doc(text))
    assert len(chunks) > 1


def test_all_chunks_carry_document_metadata() -> None:
    doc = _make_doc("Some short prose about Prabhu Capital.")
    chunks = chunk_document(doc)
    assert len(chunks) == 1
    chunk = chunks[0]
    assert chunk.source == doc.source
    assert chunk.url_or_filename == doc.url_or_filename
    assert chunk.doc_type == doc.doc_type
    assert chunk.crawl_or_parse_date == doc.crawl_or_parse_date
    assert chunk.chunk_id  # non-empty, generated
