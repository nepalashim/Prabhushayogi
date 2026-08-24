"""Offline indexing pipeline orchestrator.

Usage:
    python -m indexing.run_index [--force-rebuild]

Parses every PDF in data/raw_pdfs/ (empty is fine - none exist yet), crawls
the fixed website seed list, chunks everything, embeds it, and loads it into
Qdrant. Refuses to mix vectors from a different embedding model into an
existing collection unless --force-rebuild is passed (see indexing/index_meta.py).
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

from config.seed_urls import BASE_URL, get_page_title
from config.settings import settings
from indexing.chunker import Chunk, SourceDocument, chunk_document
from indexing.index_meta import Compatibility, check_compatibility, write_index_meta
from indexing.pdf_parser import parse_pdf
from indexing.qdrant_loader import collection_point_count, ensure_collection, upsert_chunks
from indexing.web_crawler import crawl_seed_pages
from ml_models.embedder import embedding_dimension

RAW_PDFS_DIR = Path("data/raw_pdfs")
_SAFE_TO_PROCEED_WITHOUT_FORCE = {Compatibility.MATCH, Compatibility.NO_INDEX_YET}


def _parse_all_pdfs() -> list[SourceDocument]:
    pdf_paths = sorted(RAW_PDFS_DIR.glob("*.pdf"))
    if not pdf_paths:
        print(f"[run_index] no PDFs found in {RAW_PDFS_DIR}/ - skipping PDF ingestion")
        return []
    documents = []
    for path in pdf_paths:
        print(f"[run_index] parsing {path.name}")
        documents.append(parse_pdf(path))
    return documents


async def _crawl_website() -> list[SourceDocument]:
    print("[run_index] crawling website seed pages...")
    fetched_pages = await crawl_seed_pages()
    return [
        SourceDocument(
            text=page.markdown,
            source=get_page_title(page.final_url.replace(BASE_URL, "") or "/"),
            url_or_filename=page.final_url,
            doc_type="webpage",
            crawl_or_parse_date=page.fetched_at,
        )
        for page in fetched_pages
    ]


def _chunk_all(documents: list[SourceDocument]) -> list[Chunk]:
    all_chunks: list[Chunk] = []
    for document in documents:
        chunks = chunk_document(document)
        print(f"[run_index]   {document.url_or_filename}: {len(chunks)} chunks")
        all_chunks.extend(chunks)
    return all_chunks


async def run_index(force_rebuild: bool) -> int:
    current_model = settings.resolved_embed_model()
    current_dim = embedding_dimension()

    compatibility = check_compatibility(current_model, current_dim)
    if compatibility not in _SAFE_TO_PROCEED_WITHOUT_FORCE and not force_rebuild:
        print(
            f"[run_index] REFUSING to index: the existing index is incompatible with the "
            f"current embedding model ({compatibility.value}). It was built with a different "
            f"model/dimension than '{current_model}' ({current_dim}-dim). Re-run with "
            f"--force-rebuild to drop the existing collection and rebuild from scratch."
        )
        return 1

    documents = _parse_all_pdfs()
    documents.extend(await _crawl_website())

    if not documents:
        print("[run_index] no content to index (no PDFs and the website crawl found nothing) - aborting")
        return 1

    print(f"[run_index] chunking {len(documents)} documents...")
    chunks = _chunk_all(documents)
    print(f"[run_index] {len(chunks)} total chunks")

    ensure_collection(force_recreate=force_rebuild)
    upsert_chunks(chunks)

    write_index_meta(
        embed_model=current_model,
        embed_dim=current_dim,
        collection_name=settings.QDRANT_COLLECTION_NAME,
        chunk_count=collection_point_count(),
    )

    print(f"[run_index] done. Qdrant collection now has {collection_point_count()} points.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Prabhu Sahayogi offline indexing pipeline")
    parser.add_argument(
        "--force-rebuild",
        action="store_true",
        help="Drop and recreate the Qdrant collection even if it was built with a different embedding model.",
    )
    args = parser.parse_args()
    return asyncio.run(run_index(force_rebuild=args.force_rebuild))


if __name__ == "__main__":
    sys.exit(main())
