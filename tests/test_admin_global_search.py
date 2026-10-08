"""Top-bar admin search: the server-side product filter must also find a product by its ID."""

from __future__ import annotations

from app.controllers.admin_controller import _admin_product_filters


def test_product_filter_without_search_has_no_where():
    assert _admin_product_filters() == ("", [])
    assert _admin_product_filters(search="   ") == ("", [])


def test_product_filter_matches_names_custom_id_and_the_product_id():
    where, params = _admin_product_filters(search="3f1c9e0a-7b2d")
    for column in ("name_zh", "name_en", "custom_id", "id::text", "replace(id::text, '-', '')"):
        assert column in where
    assert where.count("%s") == len(params) == 5
    # the long ID is found with or without its dashes (and ignoring spaces)
    assert params[:4] == ["%3f1c9e0a-7b2d%"] * 4
    assert params[4] == "%3f1c9e0a7b2d%"


def test_product_filter_ignores_dashes_and_spaces_in_the_compact_form():
    _, params = _admin_product_filters(search="3f1c 9e0a-7b2d")
    assert params[4] == "%3f1c9e0a7b2d%"


def test_category_and_search_combine():
    where, params = _admin_product_filters(category="ring", search="RG-001")
    assert where.startswith(" where category = %s and (")
    assert params[0] == "ring" and params[1] == "%RG-001%"
    assert where.count("%s") == len(params) == 6
