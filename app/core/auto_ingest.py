"""Auto-ingest watcher for service manual PDFs.

Periodically scans a watch directory for new PDF files and ingests them
into the RAG pipeline. Tracks processed files via a marker file so it
survives restarts and handles files dropped while the app is off.
"""

import asyncio
import json
import logging
from pathlib import Path

from app.config import get_settings
from app.core.rag_pipeline import get_rag_pipeline

logger = logging.getLogger(__name__)

MARKER_FILENAME = ".ingested_files.json"


def _get_file_key(path: Path) -> str:
    """Create a unique key for a file based on name, size, and mtime."""
    stat = path.stat()
    return f"{path.name}|{stat.st_size}|{int(stat.st_mtime)}"


def _load_marker(watch_dir: Path) -> dict:
    """Load the marker file tracking which files have been ingested."""
    marker_path = watch_dir / MARKER_FILENAME
    if marker_path.exists():
        try:
            with open(marker_path) as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            return {}
    return {}


def _save_marker(watch_dir: Path, marker: dict):
    """Save the marker file."""
    marker_path = watch_dir / MARKER_FILENAME
    with open(marker_path, "w") as f:
        json.dump(marker, f, indent=2)


def scan_and_ingest(watch_dir: Path | None = None) -> dict:
    """Scan the watch directory and ingest any new or changed PDFs.

    Returns a summary dict with new_files and chunks_created.
    """
    if watch_dir is None:
        settings = get_settings()
        watch_dir = Path(settings.manuals_watch_dir)

    if not watch_dir.exists():
        watch_dir.mkdir(parents=True, exist_ok=True)
        return {"new_files": [], "chunks_created": 0}

    marker = _load_marker(watch_dir)
    pipeline = get_rag_pipeline()

    if pipeline is None:
        logger.debug("RAG pipeline unavailable — skipping auto-ingest scan")
        return {"new_files": [], "chunks_created": 0}

    new_files = []
    total_chunks = 0

    for pdf_path in sorted(watch_dir.glob("*.pdf")):
        file_key = _get_file_key(pdf_path)

        if file_key in marker:
            continue  # Already ingested

        logger.info(f"Auto-ingesting: {pdf_path.name}")
        try:
            chunks = pipeline.ingest_pdf(pdf_path, metadata={"auto_ingested": True})
            marker[file_key] = {
                "filename": pdf_path.name,
                "chunks": chunks,
                "ingested": True,
            }
            new_files.append(pdf_path.name)
            total_chunks += chunks
            logger.info(f"  → {chunks} chunks created from {pdf_path.name}")
        except Exception as e:
            logger.error(f"  Failed to ingest {pdf_path.name}: {e}")
            marker[file_key] = {
                "filename": pdf_path.name,
                "chunks": 0,
                "ingested": False,
                "error": str(e),
            }

    _save_marker(watch_dir, marker)

    if new_files:
        logger.info(f"Auto-ingest complete: {len(new_files)} new files, {total_chunks} chunks")

    return {"new_files": new_files, "chunks_created": total_chunks}


async def start_auto_ingest_loop(interval: int | None = None):
    """Background loop that periodically scans for new PDFs.

    Runs forever until cancelled. Catches all exceptions to avoid
    crashing the main application.
    """
    if interval is None:
        settings = get_settings()
        interval = settings.auto_ingest_interval_seconds

    logger.info(f"Auto-ingest watcher started (interval: {interval}s)")

    while True:
        try:
            result = scan_and_ingest()
            if result["new_files"]:
                logger.info(f"Auto-ingest found {len(result['new_files'])} new files")
        except Exception as e:
            logger.error(f"Auto-ingest error: {e}")

        await asyncio.sleep(interval)
