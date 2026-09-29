"""
Content language: pick the prompt set that matches the transcript.

AutoClip's prompts were written for Chinese content. For English (and other
Latin-script) transcripts the pipeline now switches to the English prompt set in
``backend/prompt/en/`` — the same instructions, output formats and parsing rules,
translated. Only the words sent to the model change; chunking, timestamp
refinement, scoring thresholds and cutting are untouched.

- ``detect_language``: counts CJK characters vs Latin letters. Anything that is
  not clearly Latin-script stays ``zh`` so existing (Chinese, Japanese, Korean,
  Cyrillic, ...) behaviour is exactly what it was before.
- ``AUTOCLIP_CONTENT_LANGUAGE`` (``auto`` / ``zh`` / ``en``) forces a choice.
- Step 1 decides and writes ``content_language.json`` into the project's
  metadata dir; steps 2–5 read it back (or re-detect from the saved subtitle
  chunks when a later step is re-run on its own).
- ``localize_prompt_path`` maps a Chinese prompt path to its English twin,
  keeping the category folder (``knowledge/`` etc.). User-supplied prompt paths
  outside ``backend/prompt`` are never swapped.
"""
from __future__ import annotations

import json
import logging
import os
import re
from pathlib import Path
from typing import Any, Dict, Iterable, Mapping, Optional

logger = logging.getLogger(__name__)

ZH = "zh"
EN = "en"
SUPPORTED = (ZH, EN)
LANGUAGE_FILE = "content_language.json"
ENV_OVERRIDE = "AUTOCLIP_CONTENT_LANGUAGE"

# Chinese prompt file name -> English prompt file name (inside prompt/en/<category>/)
EN_PROMPT_NAMES: Dict[str, str] = {
    "大纲.txt": "outline.txt",
    "时间点.txt": "timeline.txt",
    "推荐理由.txt": "scoring.txt",
    "标题生成.txt": "title.txt",
    "主题聚类.txt": "clustering.txt",
    "collection_title.txt": "collection_title.txt",
}

# CJK ideographs + kana + hangul: any of these means "keep the original prompts".
_CJK_RE = re.compile(r"[぀-ヿ㐀-䶿一-鿿가-힯豈-﫿]")
_LATIN_RE = re.compile(r"[A-Za-zÀ-ɏ]")

# Share of CJK characters (among CJK + Latin letters) below which text counts as Latin-script.
# Chinese transcripts full of English terms ("我们用AI做了ChatGPT的demo") sit far above this.
CJK_SHARE_MAX_FOR_EN = 0.10
MIN_LATIN_LETTERS = 20


def _prompt_dir() -> Path:
    from ..core.shared_config import PROMPT_DIR
    return Path(PROMPT_DIR)


def _override() -> Optional[str]:
    value = (os.getenv(ENV_OVERRIDE) or "").strip().lower()
    if value in SUPPORTED:
        return value
    if value and value != "auto":
        logger.warning("%s=%r is not one of auto / zh / en; using auto-detection", ENV_OVERRIDE, value)
    return None


def script_stats(text: str) -> Dict[str, int]:
    return {"cjk": len(_CJK_RE.findall(text or "")), "latin": len(_LATIN_RE.findall(text or ""))}


def detect_language(text: str) -> str:
    """``en`` for clearly Latin-script text, otherwise ``zh`` (the original behaviour)."""
    stats = script_stats(text)
    cjk, latin = stats["cjk"], stats["latin"]
    if latin < MIN_LATIN_LETTERS:
        return ZH
    if cjk / (cjk + latin) < CJK_SHARE_MAX_FOR_EN:
        return EN
    return ZH


def _entries_text(entries: Iterable[Mapping[str, Any]]) -> str:
    return " ".join(str(e.get("text") or "") for e in entries if isinstance(e, Mapping))


def decide_language(srt_entries: Iterable[Mapping[str, Any]]) -> Dict[str, Any]:
    text = _entries_text(srt_entries)
    stats = script_stats(text)
    forced = _override()
    if forced:
        return {"language": forced, "source": "env", **stats}
    return {"language": detect_language(text), "source": "auto", **stats}


def save_language(info: Dict[str, Any], metadata_dir: Path) -> Path:
    path = Path(metadata_dir) / LANGUAGE_FILE
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(info, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def load_language(metadata_dir: Optional[Path]) -> str:
    """Language decided by step 1 for this project. Falls back to re-detecting from the
    saved subtitle chunks, then to ``zh``. The env override always wins."""
    forced = _override()
    if forced:
        return forced
    if metadata_dir is None:
        return ZH
    path = Path(metadata_dir) / LANGUAGE_FILE
    if path.exists():
        try:
            value = json.loads(path.read_text(encoding="utf-8")).get("language")
            if value in SUPPORTED:
                return value
        except Exception as e:  # noqa: BLE001
            logger.warning("Could not read %s: %s", path, e)
    try:
        from .quality import load_srt_chunks
        entries = load_srt_chunks(Path(metadata_dir))
    except Exception:  # noqa: BLE001
        entries = []
    return detect_language(_entries_text(entries)) if entries else ZH


def localize_prompt_path(path: Any, language: str) -> Path:
    """English twin of a bundled Chinese prompt file; the original path when there is none."""
    original = Path(path)
    if language != EN:
        return original
    en_name = EN_PROMPT_NAMES.get(original.name)
    if not en_name:
        return original
    prompt_dir = _prompt_dir()
    try:
        rel = original.resolve().relative_to(prompt_dir.resolve())
    except ValueError:
        return original  # a user's custom prompt: never replace it
    candidates = [prompt_dir / EN / rel.parent / en_name, prompt_dir / EN / en_name]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    logger.warning("No English prompt for %s; using the original", original)
    return original


def read_prompt(path: Any, language: str) -> str:
    chosen = localize_prompt_path(path, language)
    if chosen != Path(path):
        logger.info("Using English prompt: %s", chosen)
    return chosen.read_text(encoding="utf-8")


def transcription_language(configured: Optional[str] = "auto") -> str:
    """Whisper language. Only when it is left on ``auto`` and ``AUTOCLIP_CONTENT_LANGUAGE`` forces a
    language is the forced one used (stops auto-detection being fooled by a music intro)."""
    configured = (configured or "auto").strip() or "auto"
    forced = _override()
    if configured == "auto" and forced:
        return forced
    return configured


def language_of_payload(payload: Any) -> str:
    """For one-off calls outside the pipeline (regenerate a title): detect from the data itself."""
    forced = _override()
    if forced:
        return forced
    try:
        text = json.dumps(payload, ensure_ascii=False, default=str)
    except Exception:  # noqa: BLE001
        text = str(payload)
    # JSON keys are ASCII; drop them so they don't count as Latin content.
    text = re.sub(r'"[A-Za-z_]+"\s*:', " ", text)
    return detect_language(text)
