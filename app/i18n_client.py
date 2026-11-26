"""Browser side of the translation layer: the catalog served as a script."""

from __future__ import annotations

import hashlib
import json
from functools import lru_cache

from app.i18n import Catalog, load_catalog, page_routes

_CLIENT_VERSION = 8


@lru_cache(maxsize=16)
def _script(locale: str, catalog: Catalog) -> tuple[str, str]:
    data = {"lang": locale, "routes": page_routes(), "catalog": catalog.exact}
    body = "window.IMPRINT_I18N=" + json.dumps(data, ensure_ascii=False) + ";"
    return body, hashlib.sha256(body.encode("utf-8")).hexdigest()[:12]


def catalog_script(locale: str) -> str:
    return _script(locale, load_catalog(locale))[0]


def head_scripts(locale: str) -> str:
    """Loaded first and synchronously so JavaScript-built text is caught."""
    digest = _script(locale, load_catalog(locale))[1]
    return (
        f'<script src="/i18n/{locale}.js?v={digest}"></script>'
        f'<script src="/static/js/i18n-client.js?v={_CLIENT_VERSION}"></script>'
    )
