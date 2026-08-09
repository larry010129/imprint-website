"""Spot-check list endpoints expose page/page_size/total and SQL-bounded helpers."""

from __future__ import annotations

import ast
from pathlib import Path

from app.paging import page_window, parse_paging


def test_parse_paging_clamps_page_size():
    page, size, limit, offset = parse_paging(1, 999)
    assert page == 1
    assert size == limit == 100
    assert offset == 0


def test_page_window_matches_parse_paging():
    window = page_window(2, 25)
    page, size, limit, offset = parse_paging(2, 25)
    assert window.page == page
    assert window.page_size == size
    assert window.limit == limit
    assert window.offset == offset == 25


def test_content_fetchers_accept_limit_offset():
    import inspect

    from app import content

    for name in (
        "fetch_published_testimonials",
        "fetch_published_journal_posts",
        "fetch_all_testimonials",
        "fetch_all_journal_posts",
        "fetch_all_banners",
        "fetch_all_page_images",
    ):
        fn = getattr(content, name)
        params = inspect.signature(fn).parameters
        assert "limit" in params, name
        assert "offset" in params, name


def test_catalog_fetch_accepts_limit_offset():
    import inspect

    from app.catalog import count_catalog_rows, fetch_catalog_rows

    params = inspect.signature(fetch_catalog_rows).parameters
    assert "limit" in params and "offset" in params
    assert callable(count_catalog_rows)


def test_soft_slice_gone_from_stories_ssr():
    src = Path("app/controllers/web_controller.py").read_text(encoding="utf-8")
    assert "items[:limit]" not in src
    assert "fetch_published_testimonials(cur, limit=limit" in src or (
        "limit=limit" in src and "fetch_published_testimonials" in src
    )


def test_history_partial_returns_full_list():
    """Guard against missing return after partial=rows branch."""
    path = Path("app/controllers/htmx_member.py")
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.AsyncFunctionDef) and node.name == "history_partial":
            returns = [n for n in ast.walk(node) if isinstance(n, ast.Return)]
            assert len(returns) >= 3, "history_partial must return guest, rows, and full list"
            break
    else:
        raise AssertionError("history_partial not found")
