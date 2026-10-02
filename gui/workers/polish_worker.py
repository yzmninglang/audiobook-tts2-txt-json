"""
听书工坊 (Audiobook Workshop) - Text polishing worker.

Runs *before* JSON generation: chunks each chapter's raw text, asks an
LLM to rewrite it into a TTS-friendly spoken script (tables, numbers,
markdown/typography), and returns the polished plain text per chapter.
"""

from __future__ import annotations

import time
from concurrent.futures import ThreadPoolExecutor, as_completed

from PyQt6.QtCore import QThread, pyqtSignal
from openai import OpenAI

from gui.core.pipeline import (
    build_polish_prompt,
    clean_llm_text,
    split_text_into_chunks,
)


class TextPolishWorker(QThread):
    """Background thread that polishes chapter text for listening.

    Signals
    -------
    chapter_progress(int, str, str)
        ``(chapter_index, status, message)`` — same pattern as JsonGenWorker.
    log_message(str)
        Free-form log text.
    finished(list)
        List of result dicts: ``{chapter_index, chapter_title,
        polished_content, status, error_message}``.
    error(str)
        Fatal error description.
    """

    chapter_progress = pyqtSignal(int, str, str)
    log_message = pyqtSignal(str)
    finished = pyqtSignal(list)
    error = pyqtSignal(str)

    def __init__(
        self,
        chapters: list,            # list of dicts with index, title, content
        selected_indices: list,    # which chapter indices to process
        provider: str,             # "openrouter" / "gemini" / "qwen"
        api_key: str,
        base_url: str,
        model: str,
        max_workers: int = 5,
        chunk_size: int = 8000,
        rules: list | None = None,  # polish rule ids (tables/numbers/cleanup)
        prompt_template: str | None = None,
        rule_texts: dict | None = None,  # rule id -> override text
    ) -> None:
        super().__init__()
        self._chapters = chapters
        self._selected_indices = selected_indices
        self._provider = provider
        self._api_key = api_key
        self._base_url = base_url
        self._model = model
        self._max_workers = max_workers
        self._chunk_size = chunk_size
        self._rules = rules
        self._prompt_template = prompt_template
        self._rule_texts = rule_texts
        self._cancelled = False

    def cancel(self) -> None:
        self._cancelled = True

    # ------------------------------------------------------------------
    # Main logic
    # ------------------------------------------------------------------
    def _process_chapter(self, client, chapter: dict) -> dict:
        idx = chapter["index"]
        title = chapter["title"]
        content = chapter["content"]

        self.chapter_progress.emit(idx, "processing", f"正在润色: {title}")
        self.log_message.emit(f"[章节 {idx}] 开始润色: {title}")

        chunks = split_text_into_chunks(content, self._chunk_size)
        self.log_message.emit(f"[章节 {idx}] 已切分为 {len(chunks)} 个片段")

        polished_parts: list[str] = []

        for i, chunk_text in enumerate(chunks):
            if self._cancelled:
                return {
                    "chapter_index": idx,
                    "chapter_title": title,
                    "polished_content": "\n".join(polished_parts),
                    "status": "cancelled",
                    "error_message": "",
                }

            if not chunk_text.strip():
                continue

            self.log_message.emit(
                f"[章节 {idx}] 润色片段 {i + 1}/{len(chunks)} ({len(chunk_text)}字符)"
            )

            prompt = build_polish_prompt(
                chunk_text,
                self._rules,
                template=self._prompt_template,
                rule_texts=self._rule_texts,
            )
            max_retries = 3
            chunk_success = False

            for attempt in range(max_retries):
                try:
                    response = client.chat.completions.create(
                        model=self._model,
                        messages=[{"role": "user", "content": prompt}],
                        temperature=0.2,
                        max_tokens=1000000,
                    )
                    raw = response.choices[0].message.content or ""
                    text = clean_llm_text(raw)
                    if text:
                        polished_parts.append(text)
                    else:
                        # Nothing usable came back — keep the original chunk.
                        polished_parts.append(chunk_text.strip())
                    chunk_success = True
                    break
                except Exception as e:
                    self.log_message.emit(
                        f"[章节 {idx}] 片段 {i + 1} 第{attempt + 1}次API错误: {e}"
                    )
                    time.sleep(2)

            if not chunk_success:
                # Fall back to the original text so nothing is lost.
                self.log_message.emit(
                    f"[章节 {idx}] 片段 {i + 1} 润色失败，保留原文"
                )
                polished_parts.append(chunk_text.strip())

        polished = "\n".join(p for p in polished_parts if p)

        self.log_message.emit(
            f"[章节 {idx}] 完成，润色后 {len(polished)} 字符"
        )
        self.chapter_progress.emit(idx, "done", f"完成: {title}")

        return {
            "chapter_index": idx,
            "chapter_title": title,
            "polished_content": polished,
            "status": "done",
            "error_message": "",
        }

    def run(self) -> None:
        try:
            client = OpenAI(api_key=self._api_key, base_url=self._base_url)

            to_process = [
                ch for ch in self._chapters
                if ch["index"] in self._selected_indices
            ]

            if not to_process:
                self.error.emit("没有选中任何章节")
                return

            self.log_message.emit(
                f"开始润色 {len(to_process)} 个章节 (并发数: {self._max_workers})"
            )

            results: list[dict] = []

            for ch in to_process:
                self.chapter_progress.emit(
                    ch["index"], "pending", f"等待中: {ch['title']}"
                )

            workers = min(len(to_process), max(1, self._max_workers))
            with ThreadPoolExecutor(max_workers=workers) as executor:
                futures = {
                    executor.submit(self._process_chapter, client, ch): ch
                    for ch in to_process
                }

                for future in as_completed(futures):
                    if self._cancelled:
                        break
                    try:
                        results.append(future.result())
                    except Exception as e:
                        ch = futures[future]
                        self.chapter_progress.emit(
                            ch["index"], "error", f"错误: {str(e)}"
                        )
                        self.log_message.emit(
                            f"[章节 {ch['index']}] 处理异常: {e}"
                        )
                        results.append({
                            "chapter_index": ch["index"],
                            "chapter_title": ch["title"],
                            "polished_content": ch["content"],
                            "status": "error",
                            "error_message": str(e),
                        })

            results.sort(key=lambda r: r["chapter_index"])

            if not self._cancelled:
                self.log_message.emit(f"全部润色完成! 共 {len(results)} 个章节")
                self.finished.emit(results)

        except Exception as e:
            self.error.emit(f"润色出错: {str(e)}")
