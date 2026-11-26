"""Banner sentences split by styling must still use their saved translation."""

from __future__ import annotations

import pytest

from app.home_banners_ssr import _format_lead, _format_title
from app.i18n import load_catalog, translate_html

LEAD = "以髮絲與 DNA 培育專屬鑽石，誠摯邀請您成為我們的合作夥伴。"


def hero(lead: str, title: str = "標題") -> str:
    return (
        f'<h2 class="gh-hero__title reveal">{_format_title(title, 0)}</h2>'
        f'<p class="gh-hero__lead reveal reveal-d2">{_format_lead(lead)}</p>'
    )


def test_coloured_dna_sentence_uses_the_whole_translation():
    saved = {LEAD: "We grow DNA diamonds <together>.", "標題": "Title"}
    out, missing = translate_html(hero(LEAD), saved)
    assert missing == []
    assert 'We grow <span class="gh-dna">DNA</span> diamonds &lt;together&gt;.' in out
    assert "培育" not in out


def test_split_title_keeps_its_italic_half():
    title = "思念，永遠都在"
    out, missing = translate_html(hero("段落", title), {title: "Memory, always here", "段落": "P"})
    assert missing == []
    assert "Memory, <em>always here</em></h2>" in out


def test_japanese_result_is_not_looked_up_again():
    out, missing = translate_html(
        hero(LEAD, "標題"), {LEAD: "専用のDNAダイヤモンド", "標題": "見出し"}, spaced=False
    )
    assert missing == []
    assert '専用の<span class="gh-dna">DNA</span>ダイヤモンド' in out


@pytest.mark.parametrize("language", ["ja", "ko"])
def test_english_banner_headings_are_translated(language):
    catalog = load_catalog(language)
    for word in ("Imprint Diamond", "First Love", "Companion", "Love", "Family",
                 "Heirloom", "UNIQUE"):
        out, _ = translate_html(f'<p class="gh-script reveal">{word}</p>', catalog)
        assert catalog.get(word) and f">{catalog.get(word)}</p>" in out, word
    # the same word outside a banner heading is left alone
    out, _ = translate_html("<p>Love</p><a>Family</a>", catalog)
    assert out == "<p>Love</p><a>Family</a>"


def test_english_and_unknown_headings_stay_as_written():
    html = '<p class="gh-script">First Love</p>'
    assert translate_html(html, load_catalog("en"))[0] == html
    other = '<p class="gh-script">Brand New Line</p>'
    assert translate_html(other, load_catalog("ja"))[0] == other


def test_without_a_whole_sentence_the_pieces_still_translate():
    pieces = {"以髮絲與": "With hair and", "培育專屬鑽石，誠摯邀請您成為我們的合作夥伴。": "join us.", "標題": "T"}
    out, missing = translate_html(hero(LEAD), pieces)
    assert missing == []
    assert "With hair and" in out and "join us." in out
