from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app import i18n_store, translator_google
from app.i18n import language_links, load_catalog, page_routes, translate_html
from app.content import format_faq_answer_html
from config.settings import settings
from main import app

ROUTE = "/what-is-dna-diamond"


def test_translate_html_text_and_attributes_only():
    html = (
        '<p title="首頁">首頁</p><script>var a="首頁";</script>'
        '<span translate="no"><a>中文</a></span><p>沒有翻譯</p>'
    )
    out, missing = translate_html(html, {"首頁": 'Home "A" <b>'})
    assert 'title="Home &quot;A&quot; &lt;b&gt;"' in out
    assert '> Home "A" &lt;b&gt; </p>' in out
    assert 'var a="首頁"' in out
    assert "<a>中文</a>" in out
    assert missing == ["沒有翻譯"]


def test_language_links_only_for_translated_pages():
    assert [x["href"] for x in language_links(ROUTE, "en")] == [
        ROUTE, f"/en{ROUTE}", f"/ja{ROUTE}", f"/ko{ROUTE}"
    ]
    assert language_links("/admin") == []
    assert language_links("/api/catalog") == []


def test_english_page_is_translated_and_not_indexed():
    client = TestClient(app)
    response = client.get(f"/en{ROUTE}")
    assert response.status_code == 200
    html = response.text
    assert '<html lang="en">' in html
    assert "What Is a DNA Diamond?" in html
    assert '<meta name="robots" content="noindex, nofollow">' in html
    assert f'/en{ROUTE}">' in html
    chinese = client.get(ROUTE).text
    assert '<html lang="zh-Hant-TW">' in chinese
    assert "什麼是 DNA 鑽石" in chinese
    assert f'href="/en{ROUTE}"' in chinese


def test_english_page_has_no_untranslated_template_text():
    # Re-running the extractor with no catalog entries left must find nothing.
    html = TestClient(app).get(f"/en{ROUTE}").text
    _out, missing = translate_html(html, {})
    # The registered company name stays in Chinese on purpose.
    assert [m for m in missing if "心之銘印鑽石有限公司" not in m] == []


@pytest.mark.parametrize(
    "language, heading, sign_in",
    [
        ("ja", "DNAダイヤモンドとは", "ログイン"),
        ("ko", "DNA 다이아몬드란?", "로그인"),
    ],
)
def test_japanese_and_korean_pages(language, heading, sign_in):
    client = TestClient(app)
    html = client.get(f"/{language}{ROUTE}").text
    assert f'<html lang="{language}">' in html
    assert heading in html
    nav = client.get(
        "/htmx/nav-state", headers={"HX-Current-URL": f"http://testserver/{language}{ROUTE}"}
    ).text
    assert sign_in in nav and "會員登入" not in nav


@pytest.mark.parametrize("language", ["en", "ja", "ko"])
def test_catalog_covers_every_phrase_on_every_public_page(language):
    client = TestClient(app)
    catalog = load_catalog(language)
    missing = {}
    for route in page_routes():
        response = client.get(route, follow_redirects=False)
        if response.status_code != 200:
            continue
        _out, gaps = translate_html(response.text, catalog)
        if gaps:
            missing[route] = gaps
    assert missing == {}


@pytest.mark.parametrize("prefix", ["en", "ja", "ko"])
def test_translated_pages_never_open_the_cms_editor(monkeypatch, prefix):
    monkeypatch.setattr("app.auth.request_is_admin", lambda request: True)
    client = TestClient(app)
    assert "data-cms-site-edit" in client.get(f"{ROUTE}?cms_edit=1").text
    response = client.get(f"/{prefix}{ROUTE}?cms_edit=1", follow_redirects=False)
    assert response.status_code == 302
    assert response.headers["location"] == f"{ROUTE}?cms_edit=1"


def test_country_code_addresses_are_not_served():
    client = TestClient(app)
    assert client.get(f"/jp{ROUTE}").status_code == 404
    assert client.get(f"/kr{ROUTE}").status_code == 404


def test_japanese_text_gets_no_added_spaces():
    out, _ = translate_html("<a>首頁</a>", {"首頁": "ホーム"}, spaced=False)
    assert out == "<a>ホーム</a>"


def test_admin_and_api_have_no_translated_address():
    client = TestClient(app)
    for path in ("/en/admin", "/en/api/catalog", "/ja/admin/settings", "/ko/nope"):
        assert client.get(path, follow_redirects=False).status_code == 404, path


def test_every_language_serves_other_public_pages_with_prefixed_links():
    client = TestClient(app)
    for locale in ("en", "ja", "ko"):
        html = client.get(f"/{locale}/lab-grown-diamond").text
        assert f'<html lang="{locale}">' in html
        assert f'href="/{locale}/faq"' in html
        assert 'href="/lab-grown-diamond" lang="zh-Hant"' in html  # switcher back to Chinese
        assert f'src="/i18n/{locale}.js?v=' in html
        script = client.get(f"/i18n/{locale}.js")
        assert script.text.startswith("window.IMPRINT_I18N=")


def test_redirects_keep_the_language():
    response = TestClient(app).get("/en/price.html", follow_redirects=False)
    assert response.status_code in {301, 404}


def test_options_keep_their_chinese_value():
    out, _ = translate_html("<select><option>其他</option></select>", {"其他": "Other"})
    assert '<option value="其他"> Other </option>' in out


def test_textarea_content_is_never_translated():
    html = '<textarea placeholder="首頁">首頁</textarea>'
    out, _ = translate_html(html, {"首頁": "Home"})
    assert out == '<textarea placeholder="Home">首頁</textarea>'


def test_script_containing_svg_markup_is_left_alone():
    script = '<script>el.innerHTML="<svg></svg>";var a="首頁";</script>'
    out, missing = translate_html(script + "<p>首頁</p>", {"首頁": "Home"})
    assert out.startswith(script)
    assert "Home" in out and missing == []


def test_patterns_cover_live_values():
    out, missing = translate_html("<p>共 3 件商品</p>", {"共 {} 件商品": "{} items"})
    assert "3 items" in out and missing == []


def test_translation_sync_is_inert_without_a_key(monkeypatch):
    monkeypatch.delenv("GOOGLE_TRANSLATE_API_KEY", raising=False)

    def fail(*_args, **_kwargs):
        raise AssertionError("must not start")

    monkeypatch.setattr(i18n_store.threading, "Thread", fail)
    i18n_store.request_sync()
    assert i18n_store.saved_entries("en") == {}


def test_sign_in_button_follows_page_language():
    client = TestClient(app)
    english = client.get(
        "/htmx/nav-state", headers={"HX-Current-URL": f"http://testserver/en{ROUTE}"}
    ).text
    assert "Sign In" in english and "會員登入" not in english
    assert "會員登入" in client.get("/htmx/nav-state").text


def test_google_without_key_raises(monkeypatch):
    monkeypatch.delenv("GOOGLE_TRANSLATE_API_KEY", raising=False)
    with pytest.raises(translator_google.TranslationError):
        translator_google.translate_texts(["首頁"], "en")


def test_google_request_keeps_brand_names_and_hides_the_key(monkeypatch):
    seen = {}

    class Reply:
        def raise_for_status(self):
            pass

        def json(self):
            return {"data": {"translations": [{"translatedText": seen["json"]["q"][0]}]}}

    def fake_post(url, **kwargs):
        seen.update(kwargs, url=url)
        return Reply()

    monkeypatch.setenv("GOOGLE_TRANSLATE_API_KEY", "test-key")
    monkeypatch.setattr(translator_google.requests, "post", fake_post)
    assert translator_google.translate_texts(["滿月鑽石 <A&B>"], "ja") == [
        "ファーストラブダイヤモンド <A&B>"
    ]
    assert seen["json"]["q"] == [
        '<span translate="no">ファーストラブダイヤモンド</span> &lt;A&amp;B&gt;'
    ]
    assert seen["json"]["model"] == "nmt"
    assert seen["headers"] == {"X-goog-api-key": "test-key"}
    assert "test-key" not in seen["url"]


def test_nav_css_has_no_damaged_characters():
    css = (settings.site_root / "public" / "css" / "nav.css").read_text(encoding="utf-8")
    assert [c for c in css if ord(c) < 32 and not c.isspace()] == []


def test_no_space_before_punctuation_that_follows_a_link():
    out, _ = translate_html(
        "<p>看<a>報價</a>。</p>", {"看": "See", "報價": "quote", "。": "."}
    )
    assert "quote</a>." in out


def test_short_patterns_do_not_hide_untranslated_text():
    out, missing = translate_html("<p>品項：沒翻過的字</p>", {"品項：{}": "Item: {}"})
    assert "品項：沒翻過的字" in out and missing == ["品項：沒翻過的字"]


def test_database_content_matches_what_pages_display(monkeypatch):
    rows = {
        "faq_items": [{"question": "可以參觀嗎？", "answer": "可以。詳見 /diamond-4c 的說明。"}],
        "testimonials": [{"text": "很感動的紀念。", "role": "寵物鑽石・高雄"}],
        "journal_posts": [{"title": "新消息", "body": "第一段內容。\n\n第二段內容。"}],
    }

    class Cursor:
        def execute(self, query):
            self.rows = next(
                (v for k, v in rows.items() if f"from {k} " in query + " "), []
            )

        def fetchall(self):
            return self.rows

    texts = i18n_store.collect_public_texts(Cursor())
    saved = {key: "T" for key, parts in texts.items() if parts == [key]}
    saved.update(i18n_store._assemble(
        {k: v for k, v in texts.items() if v != [k]}, dict(saved)
    ))
    assert saved["第一段內容。 第二段內容。"] == "T\nT"  # paragraphs survive

    catalog = {**load_catalog("en").exact, **saved}
    page = (
        "<p>「很感動的紀念。」</p><div>"
        + format_faq_answer_html(rows["faq_items"][0]["answer"])
        + "</div><div>第一段內容。\n\n第二段內容。</div><h2>可以參觀嗎？</h2>"
    )
    _out, missing = translate_html(page, catalog)
    assert missing == []

