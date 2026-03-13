from __future__ import annotations
import json
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from PyQt6.QtCore import QThread, pyqtSignal
from openai import OpenAI
from gui.core.pipeline import SPEC_PROMPT, split_text_into_chunks, extract_json_from_response

class JsonGenWorker(QThread):
    chapter_progress = pyqtSignal(int, str, str)  # chapter_index, status, message
    log_message = pyqtSignal(str)                  # log text
    finished = pyqtSignal(list)                     # list of result dicts
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
        self._cancelled = False

    def cancel(self):
        self._cancelled = True

    def _process_chapter(self, client, chapter):
        """Process a single chapter: chunk -> LLM -> merge."""
        idx = chapter["index"]
        title = chapter["title"]
        content = chapter["content"]

        self.chapter_progress.emit(idx, "processing", f"正在处理: {title}")
        self.log_message.emit(f"[章节 {idx}] 开始处理: {title}")

        chunks = split_text_into_chunks(content, self._chunk_size)
        self.log_message.emit(f"[章节 {idx}] 已切分为 {len(chunks)} 个片段")

        all_entries = []

        for i, chunk_text in enumerate(chunks):
            if self._cancelled:
                return {"chapter_index": idx, "chapter_title": title, "entries": [], "status": "cancelled"}

            if not chunk_text.strip():
                continue

            self.log_message.emit(f"[章节 {idx}] 处理片段 {i+1}/{len(chunks)} ({len(chunk_text)}字符)")

            user_prompt = (
                "你是一个严格的格式化器。\n"
                f"根据下述【规范】将提供的【小说片段】转换为 index-tts v2 有声书 JSON。\n"
                "注意：这只是小说的一小部分，请只处理这段文字，不要编造开头或结尾，直接输出 JSON 数组。\n\n"
                "【规范】如下：\n" + SPEC_PROMPT + "\n"
                "【小说片段】如下：\n"
                f"'''\n{chunk_text}\n'''\n\n"
                "请直接输出 JSON 数组："
            )

            chunk_success = False
            max_retries = 3

            for attempt in range(max_retries):
                try:
                    response = client.chat.completions.create(
                        model=self._model,
                        messages=[{"role": "user", "content": user_prompt}],
                        temperature=0.2,
                        max_tokens=1000000,
                    )
                    raw = response.choices[0].message.content
                    parsed = extract_json_from_response(raw)

                    if isinstance(parsed, list):
                        all_entries.extend(parsed)
                        chunk_success = True
                        break
                    else:
                        self.log_message.emit(f"[章节 {idx}] 片段 {i+1} 第{attempt+1}次解析失败，重试中...")
                except Exception as e:
                    self.log_message.emit(f"[章节 {idx}] 片段 {i+1} 第{attempt+1}次API错误: {e}")
                    time.sleep(2)

            if not chunk_success:
                self.log_message.emit(f"[章节 {idx}] 片段 {i+1} 处理失败，已跳过")

        # Prepend chapter title
        if title and title != "扉页":
            chapter_num = idx
            title_text = f"第{chapter_num}章 {title}"
        else:
            title_text = title

        title_entry = {
            "speaker": "旁白",
            "content": title_text,
            "emo_vector": [0.0]*8,
            "delay": 600
        }
        all_entries.insert(0, title_entry)

        self.log_message.emit(f"[章节 {idx}] 完成，共生成 {len(all_entries)} 条数据")
        self.chapter_progress.emit(idx, "done", f"完成: {title} ({len(all_entries)}条)")

        return {
            "chapter_index": idx,
            "chapter_title": title,
            "entries": all_entries,
            "status": "done"
        }

    def run(self):
        try:
            client = OpenAI(api_key=self._api_key, base_url=self._base_url)

            # Filter chapters by selected indices
            to_process = [ch for ch in self._chapters if ch["index"] in self._selected_indices]

            if not to_process:
                self.error.emit("没有选中任何章节")
                return

            self.log_message.emit(f"开始处理 {len(to_process)} 个章节 (并发数: {self._max_workers})")

            results = []

            # Mark all as pending
            for ch in to_process:
                self.chapter_progress.emit(ch["index"], "pending", f"等待中: {ch['title']}")

            # Process in parallel
            workers = min(len(to_process), self._max_workers)
            with ThreadPoolExecutor(max_workers=workers) as executor:
                futures = {
                    executor.submit(self._process_chapter, client, ch): ch
                    for ch in to_process
                }

                for future in as_completed(futures):
                    if self._cancelled:
                        break
                    try:
                        result = future.result()
                        results.append(result)
                    except Exception as e:
                        ch = futures[future]
                        self.chapter_progress.emit(ch["index"], "error", f"错误: {str(e)}")
                        self.log_message.emit(f"[章节 {ch['index']}] 处理异常: {e}")
                        results.append({
                            "chapter_index": ch["index"],
                            "chapter_title": ch["title"],
                            "entries": [],
                            "status": "error",
                            "error_message": str(e)
                        })

            # Sort results by chapter index
            results.sort(key=lambda r: r["chapter_index"])

            self.log_message.emit(f"全部处理完成! 共 {len(results)} 个章节")
            self.finished.emit(results)

        except Exception as e:
            self.error.emit(f"生成出错: {str(e)}")
