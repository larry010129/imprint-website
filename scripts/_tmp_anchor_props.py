from pathlib import Path

p = Path("app/cms_pages.py")
text = p.read_text(encoding="utf-8")

old = """DEFAULT_PROPS: dict[str, dict[str, Any]] = {
    \"hero\": {
        \"eyebrow\": \"\",
        \"title\": \"新頁面標題\",
        \"lead\": \"\",
        \"image_url\": \"\",
        \"image_alt\": \"\",
        \"cta_label\": \"了解更多\",
        \"cta_href\": \"/contact.html\",
        \"cta_secondary_label\": \"\",
        \"cta_secondary_href\": \"\",
    },
    \"rich_text\": {\"title\": \"\", \"body\": \"\", \"columns\": 1},
    \"image_text\": {
        \"title\": \"\",
        \"body\": \"\",
        \"image_url\": \"\",
        \"image_alt\": \"\",
        \"layout\": \"stack\",
        \"cta_label\": \"\",
        \"cta_href\": \"\",
    },
    \"cta_band\": {
        \"title\": \"準備好開始了嗎？\",
        \"lead\": \"\",
        \"image_url\": \"\",
        \"image_alt\": \"\",
        \"cta_label\": \"客製試算\",
        \"cta_href\": \"/shop/calculator/\",
        \"cta_secondary_label\": \"聯絡我們\",
        \"cta_secondary_href\": \"/contact.html\",
    },
    \"faq_embed\": {\"mode\": \"teaser\", \"category_id\": \"\", \"limit\": 6},
    \"testimonials_embed\": {\"limit\": 6},
    \"button_row\": {
        \"buttons\": [
            {\"label\": \"客製試算\", \"href\": \"/shop/calculator/\"},
            {\"label\": \"查看價格\", \"href\": \"/price.html\"},
        ]
    },
    \"spacer\": {\"size\": \"md\"},
}"""

new = """DEFAULT_PROPS: dict[str, dict[str, Any]] = {
    \"hero\": {
        \"anchor\": \"end\",
        \"eyebrow\": \"\",
        \"title\": \"新頁面標題\",
        \"lead\": \"\",
        \"image_url\": \"\",
        \"image_alt\": \"\",
        \"cta_label\": \"了解更多\",
        \"cta_href\": \"/contact.html\",
        \"cta_secondary_label\": \"\",
        \"cta_secondary_href\": \"\",
    },
    \"rich_text\": {\"anchor\": \"end\", \"title\": \"\", \"body\": \"\", \"columns\": 1},
    \"image_text\": {
        \"anchor\": \"end\",
        \"title\": \"\",
        \"body\": \"\",
        \"image_url\": \"\",
        \"image_alt\": \"\",
        \"layout\": \"stack\",
        \"cta_label\": \"\",
        \"cta_href\": \"\",
    },
    \"cta_band\": {
        \"anchor\": \"end\",
        \"title\": \"準備好開始了嗎？\",
        \"lead\": \"\",
        \"image_url\": \"\",
        \"image_alt\": \"\",
        \"cta_label\": \"客製試算\",
        \"cta_href\": \"/shop/calculator/\",
        \"cta_secondary_label\": \"聯絡我們\",
        \"cta_secondary_href\": \"/contact.html\",
    },
    \"faq_embed\": {\"anchor\": \"end\", \"mode\": \"teaser\", \"category_id\": \"\", \"limit\": 6},
    \"testimonials_embed\": {\"anchor\": \"end\", \"limit\": 6},
    \"button_row\": {
        \"anchor\": \"end\",
        \"buttons\": [
            {\"label\": \"客製試算\", \"href\": \"/shop/calculator/\"},
            {\"label\": \"查看價格\", \"href\": \"/price.html\"},
        ]
    },
    \"spacer\": {\"anchor\": \"end\", \"size\": \"md\"},
}"""

if old not in text:
    raise SystemExit("DEFAULT_PROPS block not found")
text = text.replace(old, new, 1)

if 'from typing import Any' in text and "\nimport re\n" not in text[:800]:
    text = text.replace("from typing import Any", "import re\nfrom typing import Any", 1)

needle = '    if section_type == "image_text":'
inject = '''    anchor = str(out.get("anchor") or "end").strip().lower()
    if not re.fullmatch(r"[a-z0-9-]{1,64}", anchor or ""):
        anchor = "end"
    out["anchor"] = anchor
    if section_type == "image_text":'''
if 'out["anchor"] = anchor' not in text:
    if needle not in text:
        raise SystemExit("normalize needle missing")
    text = text.replace(needle, inject, 1)

p.write_text(text, encoding="utf-8")
print("ok")
