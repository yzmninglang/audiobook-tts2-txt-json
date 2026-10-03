from __future__ import annotations
import io
import math
import shutil
import tempfile
import threading
import time
import uuid
import zipfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from PyQt6.QtCore import QThread, pyqtSignal
import httpx

from gui.core.history import write_source_markdown
from gui.core.pdf_split import PdfPart, page_count, split_pdf


class _Cancelled(Exception):
    """Internal: the user aborted the run."""


class MineruWorker(QThread):
    progress = pyqtSignal(int, str)   # percentage, message
    finished = pyqtSignal(str)         # markdown content
    error = pyqtSignal(str)

    _API_BASE_PATH = "api/v4"
    _MODEL_VERSION = "vlm"
    _POLL_INTERVAL = 3          # seconds
    _POLL_TIMEOUT = 600         # seconds
    _UPLOAD_TIMEOUT = 120       # seconds
    _REQUEST_TIMEOUT = 60       # seconds
    _MAX_RETRIES = 3
    _RETRY_BACKOFF = 1.0        # seconds

    def __init__(self, file_path: str, api_token: str,
                 endpoint: str = "https://mineru.net",
                 max_pages: int = 199, max_workers: int = 3,
                 output_dir: str = "", book_name: str = ""):
        super().__init__()
        self._file_path = file_path
        self._api_token = api_token.strip()
        self._endpoint = endpoint.rstrip("/")
        # MinerU caps pages per uploaded file; anything longer is cut into
        # page-range parts and those parts are converted concurrently.
        self._max_pages = max(1, max_pages)
        self._max_workers = max(1, max_workers)
        self._output_dir = output_dir
        self._book_name = book_name
        self._cancelled = False

    def cancel(self):
        self._cancelled = True

    # ── auth headers ────────────────────────────────────────────────
    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self._api_token}",
            "token": self._api_token,
            "X-MinerU-User-Token": self._api_token,
        }

    # ── API base URL candidates ─────────────────────────────────────
    def _api_bases(self) -> list[str]:
        ep = self._endpoint
        if ep.endswith(f"/{self._API_BASE_PATH}"):
            return [ep, ep[: -len(f"/{self._API_BASE_PATH}")]]
        return [f"{ep}/{self._API_BASE_PATH}", ep]

    # ── HTTP request with retry + base-url fallback ─────────────────
    def _request_json(self, client: httpx.Client, method: str,
                      path: str, payload: dict | None = None,
                      timeout: float | None = None) -> dict:
        timeout = timeout or self._REQUEST_TIMEOUT
        clean_path = path.lstrip("/")
        last_error: Exception | None = None

        for base in self._api_bases():
            url = f"{base}/{clean_path}"
            for attempt in range(self._MAX_RETRIES):
                try:
                    resp = client.request(
                        method=method.upper(),
                        url=url,
                        headers=self._headers(),
                        json=payload,
                        timeout=timeout,
                    )
                except Exception as exc:
                    last_error = exc
                    if self._is_retryable_error(exc) and (attempt + 1) < self._MAX_RETRIES:
                        time.sleep(self._RETRY_BACKOFF * (attempt + 1))
                        continue
                    break

                if resp.status_code in {404, 405}:
                    break  # try next base
                if self._is_retryable_status(resp.status_code) and (attempt + 1) < self._MAX_RETRIES:
                    time.sleep(self._RETRY_BACKOFF * (attempt + 1))
                    continue
                if resp.status_code >= 400:
                    raise RuntimeError(
                        f"HTTP {resp.status_code}: {resp.text[:300]}"
                    )

                data = resp.json()
                if not isinstance(data, dict):
                    raise RuntimeError(f"意外的响应类型: {type(data).__name__}")
                return data

        raise RuntimeError(
            f"请求失败: {last_error}" if last_error
            else "API端点未找到，请检查endpoint配置"
        )

    @staticmethod
    def _is_retryable_error(exc: Exception) -> bool:
        return isinstance(exc, (
            httpx.ConnectError, httpx.ReadError, httpx.WriteError,
            httpx.ReadTimeout, httpx.WriteTimeout,
            httpx.ConnectTimeout, httpx.PoolTimeout,
            httpx.RemoteProtocolError, httpx.ProxyError,
        ))

    @staticmethod
    def _is_retryable_status(code: int) -> bool:
        return code in {408, 425, 429, 500, 502, 503, 504}

    # ── extract nested response data ────────────────────────────────
    @staticmethod
    def _extract_data(payload: dict, context: str) -> dict:
        code = payload.get("code")
        if code not in (None, 0, "0"):
            msg = payload.get("msg") or payload.get("message") or "未知错误"
            raise RuntimeError(f"{context}: {msg}")
        data = payload.get("data")
        if data is None:
            return {}
        if not isinstance(data, dict):
            raise RuntimeError(f"{context}: 返回数据格式异常")
        return data

    # ── extract upload URL from response ────────────────────────────
    @staticmethod
    def _extract_upload_url(data: dict) -> str | None:
        file_urls = data.get("file_urls")
        if isinstance(file_urls, list) and file_urls:
            first = file_urls[0]
            if isinstance(first, str) and first.strip():
                return first.strip()
            if isinstance(first, dict):
                for key in ("url", "file_url", "upload_url"):
                    val = first.get(key)
                    if isinstance(val, str) and val.strip():
                        return val.strip()
        return None

    # ── find string value from nested dict ──────────────────────────
    @staticmethod
    def _find_str(payload, keys: tuple[str, ...]) -> str | None:
        if isinstance(payload, dict):
            for k in keys:
                v = payload.get(k)
                if isinstance(v, str) and v.strip():
                    return v.strip()
            for v in payload.values():
                found = MineruWorker._find_str(v, keys)
                if found:
                    return found
        elif isinstance(payload, list):
            for item in payload:
                found = MineruWorker._find_str(item, keys)
                if found:
                    return found
        return None

    # ── resolve result entry by data_id ─────────────────────────────
    @staticmethod
    def _resolve_result_entry(data: dict, data_id: str) -> dict:
        items = data.get("extract_result")
        if not isinstance(items, list):
            items = data.get("results")
        if isinstance(items, dict):
            items = list(items.values())
        if not isinstance(items, list):
            return data
        if not items:
            return {}
        for item in items:
            if isinstance(item, dict) and str(item.get("data_id", "")).strip() == data_id:
                return item
        for item in items:
            if isinstance(item, dict):
                return item
        return {}

    # ── download markdown from zip URL ──────────────────────────────
    @staticmethod
    def _download_md_from_zip(client: httpx.Client, url: str) -> str:
        resp = client.get(url, timeout=120)
        if resp.status_code != 200:
            raise RuntimeError(f"下载zip失败: HTTP {resp.status_code}")
        try:
            with zipfile.ZipFile(io.BytesIO(resp.content)) as archive:
                md_files = sorted(
                    [n for n in archive.namelist()
                     if n.lower().endswith(".md") and not n.endswith("/")],
                    key=lambda x: (x.count("/"), len(x), x),
                )
                for name in md_files:
                    with archive.open(name, "r") as fp:
                        text = fp.read().decode("utf-8", errors="ignore").strip()
                    if text:
                        return text
        except zipfile.BadZipFile:
            raise RuntimeError("下载的zip文件格式无效")
        raise RuntimeError("zip文件中未找到markdown内容")

    # ── convert one uploaded file ───────────────────────────────────
    def _convert_one(self, client: httpx.Client, file_path: Path,
                     label: str, report) -> str:
        """Upload *file_path*, wait for MinerU, and return its markdown.

        *report* is called with ``(fraction, message)`` where *fraction* is
        this part's own 0.0-1.0 progress.  Raises :class:`_Cancelled` if the
        user aborted, or :class:`RuntimeError` on any failure.
        """
        if self._cancelled:
            raise _Cancelled()

        data_id = uuid.uuid4().hex[:12]

        # Step 1: Create upload URL (file-urls/batch)
        report(0.0, f"{label}: 正在创建上传任务...")
        create_payload = {
            "files": [{"name": file_path.name, "data_id": data_id}],
            "model_version": self._MODEL_VERSION,
        }
        create_resp = self._request_json(
            client, "POST", "file-urls/batch", create_payload
        )
        create_data = self._extract_data(create_resp, "创建上传任务")

        upload_url = self._extract_upload_url(create_data)
        if not upload_url:
            raise RuntimeError(f"{label}: 未获取到上传URL")

        batch_id = self._find_str(create_data, ("batch_id", "batchId")) or ""
        if not batch_id:
            raise RuntimeError(f"{label}: 未获取到 batch_id")

        # Step 2: Upload file to presigned URL (PUT)
        report(0.10, f"{label}: 正在上传...")
        file_bytes = file_path.read_bytes()
        last_error: Exception | None = None
        for attempt in range(self._MAX_RETRIES):
            if self._cancelled:
                raise _Cancelled()
            try:
                up_resp = client.put(
                    upload_url, content=file_bytes,
                    timeout=self._UPLOAD_TIMEOUT,
                )
            except Exception as exc:
                if not self._is_retryable_error(exc):
                    raise RuntimeError(f"{label}: 上传失败 {exc}")
                last_error = exc
            else:
                if up_resp.status_code < 400:
                    break
                if not self._is_retryable_status(up_resp.status_code):
                    raise RuntimeError(
                        f"{label}: 上传失败 HTTP {up_resp.status_code}"
                    )
                last_error = RuntimeError(f"HTTP {up_resp.status_code}")
            if (attempt + 1) < self._MAX_RETRIES:
                time.sleep(self._RETRY_BACKOFF * (attempt + 1))
        else:
            raise RuntimeError(f"{label}: 上传失败，重试次数已用完 ({last_error})")

        # Step 3: Poll for result (extract-results/batch/{batch_id})
        report(0.20, f"{label}: 已上传，等待解析...")
        start_time = time.monotonic()
        while True:
            if self._cancelled:
                raise _Cancelled()

            elapsed = time.monotonic() - start_time
            if elapsed >= self._POLL_TIMEOUT:
                raise RuntimeError(f"{label}: 解析超时")

            time.sleep(self._POLL_INTERVAL)
            # Hold between 0.20 and 0.90 while the server works.
            report(
                0.20 + 0.70 * min(1.0, elapsed / self._POLL_TIMEOUT),
                f"{label}: 正在解析... (已等待 {int(elapsed)}秒)",
            )

            try:
                result_resp = self._request_json(
                    client, "GET", f"extract-results/batch/{batch_id}",
                )
            except Exception:
                continue  # retry on next poll

            result_data = self._extract_data(result_resp, "查询解析结果")
            entry = self._resolve_result_entry(result_data, data_id)

            state = str(entry.get("state", "")).strip().lower()
            if state == "success":
                state = "done"

            if state in ("done", "finished"):
                report(0.95, f"{label}: 解析完成，正在获取结果...")
                md_content = self._get_markdown(client, entry, result_data)
                if not md_content:
                    raise RuntimeError(f"{label}: 解析完成但未找到Markdown内容")
                return md_content

            if state in ("failed", "cancelled"):
                reason = (
                    entry.get("error")
                    or entry.get("err_msg")
                    or entry.get("message")
                    or "未知错误"
                )
                raise RuntimeError(f"{label}: 解析失败 {reason}")

    # ── run every part concurrently, return markdown in page order ──
    def _convert_parts(self, client: httpx.Client,
                       parts: list[PdfPart]) -> list[str]:
        total = len(parts)
        progress_by_part: dict[int, float] = {p.index: 0.0 for p in parts}
        lock = threading.Lock()

        def reporter(index: int):
            def report(fraction: float, message: str) -> None:
                with lock:
                    progress_by_part[index] = max(
                        0.0, min(1.0, fraction)
                    )
                    overall = sum(progress_by_part.values()) / total
                # Leave the last 2% for merging/auto-save.
                self.progress.emit(min(98, int(overall * 100)), message)
            return report

        outcomes: dict[int, str] = {}
        workers = max(1, min(total, self._max_workers))
        executor = ThreadPoolExecutor(max_workers=workers)
        try:
            futures = {
                executor.submit(
                    self._convert_one, client, part.path,
                    f"批次 {part.index + 1}/{total}" if total > 1
                    else f"共 {part.page_count} 页",
                    reporter(part.index),
                ): part.index
                for part in parts
            }
            try:
                for future in as_completed(futures):
                    index = futures[future]
                    outcomes[index] = future.result()
                    with lock:
                        progress_by_part[index] = 1.0
            except BaseException:
                # Don't burn through the remaining parts after a failure.
                executor.shutdown(wait=False, cancel_futures=True)
                raise
        finally:
            # Join any uploads/polls already in flight; they cannot be
            # aborted mid-request.  wait=False above only stops pending ones.
            executor.shutdown(wait=True)

        return [outcomes[i] for i in sorted(outcomes)]

    # ── main worker logic ───────────────────────────────────────────
    def run(self):
        tmp_dir: Path | None = None
        try:
            file_path = Path(self._file_path)
            if not file_path.exists():
                self.error.emit(f"文件不存在: {file_path}")
                return

            # 1. Decide whether the book has to be cut up at all.
            try:
                total_pages = page_count(file_path)
            except Exception as exc:
                self.error.emit(f"读取PDF页数失败: {exc}")
                return

            if total_pages <= self._max_pages:
                parts = [PdfPart(0, 1, total_pages, file_path)]
            else:
                count = math.ceil(total_pages / self._max_pages)
                self.progress.emit(
                    2,
                    f"共 {total_pages} 页，超过 {self._max_pages} 页上限，"
                    f"切分为 {count} 个批次...",
                )
                tmp_dir = Path(tempfile.mkdtemp(prefix="tingbook_mineru_"))
                try:
                    parts = split_pdf(file_path, tmp_dir, self._max_pages)
                except Exception as exc:
                    self.error.emit(f"切分PDF失败: {exc}")
                    return
                self.progress.emit(5, f"已切分为 {len(parts)} 个批次，开始并行上传...")

            # 2. Convert every part concurrently.
            client = httpx.Client()
            try:
                markdowns = self._convert_parts(client, parts)
            finally:
                client.close()

            # 3. Stitch the parts back together in page order.
            self.progress.emit(99, "正在合并各批次内容...")
            markdown = "\n\n".join(m.strip() for m in markdowns if m and m.strip())

            # 4. Auto-save next to the source file.
            if self._output_dir:
                try:
                    path = write_source_markdown(
                        self._output_dir, self._book_name, markdown,
                    )
                    self.progress.emit(100, f"已自动保存: {path}")
                except Exception as exc:
                    # The conversion itself succeeded — report the save
                    # failure without discarding the result.
                    self.progress.emit(100, f"自动保存失败: {exc}")
            else:
                self.progress.emit(100, "转换完成!")

            self.finished.emit(markdown)

        except _Cancelled:
            self.error.emit("用户取消了操作")
        except Exception as e:
            message = f"转换出错: {str(e)}"
            if tmp_dir is not None:
                message += f"（已切分的批次保留在 {tmp_dir}）"
            self.error.emit(message)
        else:
            # Only clean up when the whole run succeeded; on failure the
            # parts are deliberately kept so the problem can be inspected.
            if tmp_dir is not None:
                shutil.rmtree(tmp_dir, ignore_errors=True)

    def _get_markdown(self, client: httpx.Client,
                      entry: dict, result_data: dict) -> str | None:
        """Try multiple strategies to extract markdown content."""
        # 1. Direct markdown content in response
        md = self._find_str(entry, ("md_content", "markdown", "content"))
        if not md:
            md = self._find_str(result_data, ("md_content", "markdown", "content"))
        if md:
            return md

        # 2. Download from markdown URL
        md_url = (
            self._find_str(entry, ("full_md_url", "md_url", "markdown_url"))
            or self._find_str(result_data, ("full_md_url", "md_url", "markdown_url"))
        )
        if md_url:
            try:
                resp = client.get(md_url, timeout=60)
                if resp.status_code == 200 and resp.text.strip():
                    return resp.text.strip()
            except Exception:
                pass

        # 3. Download from zip URL
        zip_url = (
            self._find_str(entry, ("full_zip_url", "zip_url", "archive_url"))
            or self._find_str(result_data, ("full_zip_url", "zip_url", "archive_url"))
        )
        if zip_url:
            try:
                return self._download_md_from_zip(client, zip_url)
            except Exception:
                pass

        return None
