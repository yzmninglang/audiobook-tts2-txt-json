from __future__ import annotations
import json
import time
from PyQt6.QtCore import QThread, pyqtSignal
from openai import OpenAI
from gui.core.pipeline import (
    extract_speakers_from_entries,
    build_classify_prompt,
    build_speaker_mapping,
    apply_speaker_replacements,
    extract_json_from_response,
)

class SpeakerExtractWorker(QThread):
    finished = pyqtSignal(list)   # list of (name, count) tuples
    error = pyqtSignal(str)

    def __init__(self, chapter_results: list):
        super().__init__()
        self._chapter_results = chapter_results

    def run(self):
        try:
            all_entries = []
            for cr in self._chapter_results:
                entries = cr.get("entries", [])
                all_entries.append(entries)
            speakers = extract_speakers_from_entries(all_entries)
            self.finished.emit(speakers)
        except Exception as e:
            self.error.emit(f"提取角色失败: {str(e)}")


class SpeakerClassifyWorker(QThread):
    finished = pyqtSignal(dict)   # classifications dict
    error = pyqtSignal(str)

    def __init__(self, speaker_names: list, api_key: str, base_url: str, model: str):
        super().__init__()
        self._speaker_names = speaker_names
        self._api_key = api_key
        self._base_url = base_url
        self._model = model

    def run(self):
        try:
            # Filter out narration
            names = [n for n in self._speaker_names if n != "旁白"]
            if not names:
                self.finished.emit({})
                return

            prompt = build_classify_prompt(names)
            client = OpenAI(api_key=self._api_key, base_url=self._base_url)

            max_retries = 3
            for attempt in range(max_retries):
                try:
                    response = client.chat.completions.create(
                        model=self._model,
                        messages=[{"role": "user", "content": prompt}],
                        temperature=0.1,
                        max_tokens=600000,
                    )
                    raw = response.choices[0].message.content

                    # Clean markdown blocks
                    text = raw.strip()
                    if text.startswith("```json"):
                        text = text[len("```json"):]
                    elif text.startswith("```"):
                        text = text[3:]
                    if text.endswith("```"):
                        text = text[:-3]
                    text = text.strip()

                    result = json.loads(text)
                    self.finished.emit(result)
                    return
                except Exception as e:
                    if attempt < max_retries - 1:
                        time.sleep(2)
                    else:
                        self.error.emit(f"AI分类失败: {str(e)}")
        except Exception as e:
            self.error.emit(f"分类出错: {str(e)}")


class SpeakerReplaceWorker(QThread):
    finished = pyqtSignal(list)   # updated chapter results
    error = pyqtSignal(str)

    def __init__(self, chapter_results: list, classifications: dict):
        super().__init__()
        self._chapter_results = chapter_results
        self._classifications = classifications

    def run(self):
        try:
            mapping = build_speaker_mapping(self._classifications)
            updated = []
            for cr in self._chapter_results:
                entries = cr.get("entries", [])
                apply_speaker_replacements(entries, mapping)
                updated.append(cr)
            self.finished.emit(updated)
        except Exception as e:
            self.error.emit(f"替换角色失败: {str(e)}")
