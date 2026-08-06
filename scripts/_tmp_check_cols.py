"""Temp: inspect product schema columns / try list path."""
from __future__ import annotations

from app.database import get_connection


def main() -> None:
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute(
            """
            select column_name from information_schema.columns
            where table_schema='public' and table_name='product_variants'
            order by ordinal_position
            """
        )
        print("variant cols:", [r["column_name"] for r in cur.fetchall()])
        cur.execute(
            """
            select column_name from information_schema.columns
            where table_schema='public' and table_name='product_categories'
            order by ordinal_position
            """
        )
        print("cat cols:", [r["column_name"] for r in cur.fetchall()])
        cur.execute("select to_regclass('public.admin_plugins') as t")
        print("admin_plugins:", cur.fetchone())

    from app.controllers.admin_controller import _products_with_children
    from app.product_categories import fetch_categories, category_labels
    from app.chain_catalog import chain_catalog_for_admin

    try:
        with get_connection() as conn, conn.cursor() as cur:
            products = _products_with_children(cur)
            categories = fetch_categories(cur)
            labels = category_labels(cur)
        catalog = chain_catalog_for_admin()
        print(
            "list ok",
            len(products),
            "products",
            len(categories),
            "cats",
            len(labels),
            "labels",
            bool(catalog),
        )
    except Exception as exc:
        print("LIST FAILED:", type(exc).__name__, exc)


if __name__ == "__main__":
    main()
