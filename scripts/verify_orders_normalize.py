"""Post-migration sanity check for normalized orders schema."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv

load_dotenv(ROOT / ".env")

from app.database import get_connection  # noqa: E402
from app.orders import attach_order_relations, hydrate_order  # noqa: E402

LEGACY_ORDER_COLS = {
    "customer_name",
    "customer_phone",
    "gold_purity",
    "category",
    "carat",
    "config_json",
    "pricing_json",
    "fulfillment_method",
}


def main() -> int:
    failures: list[str] = []
    print("=== orders normalize verification ===\n")

    with get_connection() as conn, conn.cursor() as cur:
        cur.execute(
            """
            select column_name
            from information_schema.columns
            where table_schema = 'public' and table_name = 'orders'
            order by ordinal_position
            """
        )
        order_cols = {r["column_name"] for r in cur.fetchall()}
        print("orders columns:", ", ".join(sorted(order_cols)))

        leaked = LEGACY_ORDER_COLS & order_cols
        if leaked:
            failures.append(f"orders still has legacy columns: {sorted(leaked)}")
        else:
            print("OK  legacy product/contact columns dropped from orders")

        for table in ("order_contacts", "order_fulfillment", "order_items"):
            cur.execute(
                "select to_regclass(%s) as reg",
                (f"public.{table}",),
            )
            if not cur.fetchone()["reg"]:
                failures.append(f"missing table: {table}")
            else:
                print(f"OK  table exists: {table}")

        cur.execute("select count(*) as c from orders")
        n_orders = int(cur.fetchone()["c"])
        cur.execute("select count(*) as c from order_contacts")
        n_contacts = int(cur.fetchone()["c"])
        cur.execute("select count(*) as c from order_fulfillment")
        n_fulfillment = int(cur.fetchone()["c"])
        cur.execute("select count(*) as c from order_items")
        n_items = int(cur.fetchone()["c"])

        print(f"\ncounts: orders={n_orders} contacts={n_contacts} fulfillment={n_fulfillment} items={n_items}")

        if n_orders and n_contacts != n_orders:
            failures.append(f"order_contacts ({n_contacts}) != orders ({n_orders})")
        elif n_orders:
            print("OK  order_contacts count matches orders")

        if n_orders and n_fulfillment != n_orders:
            failures.append(f"order_fulfillment ({n_fulfillment}) != orders ({n_orders})")
        elif n_orders:
            print("OK  order_fulfillment count matches orders")

        if n_orders and n_items != n_orders:
            failures.append(f"order_items ({n_items}) != orders ({n_orders})")
        elif n_orders:
            print("OK  order_items count matches orders")

        cur.execute(
            """
            select o.id, o.order_number, oc.customer_phone
            from orders o
            join order_contacts oc on oc.order_id = o.id
            order by o.created_at desc
            limit 1
            """
        )
        sample = cur.fetchone()
        if sample:
            cur.execute("select * from orders where id = %s", (sample["id"],))
            order = cur.fetchone()
            attach_order_relations(cur, [order])
            hydrate_order(order)
            needed = ("customer_name", "customer_phone", "config_json")
            missing = [k for k in needed if not order.get(k) and order.get(k) != ""]
            if missing:
                failures.append(f"hydrate missing fields on sample order: {missing}")
            else:
                print(
                    "OK  hydrate sample order",
                    sample["order_number"],
                    "→",
                    order.get("customer_name"),
                    order.get("gold_purity") or "(no gold in config)",
                )
            print("\nsample track-order lookup:")
            print(
                json.dumps(
                    {
                        "orderNumber": sample["order_number"],
                        "phone": sample["customer_phone"],
                    },
                    ensure_ascii=False,
                )
            )
        else:
            print("\n(no orders yet — skip hydrate / track-order sample)")

    print()
    if failures:
        print("FAILED:")
        for f in failures:
            print(" -", f)
        return 1

    print("All checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
