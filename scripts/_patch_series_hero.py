from pathlib import Path

ROOT = Path(r"C:\Users\user\Documents\Diamond web\imprint-website")

SLOTS = ROOT / "app" / "page_image_slots.py"
CONTENT = ROOT / "app" / "content.py"

old_sig = '''_SIGNATURE_DEFAULT_STEM = "imprint-diamond-wedding-couple-ring"


def _is_signature_default_asset(url: str, webp: str) -> bool:
    if _is_remote_asset(url) or _is_remote_asset(webp):
        return False
    stem = _hero_stem(webp or url)
    if not (url or webp):
        return True
    return stem == _SIGNATURE_DEFAULT_STEM


def _series_signature_admin_urls(url: str, webp: str) -> tuple[str, str]:
    """Landing 真我鑽石 card: use 首頁 slot, else the series-page 主視覺."""
    if not _is_signature_default_asset(url, webp):
        return url, webp or url
    try:
        from app.content import (
            effective_page_image_url,
            effective_page_image_webp,
            fetch_page_image,
        )
        from app.database import get_connection

        with get_connection() as conn, conn.cursor() as cur:
            row = fetch_page_image(cur, "/series/signature/", "hero")
        if not row:
            return url, webp
        hero = effective_page_image_url(row)
        hero_webp = effective_page_image_webp(row)
        if hero and not _is_signature_default_asset(hero, hero_webp):
            return hero, hero_webp or hero
    except Exception:
        pass
    return url, webp
'''

new_sig = '''def _series_key_from_home_slot(slot_key: str) -> str | None:
    raw = str(slot_key or "")
    if not raw.startswith("series-"):
        return None
    key = raw[len("series-") :]
    return key if key in _SERIES else None


def paired_series_slot(page_key: str, slot_key: str) -> tuple[str, str] | None:
    """Home series-* card <-> series page 主視覺."""
    home_key = _series_key_from_home_slot(slot_key)
    if page_key == "/" and home_key:
        return f"/series/{home_key}/", "hero"
    if str(slot_key or "") == "hero":
        for key in _SERIES:
            if page_key == f"/series/{key}/":
                return "/", f"series-{key}"
    return None


def sync_paired_series_image(cur, page_key: str, slot_key: str, image_url: str, image_webp: str | None) -> None:
    """Copy a 主視覺/home-card upload onto its twin so the two cannot drift."""
    pair = paired_series_slot(page_key, slot_key)
    if not pair:
        return
    twin_page, twin_slot = pair
    cur.execute(
        """
        update page_images
        set image_url = %s, image_webp = %s, updated_at = now()
        where page_key = %s and slot_key = %s
        """,
        (image_url, image_webp, twin_page, twin_slot),
    )


def _is_series_default_asset(series_key: str, url: str, webp: str) -> bool:
    if _is_remote_asset(url) or _is_remote_asset(webp):
        return False
    if not (url or webp):
        return True
    default_stem = _SERIES[series_key][1]
    return _hero_stem(webp or url) == default_stem


def _home_series_admin_urls(slot_key: str, url: str, webp: str) -> tuple[str, str]:
    """Homepage series card: series 主視覺 wins over a leftover home-slot file."""
    series_key = _series_key_from_home_slot(slot_key)
    if not series_key:
        return url, webp
    try:
        from app.content import (
            effective_page_image_url,
            effective_page_image_webp,
            fetch_page_image,
        )
        from app.database import get_connection
        from app.image_urls import with_cache_buster

        with get_connection() as conn, conn.cursor() as cur:
            row = fetch_page_image(cur, f"/series/{series_key}/", "hero")
        if not row:
            return url, webp
        hero = effective_page_image_url(row)
        hero_webp = effective_page_image_webp(row)
        if hero and not _is_series_default_asset(series_key, hero, hero_webp):
            stamp = row.get("updated_at")
            return (
                with_cache_buster(hero, stamp),
                with_cache_buster(hero_webp or hero, stamp),
            )
    except Exception:
        pass
    return url, webp
'''

text = SLOTS.read_text(encoding="utf-8")
if old_sig not in text:
    raise SystemExit("signature block not found")
text = text.replace(old_sig, new_sig, 1)
old_apply = '''            if spec.slot_key == "series-signature":
                url, webp = _series_signature_admin_urls(url, webp)
'''
new_apply = '''            if _series_key_from_home_slot(spec.slot_key):
                url, webp = _home_series_admin_urls(spec.slot_key, url, webp)
'''
if old_apply not in text:
    raise SystemExit("apply call not found")
text = text.replace(old_apply, new_apply, 1)
old_src = '''                    ""
                    if match.group().lower().startswith("<source") and not webp
                    else _replace_tag_url(match.group(), url, webp)
'''
new_src = '''                    ""
                    if match.group().lower().startswith("<source")
                    and (not webp or not _looks_like_srcset(webp))
                    else _replace_tag_url(match.group(), url, webp)
'''
if old_src not in text:
    raise SystemExit("source-strip block not found")
text = text.replace(old_src, new_src, 1)
SLOTS.write_text(text, encoding="utf-8")
print("patched", SLOTS)

ct = CONTENT.read_text(encoding="utf-8")
old_reset_end = '''    row = cur.fetchone()
    delete_page_image_urls_if_unreferenced(cur, gc)
    return row


def restore_page_image_row(cur, existing: dict) -> tuple[dict | None, str | None]:
'''
new_reset_end = '''    row = cur.fetchone()
    delete_page_image_urls_if_unreferenced(cur, gc)
    from app.page_image_slots import sync_paired_series_image

    sync_paired_series_image(cur, page_key, slot_key, default_url, default_webp)
    return row


def restore_page_image_row(cur, existing: dict) -> tuple[dict | None, str | None]:
'''
if old_reset_end not in ct:
    raise SystemExit("reset tail not found")
ct = ct.replace(old_reset_end, new_reset_end, 1)
old_stack_end = '''    delete_page_image_urls_if_unreferenced(cur, gc)
    return row


def serialize_page_image(row: dict) -> dict:
'''
new_stack_end = '''    delete_page_image_urls_if_unreferenced(cur, gc)
    from app.page_image_slots import sync_paired_series_image

    sync_paired_series_image(cur, page_key, slot_key, url, webp)
    return row


def serialize_page_image(row: dict) -> dict:
'''
if old_stack_end not in ct:
    raise SystemExit("replace-stack tail not found")
ct = ct.replace(old_stack_end, new_stack_end, 1)
CONTENT.write_text(ct, encoding="utf-8")
print("patched", CONTENT)
