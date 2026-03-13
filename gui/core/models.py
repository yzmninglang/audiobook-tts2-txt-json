from __future__ import annotations
from enum import Enum
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field


class FileType(str, Enum):
    PDF = "pdf"
    TXT = "txt"
    MD = "md"
    EPUB = "epub"


class ImportedFile(BaseModel):
    path: Path
    file_type: FileType
    size_bytes: int
    name: str


class ChapterInfo(BaseModel):
    index: int  # 1-based
    title: str
    content: str
    line_start: int = 0
    line_end: int = 0


class TTSEntry(BaseModel):
    speaker: str
    content: str
    emo_vector: list[float] = Field(default_factory=lambda: [0.0] * 8)
    delay: int = 500


class ChapterResult(BaseModel):
    chapter_index: int
    chapter_title: str
    entries: list[TTSEntry] = Field(default_factory=list)
    status: str = "pending"  # pending / processing / done / error
    error_message: str = ""


class SpeakerInfo(BaseModel):
    name: str
    count: int
    classification: str = ""  # 少男/少女/中男/中女/老男/老女/旁白


class PipelineState(BaseModel):
    book_name: str = ""
    imported_file: Optional[ImportedFile] = None
    markdown_content: str = ""
    chapter_list_raw: str = ""
    chapters: list[ChapterInfo] = Field(default_factory=list)
    chapter_results: list[ChapterResult] = Field(default_factory=list)
    speakers: list[SpeakerInfo] = Field(default_factory=list)
    classifications: dict[str, list[str]] = Field(default_factory=dict)
    output_dir: str = ""
