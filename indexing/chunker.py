"""Chunking for the offline indexing pipeline.

Uses LlamaIndex's SentenceSplitter for prose, but detects GitHub-flavored
markdown tables first and keeps each one as a single atomic chunk - splitting
a table by token count would scatter its rows across chunks and make the fee
schedules/comparison tables useless for retrieval.
"""

from __future__ import annotations

import re
import uuid
from dataclasses import dataclass

from llama_index.core.node_parser import SentenceSplitter

CHUNK_SIZE_TOKENS = 512
CHUNK_OVERLAP_TOKENS = 64

# Fixed, arbitrary namespace for content-addressable chunk IDs (uuid.uuid5).
# Deterministic on purpose: re-indexing unchanged content must reproduce the
# same chunk_id so Qdrant's upsert updates the existing point in place instead
# of accumulating duplicates every time run_index.py runs.
_CHUNK_ID_NAMESPACE = uuid.UUID("2f3f9a3e-6b0a-4b8e-9a5f-4a2e9f6d7c1b")

# A GFM table: a header row, a separator row ( |---|---| style ), then >=1 data
# rows. This is a pragmatic heuristic, not a full GFM parser - false positives
# (prose that happens to look pipe-delimited) are harmless, false negatives
# just fall back to normal sentence-splitting.
_TABLE_BLOCK_RE = re.compile(
    r"(?:^\|.*\|[ \t]*$\n)"  # header row
    r"(?:^\|[ \t:|-]+\|[ \t]*$\n)"  # separator row
    r"(?:^\|.*\|[ \t]*$\n?)+",  # one or more data rows
    re.MULTILINE,
)


@dataclass
class SourceDocument:
    """One parsed PDF or crawled webpage, before chunking."""

    text: str
    source: str  # human-readable name, e.g. a filename or page title
    url_or_filename: str
    doc_type: str  # "pdf" | "webpage"
    crawl_or_parse_date: str  # ISO8601
    section_title: str | None = None


@dataclass
class Chunk:
    chunk_id: str
    text: str
    source: str
    url_or_filename: str
    doc_type: str
    crawl_or_parse_date: str
    section_title: str | None
    is_table: bool = False


def _split_table_blocks(text: str) -> list[tuple[str, bool]]:
    """Split `text` into (segment, is_table) pieces, tables kept intact."""
    segments: list[tuple[str, bool]] = []
    last_end = 0
    for match in _TABLE_BLOCK_RE.finditer(text):
        if match.start() > last_end:
            segments.append((text[last_end : match.start()], False))
        segments.append((match.group(0), True))
        last_end = match.end()
    if last_end < len(text):
        segments.append((text[last_end:], False))
    return segments


def chunk_document(document: SourceDocument) -> list[Chunk]:
    """Chunk one SourceDocument into retrieval-ready Chunks.

    Non-table prose is split by LlamaIndex's SentenceSplitter (~512 tokens,
    64 overlap). Each detected markdown table becomes exactly one chunk,
    regardless of size, so its rows stay together.
    """
    splitter = SentenceSplitter(chunk_size=CHUNK_SIZE_TOKENS, chunk_overlap=CHUNK_OVERLAP_TOKENS)
    chunks: list[Chunk] = []

    for segment, is_table in _split_table_blocks(document.text):
        if not segment.strip():
            continue
        piece_texts = [segment.strip()] if is_table else splitter.split_text(segment)

        for piece_text in piece_texts:
            chunk_text = piece_text.strip()
            if not chunk_text:
                continue
            chunk_id = str(uuid.uuid5(_CHUNK_ID_NAMESPACE, f"{document.url_or_filename}::{chunk_text}"))
            chunks.append(
                Chunk(
                    chunk_id=chunk_id,
                    text=chunk_text,
                    source=document.source,
                    url_or_filename=document.url_or_filename,
                    doc_type=document.doc_type,
                    crawl_or_parse_date=document.crawl_or_parse_date,
                    section_title=document.section_title,
                    is_table=is_table,
                )
            )

    return chunks
