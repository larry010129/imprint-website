"""HTMX shop calculator wizard — catalog → styles → configure → quote → cart.

Reuses app.catalog + app.pricing.compute_order_pricing (no client pricing math).
ponytail: engraving girdle/band UI, pendant+chain picker, full shop.js
gallery/lightbox — memorial diamond colors use matrix PNGs (shipped).
"""

from __future__ import annotations

import json
from typing import Any
from urllib.parse import quote

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, Response
from psycopg.types.json import Jsonb

from app.auth import get_user_id, is_admin
from app.catalog import (
    build_catalog_product,
    build_catalog_product_lite,
    build_catalog_response,
    count_catalog_rows,
    fetch_catalog_rows,
    fetch_product_row,
    list_catalog_category_slugs,
    load_product_children,
    normalize_catalog_detail,
    resolve_product_id,
)
from app.paging import page_window_from_params
from app.controllers.htmx_common import (
    cart_count,
    form_bool,
    html,
    hx_redirect,
    is_shop_preview,
    templates,
)
from app.controllers.shop_controller import (
    _clamp_pendant_chain_sell_mode,
    _strip_disallowed_engraving,
    _strip_disallowed_fancy_shape,
    _summary,
    _validate_config,
)
from app.orders import apply_girdle_engraving
from app.database import get_connection
from app.image_urls import (
    category_image_url,
    diamond_matrix_image_url,
    memorial_diamond_color_options,
    shop_product_image_url,
    shop_style_thumb_url,
)
from app.memorial_diamonds import list_tombstoned_style_keys, merge_memorial_diamond_catalog
from app.pricing import VALID_FANCY_COLORS, _as_earring_quantity, compute_order_pricing
from app.product_categories import fetch_categories

router = APIRouter(prefix="/shop", tags=["htmx-shop-wizard"])

GOLD_LABELS = {
    "9k": "9K",
    "14k": "14K",
    "18k": "18K",
    "pt950": "Pt950",
    "s925": "S925",
}
CHAIN_LENGTHS_CM = [36, 41, 46, 51, 61, 76, 80]
BRACELET_LENGTHS_CM = [15, 16, 17, 18, 19, 20, 21]


def _product_thumb(product: dict[str, Any]) -> str:
    thumb = product.get("thumbUrl")
    if thumb:
        return str(thumb)
    images = product.get("images") or {}
    for urls in images.values():
        if isinstance(urls, list) and urls:
            return str(urls[0])
    style_key = product.get("styleKey")
    return (
        shop_product_image_url(style_key, "white")
        or shop_style_thumb_url(style_key)
        or ""
    )


def _default_memorial_diamond_type_ref(products: list[dict[str, Any]]) -> str:
    """Shop memorial diamond skips style grid — default white color product."""
    for product in products:
        key = str(product.get("styleKey") or "")
        if key == "diamond-white":
            return str(product.get("id") or key)
        if str(product.get("defaultColor") or "").lower() == "white":
            return str(product.get("id") or key)
    if products:
        first = products[0]
        return str(first.get("id") or first.get("styleKey") or "diamond-white")
    return "diamond-white"


def _type_grid_layout(count: int) -> dict[str, Any]:
    """Mirror retired shop.js applyTypeGridLayout — size classes drive shop.css columns."""
    if count <= 1:
        size, cols = "xl", 1
    elif count <= 3:
        size, cols = "lg", count
    elif count <= 6:
        size, cols = "md", min(3, count)
    elif count <= 12:
        size, cols = "sm", 3
    else:
        size, cols = "xs", None
    return {"type_grid_size": size, "type_grid_cols": cols, "type_grid_count": count}


def _category_meta_map(category_rows: list[dict]) -> dict[str, dict]:
    return {
        row["slug"]: {
            "labelZh": row["label_zh"],
            "labelEn": row.get("label_en"),
            "thumbUrl": row.get("thumbUrl") or category_image_url(row["slug"]),
        }
        for row in category_rows
    }


def _finalize_catalog_meta(
    categories: dict[str, list],
    order: list[str],
    meta: dict[str, dict],
) -> dict[str, Any]:
    diamond_list = categories.get("diamond") or []
    diamond_thumb = _product_thumb(diamond_list[0]) if diamond_list else ""
    meta.setdefault(
        "diamond",
        {
            "labelZh": "紀念鑽石",
            "labelEn": "Memorial diamond",
            "thumbUrl": diamond_thumb or category_image_url("diamond"),
        },
    )
    for slug, info in meta.items():
        if not info.get("thumbUrl"):
            info["thumbUrl"] = category_image_url(slug)
    return {"categories": categories, "categoryOrder": order, "categoryMeta": meta}


def _load_catalog(
    *,
    include_drafts: bool = False,
    detail: str = "lite",
    category: str | None = None,
    limit: int | None = None,
    offset: int | None = None,
) -> dict[str, Any]:
    """Load catalog; optional category + limit/offset. Children only for fetched IDs."""
    cat = (category or "").strip() or None
    # Memorial merge needs every DB overlay; page diamond after merge.
    page_sql = cat != "diamond"
    with get_connection() as conn, conn.cursor() as cur:
        total = count_catalog_rows(cur, category=cat, include_drafts=include_drafts)
        products = fetch_catalog_rows(
            cur,
            category=cat,
            include_drafts=include_drafts,
            limit=limit if page_sql else None,
            offset=offset if page_sql else None,
        )
        variants, images = load_product_children(cur, [row["id"] for row in products])
        category_rows = fetch_categories(cur)
        cat_order = [row["slug"] for row in category_rows]
        cat_meta = _category_meta_map(category_rows)
        diamond_tombstones = (
            list_tombstoned_style_keys(cur) if cat in (None, "diamond") else set()
        )
    catalog = build_catalog_response(
        products,
        variants,
        images,
        category_order=cat_order,
        category_meta=cat_meta,
        detail=detail,
    )
    categories = dict(catalog.get("categories") or {})
    if cat in (None, "diamond"):
        merged = merge_memorial_diamond_catalog(
            categories.get("diamond") or [],
            excluded_style_keys=diamond_tombstones,
        )
        if cat == "diamond" and (limit is not None or offset is not None):
            total = len(merged)
            start = max(0, int(offset or 0))
            end = start + int(limit) if limit is not None else None
            categories["diamond"] = merged[start:end]
        else:
            categories["diamond"] = merged
    order = list(catalog.get("categoryOrder") or [])
    if "diamond" in categories and "diamond" not in order:
        order = ["diamond"] + order
    elif "diamond" in order:
        order = ["diamond"] + [c for c in order if c != "diamond"]
    out = _finalize_catalog_meta(categories, order, dict(catalog.get("categoryMeta") or {}))
    out["total"] = total
    out["page_limit"] = limit
    out["page_offset"] = offset
    return out


def _load_catalog_tiles(*, include_drafts: bool = False) -> dict[str, Any]:
    """Category tiles only — no full product dump; diamond children for memorial default."""
    with get_connection() as conn, conn.cursor() as cur:
        category_rows = fetch_categories(cur)
        nonempty = set(list_catalog_category_slugs(cur, include_drafts=include_drafts))
        diamond_rows = fetch_catalog_rows(
            cur, category="diamond", include_drafts=include_drafts
        )
        variants, images = load_product_children(
            cur, [row["id"] for row in diamond_rows]
        )
        diamond_tombstones = list_tombstoned_style_keys(cur)
    diamond_products = [
        build_catalog_product_lite(
            row,
            variants.get(row["id"], []),
            images.get(row["id"], []),
        )
        for row in diamond_rows
    ]
    categories: dict[str, list] = {
        slug: [] for slug in nonempty if slug != "diamond"
    }
    categories["diamond"] = merge_memorial_diamond_catalog(
        diamond_products,
        excluded_style_keys=diamond_tombstones,
    )
    cat_order = [row["slug"] for row in category_rows]
    order = ["diamond"] + [c for c in cat_order if c != "diamond" and c in categories]
    order.extend(c for c in categories if c not in order)
    return _finalize_catalog_meta(categories, order, _category_meta_map(category_rows))


def _find_product(catalog: dict[str, Any], category: str, type_ref: str) -> dict[str, Any] | None:
    for product in catalog.get("categories", {}).get(category) or []:
        if str(product.get("id")) == type_ref or str(product.get("styleKey")) == type_ref:
            return product
    return None


def _load_full_product(
    product_id: str,
    *,
    include_drafts: bool = False,
    category_meta: dict[str, dict] | None = None,
) -> dict[str, Any] | None:
    with get_connection() as conn, conn.cursor() as cur:
        product = fetch_product_row(cur, product_id, include_drafts=include_drafts)
        if not product:
            return None
        variants, images = load_product_children(cur, [product["id"]])
        ring_meta = (category_meta or {}).get("ring") or {}
        if category_meta is None:
            from app.product_categories import build_category_meta

            ring_meta = build_category_meta(cur).get("ring") or {}
        ring_cat_cfg = ring_meta.get("ringSizeConfig")
        if not isinstance(ring_cat_cfg, dict):
            ring_cat_cfg = None
        return build_catalog_product(
            product,
            variants.get(product["id"], []),
            images.get(product["id"], []),
            category_ring_size_config=ring_cat_cfg,
        )


def _resolve_configure_product(
    catalog: dict[str, Any],
    category: str,
    type_ref: str,
    *,
    include_drafts: bool,
) -> dict[str, Any] | None:
    product = _find_product(catalog, category, type_ref)
    if product:
        if category == "diamond" or product.get("weights") is not None:
            return product
        full = _load_full_product(
            str(product["id"]),
            include_drafts=include_drafts,
            category_meta=catalog.get("categoryMeta"),
        )
        return full or product
    # Not in lite page — resolve UUID / style key directly (no category dump).
    if category == "diamond":
        return None
    with get_connection() as conn, conn.cursor() as cur:
        product_id = resolve_product_id(
            cur,
            category=category,
            type_ref=type_ref,
            require_published=not include_drafts,
        )
        if not product_id:
            return None
        product = fetch_product_row(cur, product_id, include_drafts=include_drafts)
        if not product:
            return None
        variants, images = load_product_children(cur, [product["id"]])
        ring_meta = (catalog.get("categoryMeta") or {}).get("ring") or {}
        ring_cat_cfg = ring_meta.get("ringSizeConfig")
        if not isinstance(ring_cat_cfg, dict):
            ring_cat_cfg = None
        return build_catalog_product(
            product,
            variants.get(product["id"], []),
            images.get(product["id"], []),
            category_ring_size_config=ring_cat_cfg,
        )


def _config_from_form(form: Any) -> dict[str, Any]:
    category = str(form.get("category") or "").strip()
    type_ref = str(form.get("type") or "").strip()
    carat = str(form.get("carat") or "").strip()
    gold = str(form.get("gold") or "").strip() or None
    length_raw = str(form.get("lengthCm") or "").strip()
    length_cm: float | None = None
    if length_raw:
        try:
            length_cm = float(length_raw)
        except ValueError:
            length_cm = None
    name = str(form.get("summaryZh") or "").strip()
    diamond_shape = str(form.get("diamondShape") or "round").strip() or "round"
    diamond_kind = str(form.get("diamondKind") or "white").strip() or "white"
    fancy_color = str(form.get("fancyColor") or "").strip() or None
    # Memorial color select posts diamondColor; map to kind/fancy for pricing.
    diamond_color = str(form.get("diamondColor") or "").strip().lower()
    if diamond_color in VALID_FANCY_COLORS:
        diamond_kind = "fancy"
        fancy_color = diamond_color
    elif diamond_color == "white":
        diamond_kind = "white"
        fancy_color = None
    cfg: dict[str, Any] = {
        "category": category,
        "type": type_ref,
        "carat": carat,
        "gold": gold,
        "lengthCm": length_cm,
        "diamondKind": diamond_kind,
        "diamondShape": diamond_shape,
        "fancyColor": fancy_color,
        "includeChain": form_bool(form.get("includeChain")),
        "summaryZh": name,
        # ponytail: chainProductId / chainGold / chainLength still deferred on HTMX
    }
    girdle = form.get("engravingGirdle")
    if girdle is None:
        girdle = form.get("engraving_girdle")
    if girdle is not None:
        cfg["engravingGirdle"] = str(girdle)
        apply_girdle_engraving(cfg)
    if category == "earring":
        cfg["quantity"] = _as_earring_quantity(form.get("quantity"))
    return cfg


def _with_badge_oob(resp: HTMLResponse, request: Request, user_id: str | None) -> HTMLResponse:
    badge = templates.get_template("partials/htmx/cart_badge.html").render(
        {"request": request, "count": cart_count(user_id), "oob": True}
    )
    body = resp.body.decode(resp.charset) + badge
    resp.body = body.encode(resp.charset)
    resp.headers["content-length"] = str(len(resp.body))
    return resp


def _preview_ctx(request: Request) -> dict[str, Any]:
    preview = is_shop_preview(request)
    return {"preview": preview, "preview_qs": "preview=1" if preview else ""}


def _catalog_for_request(
    request: Request,
    *,
    detail: str = "lite",
    category: str | None = None,
    limit: int | None = None,
    offset: int | None = None,
) -> dict[str, Any]:
    include_drafts = _include_drafts_for_request(request)
    return _load_catalog(
        include_drafts=include_drafts,
        detail=normalize_catalog_detail(detail),
        category=category,
        limit=limit,
        offset=offset,
    )


def _include_drafts_for_request(request: Request) -> bool:
    preview = is_shop_preview(request)
    return bool(preview and is_admin(get_user_id(request)))


def _step_ctx(
    request: Request,
    *,
    step: str,
    category: str = "",
    category_label: str = "",
    product: dict | None = None,
    **extra: Any,
) -> dict[str, Any]:
    return {
        "step": step,
        "category": category,
        "category_label": category_label,
        "product": product,
        "gold_labels": GOLD_LABELS,
        **_preview_ctx(request),
        **extra,
    }


@router.get("/step/catalog", response_class=HTMLResponse)
async def shop_step_catalog(request: Request) -> HTMLResponse:
    include_drafts = _include_drafts_for_request(request)
    catalog = _load_catalog_tiles(include_drafts=include_drafts)
    tiles = []
    for slug in catalog["categoryOrder"]:
        products = catalog["categories"].get(slug) or []
        if not products and slug != "diamond":
            # Seeded empty = category has published rows; still show tile.
            if slug not in catalog["categories"]:
                continue
        meta = catalog["categoryMeta"].get(slug) or {}
        thumb = meta.get("thumbUrl") or (
            _product_thumb(products[0]) if products else category_image_url(slug)
        )
        tiles.append(
            {
                "slug": slug,
                "label": meta.get("labelZh") or slug,
                "thumb": thumb or "",
                "memorial_type": (
                    _default_memorial_diamond_type_ref(products)
                    if slug == "diamond"
                    else None
                ),
            }
        )
    return html(request, "shop_catalog.html", _step_ctx(request, step="catalog", tiles=tiles))


@router.get("/step/styles", response_class=HTMLResponse)
async def shop_step_styles(request: Request) -> HTMLResponse:
    category = str(request.query_params.get("category") or "").strip()
    if not category:
        return await shop_step_catalog(request)
    window = page_window_from_params(request.query_params)
    catalog = _catalog_for_request(
        request,
        category=category,
        limit=window.limit,
        offset=window.offset,
    )
    if category == "diamond":
        products = catalog["categories"].get("diamond") or []
        type_ref = _default_memorial_diamond_type_ref(products)
        preview = is_shop_preview(request)
        qs = f"category=diamond&type={quote(type_ref)}"
        if preview:
            qs += "&preview=1"
        scope = dict(request.scope)
        scope["query_string"] = qs.encode()
        return await shop_step_configure(Request(scope, request.receive))
    meta = catalog["categoryMeta"].get(category) or {}
    products = []
    for product in catalog["categories"].get(category) or []:
        products.append({**product, "thumb": _product_thumb(product)})
    total = int(catalog.get("total") or len(products))
    loaded = window.offset + len(products)
    has_more = loaded < total
    next_page_size = min(window.page_size + window.page_size, 100)
    preview = is_shop_preview(request)
    more_qs = f"category={quote(category)}&page=1&page_size={next_page_size}"
    if preview:
        more_qs += "&preview=1"
    return html(
        request,
        "shop_styles.html",
        _step_ctx(
            request,
            step="styles",
            category=category,
            category_label=meta.get("labelZh") or category,
            products=products,
            page=window.page,
            page_size=window.page_size,
            total=total,
            has_more=has_more,
            more_qs=more_qs,
            **_type_grid_layout(len(products)),
        ),
    )


@router.get("/step/configure", response_class=HTMLResponse)
async def shop_step_configure(request: Request) -> HTMLResponse:
    category = str(request.query_params.get("category") or "").strip()
    type_ref = str(request.query_params.get("type") or "").strip()
    if not category:
        return await shop_step_catalog(request)
    if not type_ref:
        return await shop_step_styles(request)
    # Diamond: need merged memorial list. Jewelry: resolve by id (no full dump).
    include_drafts = _include_drafts_for_request(request)
    if category == "diamond":
        catalog = _catalog_for_request(request, detail="lite", category="diamond")
    else:
        catalog = {
            "categories": {category: []},
            "categoryOrder": [category],
            "categoryMeta": {},
        }
        with get_connection() as conn, conn.cursor() as cur:
            from app.product_categories import build_category_meta

            catalog["categoryMeta"] = build_category_meta(cur)
    product = _resolve_configure_product(
        catalog, category, type_ref, include_drafts=include_drafts
    )
    if not product:
        window = page_window_from_params(request.query_params)
        styles = _catalog_for_request(
            request,
            category=category,
            limit=window.limit,
            offset=window.offset,
        )
        products = [
            {**p, "thumb": _product_thumb(p)}
            for p in (styles["categories"].get(category) or [])
        ]
        return html(
            request,
            "shop_styles.html",
            _step_ctx(
                request,
                step="styles",
                category=category,
                category_label=(styles["categoryMeta"].get(category) or {}).get("labelZh") or category,
                products=products,
                error="找不到此款式，請重新選擇。",
                page=window.page,
                page_size=window.page_size,
                total=int(styles.get("total") or len(products)),
                has_more=False,
                more_qs="",
                **_type_grid_layout(len(products)),
            ),
            404,
        )
    meta = catalog["categoryMeta"].get(category) or {}
    golds = list(product.get("golds") or [])
    # Admin/catalog carats only (already sorted smallest-first in build_catalog_product).
    carats = [str(c) for c in (product.get("carats") or []) if c is not None and str(c).strip()]
    lengths = []
    if category == "chain":
        lengths = CHAIN_LENGTHS_CM
    elif category == "bracelet":
        lengths = BRACELET_LENGTHS_CM
    defaults = {
        # Default = first/smallest admin carat — never hard-coded 0.3.
        "carat": carats[0] if carats else "",
        "gold": golds[0] if golds else "",
        "lengthCm": 46 if category == "chain" else (18 if category == "bracelet" else ""),
        "diamondKind": "white",
        "diamondColor": "white",
        "quantity": 1,
    }
    diamond_colors = memorial_diamond_color_options() if category == "diamond" else []
    thumb = _product_thumb(product)
    if category == "diamond":
        thumb = diamond_matrix_image_url("round", "white") or thumb
    preview = is_shop_preview(request)
    require_published = category != "diamond" and not (
        preview and is_admin(get_user_id(request))
    )
    pricing = None
    if defaults["carat"] and (category == "diamond" or defaults["gold"]):
        cfg = {
            "category": category,
            "type": str(product["id"]),
            "carat": defaults["carat"],
            "gold": defaults["gold"] or None,
            "lengthCm": defaults["lengthCm"] or None,
            "diamondKind": "white",
            "diamondShape": "round",
            "summaryZh": product.get("nameZh") or "",
        }
        if category == "earring":
            cfg["quantity"] = defaults["quantity"]
        with get_connection() as conn, conn.cursor() as cur:
            pricing = compute_order_pricing(cur, cfg, require_published=require_published)
    return html(
        request,
        "shop_configure.html",
        _step_ctx(
            request,
            step="product",
            category=category,
            category_label=meta.get("labelZh") or category,
            product={**product, "thumb": thumb},
            golds=golds,
            carats=carats,
            lengths=lengths,
            defaults=defaults,
            diamond_colors=diamond_colors,
            pricing=pricing,
            quote_error=None,
            cart_msg=None,
            cart_ok=False,
        ),
    )


@router.post("/quote", response_class=HTMLResponse)
async def shop_quote_partial(request: Request) -> HTMLResponse:
    form = await request.form()
    config = _config_from_form(form)
    err = _validate_config(config)
    if err:
        return html(request, "shop_quote.html", {"pricing": None, "error": err}, 400)
    preview = is_shop_preview(request, form)
    require_published = config.get("category") != "diamond" and not (
        preview and is_admin(get_user_id(request))
    )
    with get_connection() as conn, conn.cursor() as cur:
        if config.get("category") != "diamond":
            chain_err = _clamp_pendant_chain_sell_mode(cur, config)
            if chain_err:
                return html(request, "shop_quote.html", {"pricing": None, "error": chain_err}, 400)
            _strip_disallowed_engraving(cur, config)
            _strip_disallowed_fancy_shape(cur, config)
        pricing = compute_order_pricing(cur, config, require_published=require_published)
    if not pricing.get("ready"):
        return html(
            request,
            "shop_quote.html",
            {"pricing": None, "error": pricing.get("error") or "無法計算價格，請確認選項"},
            400,
        )
    return html(request, "shop_quote.html", {"pricing": pricing, "error": None})


@router.post("/cart", response_class=HTMLResponse)
async def shop_cart_add(request: Request) -> Response:
    form = await request.form()
    if is_shop_preview(request, form):
        return html(
            request,
            "shop_cart_msg.html",
            {"ok": False, "message": "預覽模式無法加入購物車，請從正式訂製頁操作。"},
            403,
        )
    user_id = get_user_id(request)
    if not user_id:
        next_url = quote("/shop/calculator/", safe="")
        return hx_redirect(f"/login?next={next_url}")
    config = _config_from_form(form)
    err = _validate_config(config)
    if err:
        return html(request, "shop_cart_msg.html", {"ok": False, "message": err}, 400)

    with get_connection() as conn, conn.cursor() as cur:
        if config.get("category") != "diamond":
            chain_err = _clamp_pendant_chain_sell_mode(cur, config)
            if chain_err:
                return html(request, "shop_cart_msg.html", {"ok": False, "message": chain_err}, 400)
            _strip_disallowed_engraving(cur, config)
            _strip_disallowed_fancy_shape(cur, config)
        require_published = config.get("category") != "diamond"
        pricing = compute_order_pricing(cur, config, require_published=require_published)
        if not pricing.get("ready"):
            return html(
                request,
                "shop_cart_msg.html",
                {"ok": False, "message": "無法計算價格，請重新整理後再試"},
                400,
            )
        config["clientPricing"] = pricing
        summary = _summary(config)
        config_json = json.loads(json.dumps(config, default=str))
        cur.execute(
            """
            insert into cart_items (user_id, category, style_type, config_json, summary_zh, total_price)
            values (%s, %s, %s, %s, %s, %s)
            returning id
            """,
            (
                user_id,
                config["category"],
                config["type"],
                Jsonb(config_json),
                summary,
                pricing.get("total"),
            ),
        )
        cur.fetchone()
    resp = html(
        request,
        "shop_cart_msg.html",
        {"ok": True, "message": "已加入購物車", "total": pricing.get("total")},
    )
    return _with_badge_oob(resp, request, user_id)
