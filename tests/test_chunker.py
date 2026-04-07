"""Tests for the text chunker."""

import pytest
from app.ingestion.chunker import chunk_text


class TestChunker:
    """Test text chunking for service manuals."""

    def test_basic_chunking(self):
        text = "This is a paragraph about engine diagnostics. " * 50
        chunks = chunk_text(text, source="test.pdf", chunk_size=500)
        assert len(chunks) > 1
        for chunk in chunks:
            assert chunk["source"] == "test.pdf"
            assert "chunk_index" in chunk

    def test_empty_text(self):
        chunks = chunk_text("", source="test.pdf")
        assert chunks == []

    def test_whitespace_only(self):
        chunks = chunk_text("   \n\n  ", source="test.pdf")
        assert chunks == []

    def test_small_text_single_chunk(self):
        text = "This is a short piece of text about checking brake fluid levels and pad wear."
        chunks = chunk_text(text, source="test.pdf", chunk_size=1000)
        assert len(chunks) == 1
        assert chunks[0]["text"] == text

    def test_section_based_splitting(self):
        text = """SECTION 1 REMOVAL
        Remove the intake manifold by disconnecting all vacuum lines.

        SECTION 2 INSTALLATION
        Install the new gasket and torque bolts to 18 ft-lbs in sequence.
        """
        chunks = chunk_text(text, source="manual.pdf")
        assert len(chunks) >= 1
        assert all(c["source"] == "manual.pdf" for c in chunks)

    def test_tiny_fragments_skipped(self):
        text = "Short.\n\n" + "This is a longer paragraph about automotive diagnostics. " * 20
        chunks = chunk_text(text, source="test.pdf")
        for chunk in chunks:
            assert len(chunk["text"]) > 50
