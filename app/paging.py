"""Shared list pagination: page / page_size → limit / offset + response shape."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Sequence, TypeVar

DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 100
MIN_PAGE = 1

T = TypeVar("T")


@dataclass(frozen=True)
class PageWindow:
    """SQL-ready window for a 1-based page."""

    page: int
    page_size: int
    limit: int
    offset: int


def _as_int(raw: Any, *, default: int) -> int:
    if raw is None or raw is False:
        return default
    if isinstance(raw, bool):
        return default
    try:
        return int(str(raw).strip())
    except (TypeError, ValueError):
        return default


def clamp_page(raw: Any, *, default: int = MIN_PAGE) -> int:
    """1-based page index; invalid / sub-1 values fall back to default (≥1)."""
    page = _as_int(raw, default=default)
    return max(MIN_PAGE, page)


def clamp_page_size(
    raw: Any,
    *,
    default: int = DEFAULT_PAGE_SIZE,
    max_size: int = MAX_PAGE_SIZE,
) -> int:
    """Clamp page_size into [1, max_size]; invalid / <1 → default."""
    size = _as_int(raw, default=default)
    if size < 1:
        size = default
    return min(max(1, size), max(1, max_size))


# Back-compat aliases used by earlier drafts / call sites.
parse_page = clamp_page
parse_page_size = clamp_page_size


def parse_paging(
    page: Any = None,
    page_size: Any = None,
    *,
    default_page_size: int = DEFAULT_PAGE_SIZE,
    max_page_size: int = MAX_PAGE_SIZE,
) -> tuple[int, int, int, int]:
    """Return (page, page_size, limit, offset) for SQL LIMIT/OFFSET."""
    resolved_page = clamp_page(page)
    resolved_size = clamp_page_size(
        page_size, default=default_page_size, max_size=max_page_size
    )
    return (
        resolved_page,
        resolved_size,
        resolved_size,
        (resolved_page - 1) * resolved_size,
    )


def parse_paging_from_mapping(
    params: Mapping[str, Any] | None,
    *,
    page_key: str = "page",
    page_size_key: str = "page_size",
    default_page_size: int = DEFAULT_PAGE_SIZE,
    max_page_size: int = MAX_PAGE_SIZE,
) -> tuple[int, int, int, int]:
    """Read page/page_size from query params; also accepts camelCase pageSize."""
    src = params or {}
    size_raw = src.get(page_size_key)
    if size_raw is None:
        size_raw = src.get("pageSize")
    return parse_paging(
        src.get(page_key),
        size_raw,
        default_page_size=default_page_size,
        max_page_size=max_page_size,
    )


def page_window(
    page: Any = None,
    page_size: Any = None,
    *,
    default_page_size: int = DEFAULT_PAGE_SIZE,
    max_page_size: int = MAX_PAGE_SIZE,
) -> PageWindow:
    """Resolve page + page_size into a PageWindow."""
    p, s, limit, offset = parse_paging(
        page,
        page_size,
        default_page_size=default_page_size,
        max_page_size=max_page_size,
    )
    return PageWindow(page=p, page_size=s, limit=limit, offset=offset)


def page_window_from_params(
    params: Mapping[str, Any] | None,
    *,
    page_key: str = "page",
    page_size_key: str = "page_size",
    default_page_size: int = DEFAULT_PAGE_SIZE,
    max_page_size: int = MAX_PAGE_SIZE,
) -> PageWindow:
    """Read page/page_size from a query-param mapping into a PageWindow."""
    p, s, limit, offset = parse_paging_from_mapping(
        params,
        page_key=page_key,
        page_size_key=page_size_key,
        default_page_size=default_page_size,
        max_page_size=max_page_size,
    )
    return PageWindow(page=p, page_size=s, limit=limit, offset=offset)


def normalize_total(total: Any) -> int:
    """Non-negative int total for response envelopes."""
    value = _as_int(total, default=0)
    return max(0, value)


def sql_count_total(
    cur: Any,
    sql: str,
    params: Sequence[Any] | None = None,
) -> int:
    """Run a COUNT query that returns one numeric column; return non-negative int."""
    cur.execute(sql, list(params or ()))
    row = cur.fetchone()
    if row is None:
        return 0
    if isinstance(row, Mapping):
        return normalize_total(next(iter(row.values()), 0))
    try:
        return normalize_total(row[0])
    except (TypeError, IndexError, KeyError):
        return 0


def page_meta(
    *,
    page: int,
    page_size: int,
    total: Any,
) -> dict[str, int]:
    """Paging fields without items: {page, page_size, pageSize, total}."""
    size = int(page_size)
    return {
        "page": int(page),
        "page_size": size,
        "pageSize": size,
        "total": normalize_total(total),
    }


def page_response(
    items: Sequence[T],
    *,
    page: int,
    page_size: int,
    total: Any,
    items_key: str = "items",
) -> dict[str, Any]:
    """List envelope: {items_key, page, page_size, pageSize, total}."""
    out: dict[str, Any] = {items_key: list(items)}
    out.update(page_meta(page=page, page_size=page_size, total=total))
    return out


def page_response_from_window(
    items: Sequence[T],
    window: PageWindow,
    *,
    total: Any,
    items_key: str = "items",
) -> dict[str, Any]:
    """Build page_response from a PageWindow."""
    return page_response(
        items,
        page=window.page,
        page_size=window.page_size,
        total=total,
        items_key=items_key,
    )
