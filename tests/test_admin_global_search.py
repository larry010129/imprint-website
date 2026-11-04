"""Top-bar admin search matches each word anywhere, not the whole phrase."""

from __future__ import annotations

from app.controllers.admin_controller import (
    _admin_orders_search_from,
    _admin_product_filters,
    _product_word_params,
)


def test_product_filter_without_search_has_no_where():
    assert _admin_product_filters() == ("", [])
    assert _admin_product_filters(search="   ") == ("", [])


def test_product_filter_matches_names_descriptions_category_and_id():
    where, params = _admin_product_filters(search="3f1c9e0a-7b2d")
    for column in (
        "name_zh",
        "name_en",
        "description_zh",
        "custom_id",
        "style_key",
        "id::text",
        "replace(id::text, '-', '')",
        "product_variants",
        "戒指",
    ):
        assert column in where
    assert where.count("%s") == len(params) == len(_product_word_params("x"))
    assert params[0] == "%3f1c9e0a-7b2d%"
    assert "%3f1c9e0a7b2d%" in params


def test_product_filter_requires_every_word():
    where, params = _admin_product_filters(search="黃金 18k")
    assert where.count("product_variants") == 2
    assert "%黃金%" in params
    assert "%18k%" in params
    assert "%黃金 18k%" not in params
    assert where.count("%s") == len(params) == len(_product_word_params("x")) * 2


def test_product_filter_ignores_dashes_inside_each_word():
    _, params = _admin_product_filters(search="3f1c 9e0a-7b2d")
    assert "%3f1c%" in params
    assert "%9e0a7b2d%" in params


def test_category_and_search_combine():
    where, params = _admin_product_filters(category="ring", search="RG-001")
    assert where.startswith(" where category = %s and (")
    assert params[0] == "ring" and params[1] == "%RG-001%"
    assert where.count("%s") == len(params) == 1 + len(_product_word_params("x"))


def test_order_search_requires_every_word_across_fields():
    sql, params = _admin_orders_search_from("王 18k")
    assert sql.count(" and ") == 1
    assert "o.order_number ilike" in sql
    assert "oc.customer_email" in sql
    assert "oful.order_note" in sql
    assert "config_json::text" not in sql
    assert params.count("%王%") == 12
    assert params.count("%18k%") == 12
    assert "%王 18k%" not in params
