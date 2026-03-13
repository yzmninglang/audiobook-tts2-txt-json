from __future__ import annotations
import io
import time
import uuid
import zipfile
from pathlib import Path
from PyQt6.QtCore import QThread, pyqtSignal
import httpx


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
                 endpoint: str = "https://mineru.net"):
        super().__init__()
        self._file_path = file_path
        self._api_token = api_token.strip()
        self._endpoint = endpoint.rstrip("/")
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

    # ── main worker logic ───────────────────────────────────────────
    def run(self):
        try:
            self.progress.emit(5, "准备上传文件...")

            file_path = Path(self._file_path)
            data_id = uuid.uuid4().hex[:12]

            with httpx.Client() as client:
                # Step 1: Create upload URL (file-urls/batch)
                self.progress.emit(10, "正在创建上传任务...")
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
                    self.error.emit("创建上传任务失败: 未获取到上传URL")
                    return

                batch_id = self._find_str(create_data, ("batch_id", "batchId")) or ""
                if not batch_id:
                    self.error.emit("创建上传任务失败: 未获取到 batch_id")
                    return

                # Step 2: Upload file to presigned URL (PUT)
                self.progress.emit(20, "正在上传PDF文件...")
                file_bytes = file_path.read_bytes()
                for attempt in range(self._MAX_RETRIES):
                    try:
                        up_resp = client.put(
                            upload_url, content=file_bytes,
                            timeout=self._UPLOAD_TIMEOUT,
                        )
                        if up_resp.status_code < 400:
                            break
                        if not self._is_retryable_status(up_resp.status_code):
                            self.error.emit(
                                f"上传文件失败: HTTP {up_resp.status_code}"
                            )
                            return
                    except Exception as exc:
                        if not self._is_retryable_error(exc) or (attempt + 1) >= self._MAX_RETRIES:
                            self.error.emit(f"上传文件失败: {exc}")
                            return
                    time.sleep(self._RETRY_BACKOFF * (attempt + 1))
                else:
                    self.error.emit("上传文件失败: 重试次数已用完")
                    return

                self.progress.emit(35, "文件上传成功，等待解析...")

                # Step 3: Poll for result (extract-results/batch/{batch_id})
                start_time = time.monotonic()
                while True:
                    if self._cancelled:
                        self.error.emit("用户取消了操作")
                        return

                    elapsed = time.monotonic() - start_time
                    if elapsed >= self._POLL_TIMEOUT:
                        self.error.emit("解析超时，请稍后重试")
                        return

                    time.sleep(self._POLL_INTERVAL)
                    progress_pct = 35 + min(50, int(elapsed / self._POLL_TIMEOUT * 50))
                    self.progress.emit(progress_pct, f"正在解析... (已等待 {int(elapsed)}秒)")

                    try:
                        result_resp = self._request_json(
                            client, "GET",
                            f"extract-results/batch/{batch_id}",
                        )
                    except Exception:
                        continue  # retry on next poll

                    result_data = self._extract_data(result_resp, "查询解析结果")
                    entry = self._resolve_result_entry(result_data, data_id)

                    state = str(entry.get("state", "")).strip().lower()
                    if state == "success":
                        state = "done"

                    if state in ("done", "finished"):
                        self.progress.emit(90, "解析完成，正在获取结果...")
                        md_content = self._get_markdown(client, entry, result_data)
                        if md_content:
                            self.progress.emit(100, "转换完成!")
                            self.finished.emit(md_content)
                            return
                        self.error.emit("解析完成但未找到Markdown内容")
                        return

                    if state in ("failed", "cancelled"):
                        reason = (
                            entry.get("error")
                            or entry.get("err_msg")
                            or entry.get("message")
                            or "未知错误"
                        )
                        self.error.emit(f"解析失败: {reason}")
                        return

        except Exception as e:
            self.error.emit(f"转换出错: {str(e)}")

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
