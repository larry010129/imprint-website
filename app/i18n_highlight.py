"""Translate banner text that is split by styling as the whole sentence it is.

The home banners colour "DNA" and italicise part of the first title, which cuts
one saved sentence into pieces that match nothing. When the catalog has the whole
sentence, it replaces the block and the styling is put back on the translation.
(public/js/i18n-client.js does the same for banners built by JavaScript.)
"""

from __future__ import annotations

import re
from html import escape, unescape

_BLOCK_RE = re.compile(
    r"""(<([a-z][a-z0-9]*)\b[^<>]*\sclass="gh-hero__(?:lead|title)\b[^"]*"[^<>]*>)"""
    r"(.*?)(</\2\s*>)",
    re.DOTALL,
)
_STYLING_RE = re.compile(r'<span class="gh-dna">|</span>|</?em>')
_DNA_RE = re.compile(r"(?<![A-Za-z])DNA(?![A-Za-z])")
_PLACEHOLDER_RE = re.compile("\x00(\\d+)\x00")


def _restyle(target: str, italic: bool) -> str:
    text = escape(target, quote=False)
    comma = re.search("[,，、]\\s*", text) if italic else None
    if comma and comma.end() < len(text):
        text = f"{text[: comma.end()]}<em>{text[comma.end():]}</em>"
    return _DNA_RE.sub('<span class="gh-dna">DNA</span>', text)


def swap_styled_blocks(html: str, lookup) -> tuple[str, list[str]]:
    """Replace known styled blocks with placeholders; returns (html, replacements)."""
    done: list[str] = []

    def swap(match: re.Match[str]) -> str:
        inner = match[3]
        plain = _STYLING_RE.sub("", inner)
        # Only styled text qualifies: any other markup keeps the normal handling.
        if plain == inner or "<" in plain:
            return match[0]
        target = lookup(" ".join(unescape(plain).split()))
        if target is None:
            return match[0]
        done.append(_restyle(target, "<em>" in inner))
        return f"{match[1]}\x00{len(done) - 1}\x00{match[4]}"

    return _BLOCK_RE.sub(swap, html), done


def restore_styled_blocks(html: str, done: list[str]) -> str:
    return _PLACEHOLDER_RE.sub(lambda m: done[int(m[1])], html) if done else html
