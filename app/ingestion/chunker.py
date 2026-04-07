"""Text chunking for service manuals — optimized for technical content."""

import re


def chunk_text(
    text: str,
    source: str = "unknown",
    chunk_size: int = 1000,
    chunk_overlap: int = 200,
) -> list[dict]:
    """Split text into overlapping chunks for embedding.

    Uses section-aware splitting:
    1. First tries to split on section headings (common in service manuals)
    2. Falls back to paragraph-based splitting
    3. Last resort: character-based splitting with overlap

    Returns list of dicts with 'text', 'source', and 'chunk_index'.
    """
    if not text.strip():
        return []

    # Try section-based splitting first
    sections = _split_on_headings(text)

    chunks = []
    for section in sections:
        if len(section) <= chunk_size:
            chunks.append(section)
        else:
            # Split large sections into smaller chunks with overlap
            sub_chunks = _split_with_overlap(section, chunk_size, chunk_overlap)
            chunks.extend(sub_chunks)

    # Build result with metadata
    result = []
    for i, chunk in enumerate(chunks):
        cleaned = chunk.strip()
        if cleaned and len(cleaned) > 50:  # Skip tiny fragments
            result.append(
                {
                    "text": cleaned,
                    "source": source,
                    "chunk_index": i,
                }
            )

    return result


def _split_on_headings(text: str) -> list[str]:
    """Split text on common service manual section patterns."""

    # Common heading patterns in service manuals
    heading_patterns = [
        r"\n(?=#{1,3}\s)",  # Markdown headings
        r"\n(?=[A-Z][A-Z\s]{4,}:?\n)",  # ALL CAPS HEADINGS
        r"\n(?=\d+\.\d+\s+[A-Z])",  # Numbered sections like "3.2 REMOVAL"
        r"\n(?=--- Page \d+)",  # Page markers from our PDF extraction
        r"\n(?=SECTION\s+\d+)",  # SECTION markers
        r"\n(?=STEP\s+\d+)",  # STEP markers
    ]

    # Combine patterns
    combined = "|".join(heading_patterns)

    sections = re.split(combined, text)
    return [s for s in sections if s.strip()]


def _split_with_overlap(text: str, chunk_size: int, overlap: int) -> list[str]:
    """Split text into overlapping chunks, preferring paragraph boundaries."""

    paragraphs = text.split("\n\n")
    chunks = []
    current_chunk = ""

    for para in paragraphs:
        para = para.strip()
        if not para:
            continue

        if len(current_chunk) + len(para) + 2 <= chunk_size:
            current_chunk += ("\n\n" + para) if current_chunk else para
        else:
            if current_chunk:
                chunks.append(current_chunk)
                # Keep overlap from end of previous chunk
                overlap_text = current_chunk[-overlap:] if overlap else ""
                current_chunk = overlap_text + "\n\n" + para if overlap_text else para
            else:
                # Single paragraph exceeds chunk_size — hard split
                for i in range(0, len(para), chunk_size - overlap):
                    chunks.append(para[i : i + chunk_size])
                current_chunk = ""

    if current_chunk.strip():
        chunks.append(current_chunk)

    return chunks
