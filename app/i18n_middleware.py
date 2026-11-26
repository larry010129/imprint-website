"""Serve /en, /ja and /ko by reusing the Chinese routes and translating the result."""

from __future__ import annotations

from fastapi import FastAPI, Request
from starlette.concurrency import run_in_threadpool
from starlette.responses import RedirectResponse, Response

from app import i18n_store
from app.i18n import (
    LOCALES,
    is_localizable,
    locale_for_url,
    localize_html,
    localized_url,
    translate_for_locale,
)
from app.i18n_client import catalog_script

# CMS editing and previews must stay on the Chinese pages.
_EDIT_PARAMS = ("cms_edit", "preview", "inline")
_ADMIN_WRITE_PREFIXES = ("/api/admin/", "/api/cms/")
_READ_METHODS = frozenset({"GET", "HEAD"})


def _split_locale(path: str) -> tuple[str | None, str]:
    first, _sep, rest = path.lstrip("/").partition("/")
    if first in LOCALES and is_localizable(f"/{rest}"):
        return first, f"/{rest}"
    return None, path


async def _rewrite(response: Response, transform) -> Response:
    """Read a streamed response, transform its text, keep status and headers."""
    chunks = [chunk async for chunk in response.body_iterator]
    text = b"".join(chunks).decode("utf-8")
    body = (await run_in_threadpool(transform, text)).encode("utf-8")
    result = Response(content=body, status_code=response.status_code)
    # raw_headers keeps repeated headers such as multiple Set-Cookie.
    result.raw_headers = [
        (k, v) for k, v in response.raw_headers if k.lower() != b"content-length"
    ] + [(b"content-length", str(len(body)).encode())]
    return result


def register_i18n_middleware(app: FastAPI) -> None:
    """Call before GZipMiddleware is added, so bodies arrive uncompressed."""

    @app.middleware("http")
    async def i18n_layer(request: Request, call_next):
        path = request.scope["path"]

        if request.method in _READ_METHODS and path.startswith("/i18n/"):
            language = path.removeprefix("/i18n/").removesuffix(".js")
            if language in LOCALES:
                script = await run_in_threadpool(catalog_script, language)
                return Response(
                    script,
                    media_type="application/javascript; charset=utf-8",
                    headers={"Cache-Control": "public, max-age=300"},
                )

        locale, zh_path = _split_locale(path)
        if locale:
            if any(name in request.query_params for name in _EDIT_PARAMS):
                query = request.url.query
                return RedirectResponse(f"{zh_path}?{query}", status_code=302)
            request.scope["path"] = zh_path
            request.scope["raw_path"] = zh_path.encode("utf-8")
            request.state.locale = locale
            i18n_store.request_sync(min_interval=600)

        response = await call_next(request)

        if request.method not in _READ_METHODS and path.startswith(_ADMIN_WRITE_PREFIXES):
            if response.status_code < 400:
                i18n_store.request_sync()  # translate what was just saved
            return response

        fragment_locale = None
        if path.startswith("/htmx/"):
            fragment_locale = locale_for_url(request.headers.get("HX-Current-URL"))
        active = locale or fragment_locale
        if not active:
            return response

        for header in ("location", "hx-redirect"):
            target = response.headers.get(header)
            if target and target.startswith("/"):
                response.headers[header] = localized_url(target, active)

        is_html = response.headers.get("content-type", "").startswith("text/html")
        if not is_html or request.method == "HEAD" or response.status_code in {204, 304}:
            return response
        if fragment_locale:
            return await _rewrite(response, lambda t: translate_for_locale(t, active))
        return await _rewrite(response, lambda t: localize_html(t, active, zh_path))
