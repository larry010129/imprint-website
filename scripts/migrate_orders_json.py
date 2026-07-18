#!/usr/bin/env python3
"""Apply orders json snapshot migration (20260718100000)."""

from __future__ import annotations

import os
import sys
from pathlib import Path

import psycopg
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

STEPS = [
    """
    alter table orders
      add column if not exists config_json jsonb not null default '{}',
      add column if not exists pricing_json jsonb not null default '{}',
      add column if not exists summary_zh text
    """,
    """
    update orders
    set
      config_json = jsonb_strip_nulls(
        jsonb_build_object(
          'category', category,
          'type', case when product_id is not null then product_id::text else product_type end,
          'gold', gold_purity,
          'carat', carat,
          'color', color,
          'diamondKind', diamond_kind,
          'fancyColor', fancy_color,
          'stoneCount', stone_count,
          'diamondShape', diamond_shape,
          'ringSize', ring_size,
          'engravingBand', engraving_band,
          'engravingGirdle', engraving_girdle,
          'includeChain', include_chain,
          'chainGold', chain_gold,
          'chainColor', chain_color,
          'chainLength', case when coalesce(category, '') <> 'chain' then chain_length_cm else null end,
          'lengthCm', case when category = 'chain' then chain_length_cm else null end,
          'series', series,
          'summaryZh', product_type
        )
      ),
      pricing_json = jsonb_strip_nulls(
        jsonb_build_object(
          'weightGrams', weight_grams,
          'diamondPrice', diamond_price_twd,
          'taijinPrice', taijin_price_twd,
          'laborPrice', labor_price_twd,
          'total', total_price,
          'goldRatePerGram', gold_rate_per_gram,
          'priceSource', price_source
        )
      ),
      summary_zh = coalesce(
        nullif(trim(product_type), ''),
        nullif(trim(category), ''),
        '訂製品項'
      )
    where config_json = '{}'::jsonb
    """,
    """
    update orders
    set config_json = config_json || jsonb_build_object('clientPricing', pricing_json)
    where pricing_json <> '{}'::jsonb
      and not (config_json ? 'clientPricing')
    """,
    """
    alter table orders
      drop column if exists series,
      drop column if exists product_type,
      drop column if exists category,
      drop column if exists carat,
      drop column if exists gold_purity,
      drop column if exists color,
      drop column if exists diamond_kind,
      drop column if exists fancy_color,
      drop column if exists stone_count,
      drop column if exists diamond_shape,
      drop column if exists weight_grams,
      drop column if exists ring_size,
      drop column if exists engraving_band,
      drop column if exists engraving_girdle,
      drop column if exists include_chain,
      drop column if exists chain_product_id,
      drop column if exists chain_gold,
      drop column if exists chain_color,
      drop column if exists chain_length_cm,
      drop column if exists chain_weight_chin,
      drop column if exists chain_total_twd,
      drop column if exists diamond_price_twd,
      drop column if exists taijin_price_twd,
      drop column if exists labor_price_twd,
      drop column if exists tax_amount_twd,
      drop column if exists gold_rate_per_gram,
      drop column if exists price_source
    """,
    "create index if not exists orders_summary_zh_idx on orders (summary_zh)",
]


def _has_column(cur, table: str, column: str) -> bool:
    cur.execute(
        """
        select 1 from information_schema.columns
        where table_schema = 'public' and table_name = %s and column_name = %s
        """,
        (table, column),
    )
    return cur.fetchone() is not None


def main() -> None:
    dsn = os.environ.get("DATABASE_URL")
    if not dsn:
        sys.exit("DATABASE_URL is not set")

    with psycopg.connect(dsn, autocommit=True) as conn:
        with conn.cursor() as cur:
            cur.execute(STEPS[0])
            print("step 1 ok")

            if _has_column(cur, "orders", "category"):
                cur.execute(STEPS[1])
                print("step 2 ok (backfill)")
                cur.execute(STEPS[2])
                print("step 3 ok (clientPricing)")
                cur.execute(STEPS[3])
                print("step 4 ok (drop legacy columns)")
            else:
                print("step 2-4 skipped (already migrated)")

            cur.execute(STEPS[4])
            print("step 5 ok")

    print("orders json migration complete")


if __name__ == "__main__":
    main()
