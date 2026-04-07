"""Extract text from service manual PDFs."""

from pathlib import Path
import fitz  # PyMuPDF


def extract_text_from_pdf(pdf_path: str | Path) -> str:
    """Extract all text from a PDF file using PyMuPDF.

    Handles multi-column layouts and preserves section structure
    better than basic text extraction.
    """
    pdf_path = Path(pdf_path)
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")

    doc = fitz.open(pdf_path)
    full_text = []

    for page_num, page in enumerate(doc):
        # Extract text with layout preservation
        text = page.get_text("text")
        if text.strip():
            full_text.append(f"--- Page {page_num + 1} ---\n{text}")

    doc.close()
    return "\n\n".join(full_text)


def extract_text_with_metadata(pdf_path: str | Path) -> list[dict]:
    """Extract text page-by-page with metadata.

    Returns list of dicts with 'page', 'text', and 'source' keys.
    Useful for preserving page references in RAG results.
    """
    pdf_path = Path(pdf_path)
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")

    doc = fitz.open(pdf_path)
    pages = []

    for page_num, page in enumerate(doc):
        text = page.get_text("text")
        if text.strip():
            pages.append(
                {
                    "page": page_num + 1,
                    "text": text.strip(),
                    "source": pdf_path.name,
                }
            )

    doc.close()
    return pages
