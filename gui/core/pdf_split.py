"""
听书工坊 (Audiobook Workshop) - PDF page-range splitting.

The MinerU conversion API caps how many pages a single uploaded file may
contain, so a thick book has to be cut into page-range parts, converted
part by part, and stitched back together.  This module does the cutting.

Pure-Python, no Qt dependencies.  Uses ``pypdfium2`` (already a project
dependency); page indices in its API are 0-based, while everything this
module exposes to callers is 1-based to match how page numbers are shown
to the user.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pypdfium2 as pdfium


@dataclass(frozen=True)
class PdfPart:
    """One page-range slice of a source PDF."""

    index: int        # 0-based position in the part list
    first_page: int   # 1-based, inclusive
    last_page: int    # 1-based, inclusive
    path: Path

    @property
    def label(self) -> str:
        """Human-readable page range, e.g. ``"200-398"``."""
        return f"{self.first_page}-{self.last_page}"

    @property
    def page_count(self) -> int:
        return self.last_page - self.first_page + 1


def page_count(pdf_path: Path | str) -> int:
    """Return the number of pages in *pdf_path*."""
    doc = pdfium.PdfDocument(str(pdf_path))
    try:
        return len(doc)
    finally:
        doc.close()


def plan_ranges(total_pages: int, max_pages: int) -> list[tuple[int, int]]:
    """Split *total_pages* into 1-based inclusive ``(first, last)`` ranges.

    Each range holds at most *max_pages* pages.  The final range is short
    rather than padded, so a 400-page book at 199 pages per part gives
    199 / 199 / 2.
    """
    if max_pages <= 0:
        raise ValueError("max_pages must be positive")
    if total_pages <= 0:
        return []
    return [
        (start, min(start + max_pages - 1, total_pages))
        for start in range(1, total_pages + 1, max_pages)
    ]


def split_pdf(
    pdf_path: Path | str,
    out_dir: Path | str,
    max_pages: int,
) -> list[PdfPart]:
    """Cut *pdf_path* into parts of at most *max_pages* pages each.

    Writes ``partNN_p{first}-{last}.pdf`` into *out_dir* and returns the
    parts in page order.  The caller owns the written files and is
    responsible for cleaning them up.
    """
    pdf_path = Path(pdf_path)
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    src = pdfium.PdfDocument(str(pdf_path))
    try:
        total = len(src)
        parts: list[PdfPart] = []
        for index, (first, last) in enumerate(plan_ranges(total, max_pages)):
            # pypdfium2 selects pages with 0-based indices.
            part_doc = pdfium.PdfDocument.new()
            try:
                part_doc.import_pages(src, pages=range(first - 1, last))
                path = out_dir / f"part{index + 1:02d}_p{first}-{last}.pdf"
                part_doc.save(str(path))
            finally:
                part_doc.close()
            parts.append(PdfPart(index, first, last, path))
        return parts
    finally:
        src.close()
