"""
听书工坊 (Audiobook Workshop) - TTS synthesis worker.

Posts each TTS entry to the IndexTTS2 server, collects the
returned WAV audio, and assembles per-chapter audio files
using pydub.
"""

from __future__ import annotations

import base64
import io
from pathlib import Path

import httpx
from pydub import AudioSegment
from PyQt6.QtCore import QThread, pyqtSignal


class TTSWorker(QThread):
    """Background thread for synthesising chapter audio.

    Signals
    -------
    chapter_progress(int, str, str)
        ``(chapter_index, status, message)`` — same pattern as JsonGenWorker.
    entry_progress(int, int, int)
        ``(chapter_index, current_entry, total_entries)``
    log_message(str)
        Free-form log text.
    finished(list)
        List of output file paths (str) for successfully synthesised chapters.
    error(str)
        Fatal error description.
    """

    chapter_progress = pyqtSignal(int, str, str)
    entry_progress = pyqtSignal(int, int, int)
    log_message = pyqtSignal(str)
    finished = pyqtSignal(list)
    error = pyqtSignal(str)

    def __init__(
        self,
        chapter_results: list[dict],
        selected_indices: list[int],
        prompt_audio_mapping: dict[str, str],  # category → wav path
        tts_server_url: str,
        output_dir: str,
    ) -> None:
        super().__init__()
        self._chapter_results = chapter_results
        self._selected_indices = selected_indices
        self._prompt_audio_mapping = prompt_audio_mapping
        self._server_url = tts_server_url.rstrip("/")
        self._output_dir = Path(output_dir)
        self._cancelled = False

    def cancel(self) -> None:
        self._cancelled = True

    # ------------------------------------------------------------------
    # Main logic
    # ------------------------------------------------------------------

    def run(self) -> None:
        try:
            self._output_dir.mkdir(parents=True, exist_ok=True)

            # Pre-encode prompt audio files to base64
            prompt_b64: dict[str, str] = {}
            for cat, wav_path in self._prompt_audio_mapping.items():
                try:
                    data = Path(wav_path).read_bytes()
                    prompt_b64[cat] = base64.b64encode(data).decode("ascii")
                    self.log_message.emit(f"Loaded prompt audio for [{cat}]: {wav_path}")
                except Exception as exc:
                    self.log_message.emit(f"Warning: failed to load [{cat}] audio: {exc}")

            if not prompt_b64:
                self.error.emit("No valid prompt audio files loaded.")
                return

            # Determine a fallback category (first available)
            fallback_cat = next(iter(prompt_b64))

            output_files: list[str] = []
            client = httpx.Client(timeout=120.0)

            for cr in self._chapter_results:
                if self._cancelled:
                    break

                ch_idx = cr["chapter_index"]
                if ch_idx not in self._selected_indices:
                    continue

                ch_title = cr["chapter_title"]
                entries = cr.get("entries", [])
                total = len(entries)

                self.chapter_progress.emit(ch_idx, "processing", f"合成中 ({total} entries)")
                self.log_message.emit(f"--- Chapter P{ch_idx:02d}_{ch_title} ({total} entries) ---")

                segments: list[AudioSegment] = []

                for i, entry in enumerate(entries):
                    if self._cancelled:
                        break

                    self.entry_progress.emit(ch_idx, i + 1, total)

                    speaker = entry.get("speaker", "旁白")
                    text = entry.get("content", "")
                    emo_vector = entry.get("emo_vector", [0.0] * 8)
                    delay_ms = entry.get("delay", 500)

                    if not text.strip():
                        self.log_message.emit(f"  [{i+1}/{total}] Empty content, skipping")
                        continue

                    # Resolve prompt audio: speaker name IS the category after apply_classifications
                    b64 = prompt_b64.get(speaker) or prompt_b64.get(fallback_cat, "")
                    if not b64:
                        self.log_message.emit(f"  [{i+1}/{total}] No prompt audio for '{speaker}', skipping")
                        continue

                    payload = {
                        "tts_text": text,
                        "prompt_audio": b64,
                        "emo_control_method": 2,
                        "emo_vector": emo_vector,
                    }

                    try:
                        resp = client.post(f"{self._server_url}/api/tts", json=payload)
                        resp.raise_for_status()
                        resp_data = resp.json()

                        audio_b64 = resp_data.get("audio", "")
                        if not audio_b64:
                            self.log_message.emit(f"  [{i+1}/{total}] No audio in response")
                            continue

                        wav_bytes = base64.b64decode(audio_b64)
                        seg = AudioSegment.from_wav(io.BytesIO(wav_bytes))
                        segments.append(seg)

                        # Add silence gap
                        if delay_ms > 0:
                            segments.append(AudioSegment.silent(duration=delay_ms))

                        self.log_message.emit(
                            f"  [{i+1}/{total}] OK ({len(wav_bytes)} bytes, {len(seg)}ms)"
                        )

                    except Exception as exc:
                        self.log_message.emit(f"  [{i+1}/{total}] Error: {exc}")

                if self._cancelled:
                    break

                # Assemble chapter audio
                if segments:
                    combined = segments[0]
                    for seg in segments[1:]:
                        combined += seg

                    filename = f"P{ch_idx:02d}_{ch_title}.wav"
                    out_path = self._output_dir / filename
                    combined.export(str(out_path), format="wav")
                    output_files.append(str(out_path))

                    self.chapter_progress.emit(ch_idx, "done", f"Saved: {filename}")
                    self.log_message.emit(f"  => Saved {filename} ({len(combined)}ms)")
                else:
                    self.chapter_progress.emit(ch_idx, "error", "No audio segments produced")
                    self.log_message.emit(f"  => No audio segments for P{ch_idx:02d}_{ch_title}")

            client.close()

            if not self._cancelled:
                self.finished.emit(output_files)

        except Exception as exc:
            self.error.emit(str(exc))
