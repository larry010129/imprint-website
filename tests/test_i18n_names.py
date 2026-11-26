"""Customer names shown as surname + title use the saved surname list."""

from __future__ import annotations

import pytest

from app.i18n import load_catalog, translate_html

# The surname + title forms in the published stories when the list was added.
PUBLISHED = (
    "吳小姐 周小姐 張小姐 徐小姐 曾小姐 朱小姐 林先生 林小姐 楊先生 沈小姐 "
    "洪先生 簡小姐 蔡先生 謝小姐 譚小姐 賴先生 郭小姐 陳先生 陳小姐 高小姐"
).split()


@pytest.mark.parametrize(
    "language, expected",
    [("en", "Ms. Shen"), ("ja", "沈様"), ("ko", "선 님")],
)
def test_story_card_name(language, expected):
    out, missing = translate_html("<strong>沈小姐</strong>", load_catalog(language))
    assert expected in out and missing == []


@pytest.mark.parametrize("language", ["en", "ja", "ko"])
def test_every_published_name_has_a_translation(language):
    catalog = load_catalog(language)
    assert [name for name in PUBLISHED if not catalog.get(name)] == []


def test_japanese_uses_japanese_character_forms():
    catalog = load_catalog("ja")
    assert (catalog.get("吳小姐"), catalog.get("黃先生")) == ("呉様", "黄様")
    assert catalog.get("林先生") == "林様"


def test_unknown_or_differently_written_names_stay_chinese():
    catalog = load_catalog("en")
    for name in ("歐陽小姐", "小美", "王大明", "沈小姐與家人合照紀念"):
        out, _ = translate_html(f"<strong>{name}</strong>", catalog)
        assert name in out, name
