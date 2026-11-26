"""Google Cloud Translation (Basic v2, standard NMT model) for public site text.

Server-side only. The API key comes from the environment, is sent in a header
(never in the URL) and is never logged. Send public site content only.
"""

from __future__ import annotations

import os
import re
from html import escape, unescape

import requests

_ENDPOINT = "https://translation.googleapis.com/language/translate/v2"
# Google allows 128 strings per request and recommends about 5,000 characters.
_MAX_ITEMS = 128
_MAX_CHARS = 5_000
_MAX_TEXT_CHARS = 30_000
_TIMEOUT_SECONDS = 20

# Brand and series names are fixed: Google must never translate them itself.
GLOSSARY: dict[str, dict[str, str]] = {
    "銘印鑽石": {"en": "Imprint Diamond", "ja": "インプリントダイヤモンド", "ko": "임프린트 다이아몬드"},
    "滿月鑽石": {"en": "First Love Diamond", "ja": "ファーストラブダイヤモンド", "ko": "퍼스트 러브 다이아몬드"},
    "寵物鑽石": {"en": "Pet Diamond", "ja": "ペットダイヤモンド", "ko": "펫 다이아몬드"},
    "結髮鑽石": {"en": "Love Diamond", "ja": "ラブダイヤモンド", "ko": "러브 다이아몬드"},
    "全家福鑽石": {"en": "Family Diamond", "ja": "ファミリーダイヤモンド", "ko": "패밀리 다이아몬드"},
    "生命鑽石": {"en": "Heirloom Diamond", "ja": "エアルームダイヤモンド", "ko": "에어룸 다이아몬드"},
    "真我鑽石": {"en": "Signature Diamond", "ja": "シグネチャーダイヤモンド", "ko": "시그니처 다이아몬드"},
    "培育鑽石": {"en": "lab-grown diamond", "ja": "ラボグロウンダイヤモンド", "ko": "랩그로운 다이아몬드"},
}
_TERM_RE = re.compile("|".join(sorted(map(re.escape, GLOSSARY), key=len, reverse=True)))
_KEEP_RE = re.compile(r'<span translate="no">(.*?)</span>', re.DOTALL)


class TranslationError(RuntimeError):
    """Raised so callers can keep the Chinese text and retry later."""


def is_configured() -> bool:
    return bool(os.environ.get("GOOGLE_TRANSLATE_API_KEY", "").strip())


def protect_terms(text: str, target: str) -> str:
    """HTML for Google: fixed terms arrive pre-translated and marked do-not-translate."""
    return _TERM_RE.sub(
        lambda m: f'<span translate="no">{GLOSSARY[m[0]][target]}</span>',
        escape(text, quote=False),
    )


def restore_terms(translated: str) -> str:
    return unescape(_KEEP_RE.sub(r"\1", translated))


def _batches(texts: list[str]):
    batch: list[str] = []
    size = 0
    for text in texts:
        if len(text) > _MAX_TEXT_CHARS:
            raise TranslationError("One text is longer than Google's request limit")
        if batch and (len(batch) >= _MAX_ITEMS or size + len(text) > _MAX_CHARS):
            yield batch
            batch, size = [], 0
        batch.append(text)
        size += len(text)
    if batch:
        yield batch


def translate_texts(texts: list[str], target: str) -> list[str]:
    """Translate Traditional Chinese texts into `target` (en, ja or ko), in order."""
    key = os.environ.get("GOOGLE_TRANSLATE_API_KEY", "").strip()
    if not key:
        raise TranslationError("GOOGLE_TRANSLATE_API_KEY is not set")

    results: list[str] = []
    for batch in _batches([protect_terms(text, target) for text in texts]):
        try:
            response = requests.post(
                _ENDPOINT,
                headers={"X-goog-api-key": key},
                json={
                    "q": batch,
                    "source": "zh-TW",
                    "target": target,
                    "format": "html",
                    "model": "nmt",
                },
                timeout=_TIMEOUT_SECONDS,
            )
            response.raise_for_status()
            translated = [
                restore_terms(item["translatedText"])
                for item in response.json()["data"]["translations"]
            ]
        except (requests.RequestException, ValueError, KeyError, TypeError) as exc:
            raise TranslationError(f"Google Translation failed: {type(exc).__name__}") from exc
        if len(translated) != len(batch):
            raise TranslationError("Google returned the wrong number of items")
        results.extend(translated)
    return results
