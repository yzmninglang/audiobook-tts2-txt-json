"""
听书工坊 (Audiobook Workshop) - History manager.

Pure-Python module for saving / listing / loading / deleting
markdown conversion results.  No Qt dependencies.

Storage layout:
    ~/.audiobook_workshop/history/{safe_name}_{timestamp}.md

Each file uses a YAML-like front-matter block:
    ---
    book_name: ...
    source_file: ...
    source_type: ...
    created_at: ...
    ---
    <markdown body>
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from gui.core.config import CONFIG_DIR

HISTORY_DIR = CONFIG_DIR / "history"

# Front-matter boundary
_FM_SEP = "---"


@dataclass
class HistoryEntry:
    """Metadata for one saved history file."""

    filepath: Path
    book_name: str
    source_file: str
    source_type: str
    created_at: str  # ISO-8601


def _safe_filename(name: str) -> str:
    """Strip characters that are problematic in file paths."""
    return re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", name).strip("_ ")


def save_history(
    book_name: str,
    markdown_content: str,
    source_file: str = "",
    source_type: str = "",
) -> Path:
    """Persist *markdown_content* with front-matter metadata.

    Returns the path to the saved file.
    """
    HISTORY_DIR.mkdir(parents=True, exist_ok=True)

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe = _safe_filename(book_name) or "untitled"
    filename = f"{safe}_{ts}.md"
    filepath = HISTORY_DIR / filename

    now_iso = datetime.now().isoformat(timespec="seconds")
    front_matter = (
        f"{_FM_SEP}\n"
        f"book_name: {book_name}\n"
        f"source_file: {source_file}\n"
        f"source_type: {source_type}\n"
        f"created_at: {now_iso}\n"
        f"{_FM_SEP}\n"
    )

    filepath.write_text(front_matter + markdown_content, encoding="utf-8")
    return filepath


def list_history() -> list[HistoryEntry]:
    """Return all history entries sorted newest-first."""
    if not HISTORY_DIR.exists():
        return []

    entries: list[HistoryEntry] = []
    for f in HISTORY_DIR.glob("*.md"):
        meta = _parse_front_matter(f)
        entries.append(
            HistoryEntry(
                filepath=f,
                book_name=meta.get("book_name", f.stem),
                source_file=meta.get("source_file", ""),
                source_type=meta.get("source_type", ""),
                created_at=meta.get("created_at", ""),
            )
        )

    entries.sort(key=lambda e: e.created_at, reverse=True)
    return entries


def load_history_content(filepath: Path | str) -> str:
    """Read a history file and return the body (without front matter)."""
    filepath = Path(filepath)
    text = filepath.read_text(encoding="utf-8")
    return _strip_front_matter(text)


def delete_history(filepath: Path | str) -> None:
    """Delete a history file."""
    filepath = Path(filepath)
    if filepath.exists():
        filepath.unlink()


# ------------------------------------------------------------------
# Internal helpers
# ------------------------------------------------------------------

def _parse_front_matter(filepath: Path) -> dict[str, str]:
    """Extract key-value pairs from the YAML-like front matter."""
    meta: dict[str, str] = {}
    try:
        text = filepath.read_text(encoding="utf-8")
    except Exception:
        return meta

    lines = text.split("\n")
    if not lines or lines[0].strip() != _FM_SEP:
        return meta

    for line in lines[1:]:
        stripped = line.strip()
        if stripped == _FM_SEP:
            break
        if ":" in stripped:
            key, _, value = stripped.partition(":")
            meta[key.strip()] = value.strip()

    return meta


def _strip_front_matter(text: str) -> str:
    """Remove the front-matter block and return the body."""
    lines = text.split("\n")
    if not lines or lines[0].strip() != _FM_SEP:
        return text

    for idx, line in enumerate(lines[1:], start=1):
        if line.strip() == _FM_SEP:
            # Body starts on the line after the closing separator
            return "\n".join(lines[idx + 1:])

    # No closing separator found — return everything
    return text
