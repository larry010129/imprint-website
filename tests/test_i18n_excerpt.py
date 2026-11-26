"""Cut-off customer stories must use the saved translation of the whole story."""

from __future__ import annotations

from app.i18n import Catalog, excerpt_of, translate_html

STORY = "".join(f"第{i}段回憶，收到鑽石的那一刻真的很感動。" for i in range(8))
ENGLISH = "I was deeply moved when the diamond arrived. " * 12


def home_card(story: str) -> str:
    """The same cut public/js/home-wall.js makes."""
    return f"<p>「{story[:88]}…」</p>"


def test_quoted_cut_off_story_is_translated():
    out, missing = translate_html(home_card(STORY), {STORY: ENGLISH.strip()})
    assert missing == []
    assert "“I was deeply moved" in out and "…”" in out and "回憶" not in out


def test_story_with_line_breaks_still_matches():
    story = STORY.replace("。", "。\n", 3)
    saved = {" ".join(story.split()): "Moved."}
    out, missing = translate_html(home_card(story), saved)
    assert missing == [] and "“Moved.”" in out


def test_cut_translation_ends_on_a_whole_word():
    cut = excerpt_of(ENGLISH.strip(), 0.4)
    assert cut.endswith("…") and cut[:-1].split()[-1] in ENGLISH.split() + ["arrived"]
    assert excerpt_of("Short.", 0.4) == "Short."


def test_unknown_or_short_cut_off_text_stays_chinese():
    assert Catalog({STORY: "x"}).get("完全不同的內容" * 12 + "…") is None
    assert Catalog({STORY: "x"}).get(STORY[:20] + "…") is None


def test_browser_script_has_the_same_excerpt_rule():
    script = open("public/js/i18n-client.js", encoding="utf-8").read()
    assert "return excerpt(key);" in script and "key.length <= 60" in script
