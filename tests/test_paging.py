"""Unit tests for app.paging helpers."""

from __future__ import annotations

from app.paging import (
    DEFAULT_PAGE_SIZE,
    MAX_PAGE_SIZE,
    page_meta,
    page_response,
    page_response_from_window,
    page_window,
    page_window_from_params,
    parse_page,
    parse_page_size,
)


def test_parse_page_bounds_and_bad_input():
    assert parse_page(None) == 1
    assert parse_page(0) == 1
    assert parse_page(-3) == 1
    assert parse_page("2") == 2
    assert parse_page("nope") == 1
    assert parse_page(True) == 1


def test_parse_page_size_default_and_max():
    assert parse_page_size(None) == DEFAULT_PAGE_SIZE
    assert parse_page_size(0) == DEFAULT_PAGE_SIZE
    assert parse_page_size(999) == MAX_PAGE_SIZE
    assert parse_page_size("10") == 10
    assert parse_page_size("x", default=5) == 5


def test_page_window_offset_math():
    window = page_window(3, 10)
    assert window.page == 3
    assert window.page_size == 10
    assert window.limit == 10
    assert window.offset == 20
    first = page_window(1, None)
    assert first.page == 1
    assert first.page_size == DEFAULT_PAGE_SIZE
    assert first.offset == 0


def test_page_window_from_params():
    window = page_window_from_params({"page": "2", "page_size": "15"})
    assert window.page == 2
    assert window.page_size == 15
    assert window.offset == 15


def test_page_response_shape():
    out = page_response(["a"], page=1, page_size=20, total=1)
    assert out == {
        "items": ["a"],
        "page": 1,
        "page_size": 20,
        "pageSize": 20,
        "total": 1,
    }
    meta = page_meta(page=2, page_size=10, total=-5)
    assert meta == {"page": 2, "page_size": 10, "pageSize": 10, "total": 0}
    window = page_window(1, 5)
    assert page_response_from_window(["x"], window, total=9)["total"] == 9
