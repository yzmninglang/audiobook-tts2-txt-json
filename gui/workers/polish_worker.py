"""
听书工坊 (Audiobook Workshop) - Text polishing worker.

Runs *before* JSON generation: chunks each chapter's raw text, asks an
LLM to rewrite it into a TTS-friendly spoken script (tables, numbers,
markdown/typography), and returns the polished plain text per chapter.

Chunks are dispatched through a single flat thread pool, so a book made of
one or two very long chapters parallelises just as well as one with many
short chapters.
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
    progress(int, str)
        Overall ``(percentage 0-100, message)`` by completed chunk.
    log_message(str)
        Free-form log text.
    finished(list)
        List of result dicts: ``{chapter_index, chapter_title,
        polished_content, status, error_message}``.  Not emitted on cancel.
    cancelled()
        The run was aborted by the user.
    error(str)
        Fatal error description.
    """

    chapter_progress = pyqtSignal(int, str, str)
    progress = pyqtSignal(int, str)
    log_message = pyqtSignal(str)
    finished = pyqtSignal(list)
    cancelled = pyqtSignal()
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
    def _process_chunk(self, client, chapter_index: int, chunk_index: int,
                       chunk_text: str) -> tuple[int, int, str]:
        """Polish a single chunk.

        Returns ``(chapter_index, chunk_index, text)``.  On failure the
        original chunk text is returned so no content is ever lost.
        """
        if self._cancelled:
            return chapter_index, chunk_index, ""

        self.log_message.emit(
            f"[章节 {chapter_index}] 润色片段 {chunk_index + 1} ({len(chunk_text)}字符)"
        )
        prompt = build_polish_prompt(
            chunk_text,
            self._rules,
            template=self._prompt_template,
            rule_texts=self._rule_texts,
        )

        max_retries = 3
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
                    return chapter_index, chunk_index, text
                # Nothing usable came back — keep the original chunk.
                return chapter_index, chunk_index, chunk_text.strip()
            except Exception as e:
                self.log_message.emit(
                    f"[章节 {chapter_index}] 片段 {chunk_index + 1} "
                    f"第{attempt + 1}次API错误: {e}"
                )
                time.sleep(2)

        # All retries failed — fall back to the original text.
        self.log_message.emit(
            f"[章节 {chapter_index}] 片段 {chunk_index + 1} 润色失败，保留原文"
        )
        return chapter_index, chunk_index, chunk_text.strip()

    def run(self) -> None:
        try:
            to_process = [
                ch for ch in self._chapters
                if ch["index"] in self._selected_indices
            ]
            if not to_process:
                self.error.emit("没有选中任何章节")
                return

            client = OpenAI(api_key=self._api_key, base_url=self._base_url)

            # Per-chapter bookkeeping, touched only from this thread.
            meta: dict[int, dict] = {}                    # idx -> {title, expected, error}
            collected: dict[int, dict[int, str]] = {}     # idx -> {chunk_i: text}
            done: dict[int, int] = {}                     # idx -> finished chunk count
            results_by_idx: dict[int, dict] = {}

            # 1. Flatten every chapter into one task list.
            tasks: list[tuple[int, int, str]] = []
            for ch in to_process:
                idx, title = ch["index"], ch["title"]
                self.chapter_progress.emit(idx, "pending", f"等待中: {title}")
                try:
                    chunks = split_text_into_chunks(ch["content"], self._chunk_size)
                except Exception as e:
                    meta[idx] = {"title": title, "expected": 0, "error": str(e)}
                    results_by_idx[idx] = {
                        "chapter_index": idx,
                        "chapter_title": title,
                        "polished_content": ch["content"],
                        "status": "error",
                        "error_message": str(e),
                    }
                    self.chapter_progress.emit(idx, "error", f"错误: {e}")
                    continue

                nonempty = [(i, t) for i, t in enumerate(chunks) if t.strip()]
                meta[idx] = {"title": title, "expected": len(nonempty), "error": None}
                collected[idx] = {}
                done[idx] = 0
                for i, t in nonempty:
                    tasks.append((idx, i, t))
                self.log_message.emit(f"[章节 {idx}] 已切分为 {len(nonempty)} 个片段")

            def finalize(idx: int) -> None:
                """Join a completed chapter's chunks in order."""
                parts = [
                    collected[idx][chunk_i]
                    for chunk_i in sorted(collected[idx])
                ]
                polished = "\n".join(p for p in parts if p)
                title = meta[idx]["title"]

                results_by_idx[idx] = {
                    "chapter_index": idx,
                    "chapter_title": title,
                    "polished_content": polished,
                    "status": "done",
                    "error_message": "",
                }
                self.chapter_progress.emit(idx, "done", f"完成: {title}")
                self.log_message.emit(
                    f"[章节 {idx}] 完成，润色后 {len(polished)} 字符"
                )

            # 2. Chapters with nothing to send complete on the spot.
            for idx, info in meta.items():
                if info["error"] is None and info["expected"] == 0:
                    finalize(idx)

            total_tasks = len(tasks)
            if total_tasks:
                workers = max(1, min(total_tasks, self._max_workers))
                self.log_message.emit(
                    f"开始润色 {len(to_process)} 个章节 / {total_tasks} 个片段 "
                    f"(并发数: {workers})"
                )

                executor = ThreadPoolExecutor(max_workers=workers)
                futures = {
                    executor.submit(self._process_chunk, client, ci, chi, txt): (ci, chi)
                    for ci, chi, txt in tasks
                }
                completed = 0
                try:
                    for future in as_completed(futures):
                        if self._cancelled:
                            executor.shutdown(wait=False, cancel_futures=True)
                            break

                        ci, chi = futures[future]
                        try:
                            _, _, text = future.result()
                        except Exception as e:
                            text = ""
                            self.log_message.emit(
                                f"[章节 {ci}] 片段 {chi + 1} 异常: {e}"
                            )

                        completed += 1
                        collected[ci][chi] = text
                        done[ci] += 1

                        self.progress.emit(
                            int(completed * 100 / total_tasks),
                            f"片段 {completed}/{total_tasks}",
                        )

                        if (meta[ci]["error"] is None
                                and done[ci] == meta[ci]["expected"]):
                            finalize(ci)
                finally:
                    executor.shutdown(wait=True)
            else:
                self.progress.emit(100, "无待处理片段")

            if self._cancelled:
                self.log_message.emit("已取消润色")
                self.cancelled.emit()
                return

            results = [
                results_by_idx[ch["index"]]
                for ch in to_process
                if ch["index"] in results_by_idx
            ]
            results.sort(key=lambda r: r["chapter_index"])

            self.progress.emit(100, "完成")
            self.log_message.emit(f"全部润色完成! 共 {len(results)} 个章节")
            self.finished.emit(results)

        except Exception as e:
            self.error.emit(f"润色出错: {str(e)}")
