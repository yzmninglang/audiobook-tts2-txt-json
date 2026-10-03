from __future__ import annotations
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from PyQt6.QtCore import QThread, pyqtSignal
from openai import OpenAI
from gui.core.history import write_chapter_json
from gui.core.pipeline import (
    MAX_OUTPUT_TOKENS,
    build_json_gen_prompt,
    extract_json_from_response,
    split_text_into_chunks,
)

class JsonGenWorker(QThread):
    chapter_progress = pyqtSignal(int, str, str)  # chapter_index, status, message
    progress = pyqtSignal(int, str)                # percentage 0-100, message
    log_message = pyqtSignal(str)                  # log text
    finished = pyqtSignal(list)                     # list of result dicts
    cancelled = pyqtSignal()                        # user aborted the run
    error = pyqtSignal(str)

    def __init__(
        self,
        chapters: list,           # list of dicts with index, title, content
        selected_indices: list,    # which chapter indices to process
        provider: str,             # "openrouter" / "gemini" / "qwen"
        api_key: str,
        base_url: str,
        model: str,
        max_workers: int = 5,
        chunk_size: int = 8000,
        prompt_template: str | None = None,
        output_dir: str = "",      # project folder for incremental auto-save
        autosave: bool = True,
    ):
        super().__init__()
        self._chapters = chapters
        self._selected_indices = selected_indices
        self._provider = provider
        self._api_key = api_key
        self._base_url = base_url
        self._model = model
        self._max_workers = max_workers
        self._chunk_size = chunk_size
        self._prompt_template = prompt_template
        self._output_dir = output_dir
        self._autosave = autosave
        self._cancelled = False

    def cancel(self):
        self._cancelled = True

    def _process_chunk(self, client, chapter_index: int, chunk_index: int,
                       chunk_text: str) -> tuple[int, int, list | None]:
        """Run a single chunk through the LLM.

        Returns ``(chapter_index, chunk_index, entries)``; ``entries`` is
        ``None`` when the chunk was skipped (cancelled, or every retry failed).
        """
        if self._cancelled:
            return chapter_index, chunk_index, None

        self.log_message.emit(
            f"[章节 {chapter_index}] 处理片段 {chunk_index + 1} ({len(chunk_text)}字符)"
        )
        user_prompt = build_json_gen_prompt(chunk_text, self._prompt_template)

        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = client.chat.completions.create(
                    model=self._model,
                    messages=[{"role": "user", "content": user_prompt}],
                    temperature=0.2,
                    max_tokens=MAX_OUTPUT_TOKENS,
                )
                raw = response.choices[0].message.content
                parsed = extract_json_from_response(raw)

                if isinstance(parsed, list):
                    return chapter_index, chunk_index, parsed
                self.log_message.emit(
                    f"[章节 {chapter_index}] 片段 {chunk_index + 1} 第{attempt + 1}次解析失败，重试中..."
                )
            except Exception as e:
                self.log_message.emit(
                    f"[章节 {chapter_index}] 片段 {chunk_index + 1} 第{attempt + 1}次API错误: {e}"
                )
                time.sleep(2)

        self.log_message.emit(f"[章节 {chapter_index}] 片段 {chunk_index + 1} 处理失败，已跳过")
        return chapter_index, chunk_index, None

    def _build_result(self, idx: int, title: str, entries: list,
                      status: str = "done", error_message: str = "") -> dict:
        """Assemble one chapter's result, prepending the narration title entry."""
        if title and title != "扉页":
            title_text = f"第{idx}章 {title}"
        else:
            title_text = title

        entries = list(entries)
        entries.insert(0, {
            "speaker": "旁白",
            "content": title_text,
            "emo_vector": [0.0] * 8,
            "delay": 600,
        })
        return {
            "chapter_index": idx,
            "chapter_title": title,
            "entries": entries,
            "status": status,
            "error_message": error_message,
        }

    def run(self):
        try:
            to_process = [
                ch for ch in self._chapters
                if ch["index"] in self._selected_indices
            ]
            if not to_process:
                self.error.emit("没有选中任何章节")
                return

            client = OpenAI(api_key=self._api_key, base_url=self._base_url)

            # Per-chapter bookkeeping.  Only ever touched from this thread --
            # the pool workers just return their chunk's entries.
            meta: dict[int, dict] = {}                      # idx -> {title, expected, error}
            collected: dict[int, dict[int, list]] = {}      # idx -> {chunk_i: entries}
            done: dict[int, int] = {}                       # idx -> finished chunk count
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
                    results_by_idx[idx] = self._build_result(
                        idx, title, [], "error", str(e)
                    )
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
                """Assemble a completed chapter, persist it, announce it."""
                bucket = collected[idx]
                entries: list = []
                for chunk_i in sorted(bucket):
                    entries.extend(bucket[chunk_i])

                result = self._build_result(idx, meta[idx]["title"], entries)
                results_by_idx[idx] = result
                self.chapter_progress.emit(
                    idx, "done", f"完成: {meta[idx]['title']} ({len(result['entries'])}条)"
                )
                self.log_message.emit(
                    f"[章节 {idx}] 完成，共生成 {len(result['entries'])} 条数据"
                )

                if self._autosave and self._output_dir:
                    try:
                        path = write_chapter_json(
                            self._output_dir, idx, meta[idx]["title"],
                            result["entries"],
                        )
                        self.log_message.emit(f"[章节 {idx}] 已自动保存: {path.name}")
                    except Exception as e:
                        self.log_message.emit(f"[章节 {idx}] 自动保存失败: {e}")

            # 2. Chapters with nothing to send complete on the spot.
            for idx, info in meta.items():
                if info["error"] is None and info["expected"] == 0:
                    finalize(idx)

            total_tasks = len(tasks)
            if total_tasks:
                workers = max(1, min(total_tasks, self._max_workers))
                self.log_message.emit(
                    f"开始处理 {len(to_process)} 个章节 / {total_tasks} 个片段 "
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
                            _, _, entries = future.result()
                        except Exception as e:
                            # _process_chunk handles its own errors; this is belt
                            # and braces so one bad chunk cannot kill the run.
                            entries = None
                            self.log_message.emit(
                                f"[章节 {ci}] 片段 {chi + 1} 异常: {e}"
                            )

                        completed += 1
                        if entries is not None:
                            collected[ci][chi] = entries
                        done[ci] += 1

                        self.progress.emit(
                            int(completed * 100 / total_tasks),
                            f"片段 {completed}/{total_tasks}",
                        )

                        if (meta[ci]["error"] is None
                                and done[ci] == meta[ci]["expected"]):
                            finalize(ci)
                finally:
                    # Join any requests still in flight (they cannot be aborted
                    # mid-flight); wait=False above only stops pending ones.
                    executor.shutdown(wait=True)
            else:
                self.progress.emit(100, "无待处理片段")

            if self._cancelled:
                self.log_message.emit("已取消生成")
                self.cancelled.emit()
                return

            results = [
                results_by_idx[ch["index"]]
                for ch in to_process
                if ch["index"] in results_by_idx
            ]
            results.sort(key=lambda r: r["chapter_index"])

            self.progress.emit(100, "完成")
            self.log_message.emit(f"全部处理完成! 共 {len(results)} 个章节")
            self.finished.emit(results)

        except Exception as e:
            self.error.emit(f"生成出错: {str(e)}")
