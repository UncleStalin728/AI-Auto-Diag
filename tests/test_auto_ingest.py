"""Tests for auto-ingest PDF watcher."""

import json
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

from app.core.auto_ingest import scan_and_ingest, _load_marker, _save_marker


@pytest.fixture
def watch_dir(tmp_path):
    """Create a temporary watch directory."""
    d = tmp_path / "manuals"
    d.mkdir()
    return d


@pytest.fixture
def mock_pipeline():
    """Mock RAG pipeline."""
    pipeline = MagicMock()
    pipeline.ingest_pdf.return_value = 10  # 10 chunks per PDF
    return pipeline


class TestScanAndIngest:
    def test_finds_new_pdfs(self, watch_dir, mock_pipeline):
        # Create fake PDFs
        (watch_dir / "service_manual.pdf").write_bytes(b"%PDF-1.4 fake content")
        (watch_dir / "torque_specs.pdf").write_bytes(b"%PDF-1.4 more content")

        with patch("app.core.auto_ingest.get_rag_pipeline", return_value=mock_pipeline):
            result = scan_and_ingest(watch_dir)

        assert len(result["new_files"]) == 2
        assert result["chunks_created"] == 20
        assert mock_pipeline.ingest_pdf.call_count == 2

    def test_skips_already_ingested(self, watch_dir, mock_pipeline):
        # Create a PDF
        pdf = watch_dir / "manual.pdf"
        pdf.write_bytes(b"%PDF-1.4 content")

        with patch("app.core.auto_ingest.get_rag_pipeline", return_value=mock_pipeline):
            # First scan: should ingest
            result1 = scan_and_ingest(watch_dir)
            assert len(result1["new_files"]) == 1

            # Second scan: should skip
            result2 = scan_and_ingest(watch_dir)
            assert len(result2["new_files"]) == 0

        # Pipeline should only have been called once
        assert mock_pipeline.ingest_pdf.call_count == 1

    def test_handles_empty_directory(self, watch_dir, mock_pipeline):
        with patch("app.core.auto_ingest.get_rag_pipeline", return_value=mock_pipeline):
            result = scan_and_ingest(watch_dir)

        assert result["new_files"] == []
        assert result["chunks_created"] == 0

    def test_creates_missing_directory(self, tmp_path, mock_pipeline):
        missing_dir = tmp_path / "does_not_exist"
        with patch("app.core.auto_ingest.get_rag_pipeline", return_value=mock_pipeline):
            result = scan_and_ingest(missing_dir)

        assert missing_dir.exists()
        assert result["new_files"] == []

    def test_ignores_non_pdf_files(self, watch_dir, mock_pipeline):
        (watch_dir / "readme.txt").write_text("not a pdf")
        (watch_dir / "image.png").write_bytes(b"PNG")

        with patch("app.core.auto_ingest.get_rag_pipeline", return_value=mock_pipeline):
            result = scan_and_ingest(watch_dir)

        assert result["new_files"] == []
        assert mock_pipeline.ingest_pdf.call_count == 0

    def test_detects_changed_pdf(self, watch_dir, mock_pipeline):
        pdf = watch_dir / "manual.pdf"

        with patch("app.core.auto_ingest.get_rag_pipeline", return_value=mock_pipeline):
            # First version
            pdf.write_bytes(b"%PDF-1.4 version 1")
            result1 = scan_and_ingest(watch_dir)
            assert len(result1["new_files"]) == 1

            # Modify the file (different content = different size/mtime)
            pdf.write_bytes(b"%PDF-1.4 version 2 with more content added")
            result2 = scan_and_ingest(watch_dir)
            assert len(result2["new_files"]) == 1

    def test_handles_ingest_failure(self, watch_dir):
        (watch_dir / "bad.pdf").write_bytes(b"not really a pdf")

        fail_pipeline = MagicMock()
        fail_pipeline.ingest_pdf.side_effect = Exception("Parse error")

        with patch("app.core.auto_ingest.get_rag_pipeline", return_value=fail_pipeline):
            result = scan_and_ingest(watch_dir)

        # Should not crash, but file is marked (with error) so it's not retried
        assert result["new_files"] == []
        assert result["chunks_created"] == 0

        # Check marker file records the error
        marker = _load_marker(watch_dir)
        assert len(marker) == 1
        entry = list(marker.values())[0]
        assert entry["ingested"] is False
        assert "Parse error" in entry["error"]


class TestMarkerFile:
    def test_save_and_load(self, watch_dir):
        data = {"file1|100|12345": {"filename": "file1.pdf", "chunks": 5, "ingested": True}}
        _save_marker(watch_dir, data)
        loaded = _load_marker(watch_dir)
        assert loaded == data

    def test_load_missing(self, watch_dir):
        loaded = _load_marker(watch_dir)
        assert loaded == {}

    def test_load_corrupted(self, watch_dir):
        marker_path = watch_dir / ".ingested_files.json"
        marker_path.write_text("not json{{{")
        loaded = _load_marker(watch_dir)
        assert loaded == {}
