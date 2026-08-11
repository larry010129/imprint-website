"""Seed page_copy_slots against DATABASE_URL from .env and verify the new rows.

Writes are exactly the intended slot upserts (idempotent, edit-preserving).
Never prints the DSN or any secret. Prints row counts and spot-check values.

Usage: .venv\\Scripts\\python.exe scripts\\seed_cms_copy_slots_verify.py
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(ROOT / ".env")

import psycopg  # noqa: E402
from psycopg.rows import dict_row  # noqa: E402

from app.cms_copy_slot_specs import copy_slot_specs  # noqa: E402
from app.cms_copy_slots import ensure_page_copy_slots_schema, seed_page_copy_slots  # noqa: E402

NEW_PAGES = (
    "/diamond-4c",
    "/lab-grown-diamond",
    "/diamond-comparison",
    "/journal",
    "/stories",
    "/faq",
    "/privacy",
    "/terms",
    "/return-policy",
)

SPOT_CHECKS = {
    ("/what-is-dna-diamond", "sec-cvd-title"): "什麼是 CVD 鑽石",
    ("/what-is-dna-diamond", "step-1-title"): "樣本萃取",
    ("/what-is-dna-diamond", "usp-1-title"): "在地實驗室",
    ("/diamond-4c", "sec-clarity-li-1"): "IF：十倍放大鏡下無包裹體，只有不明顯的可見外部瑕疵。",
    ("/lab-grown-diamond", "sec-ftc-title"): "FTC 2018：鑽石定義不再限於「自然」",
    ("/diamond-comparison", "sec-points-title"): "對照重點",
    ("/journal", "list-title"): "品牌日誌",
    ("/stories", "chrome-title"): "客戶見證",
    ("/faq", "know-title"): "想先讀完整說明？",
    ("/privacy", "collect-title"): "我們蒐集哪些資料",
    ("/terms", "price-title"): "價格",
    ("/return-policy", "custom-title"): "DNA 鑽石及其他客製化商品",
    ("/series", "det-pet-title"): "寵物鑽石",
    ("/series", "quick-signature-title"): "真我鑽石",
    ("/series", "next-title"): "還想多了解一點？",
    ("/series/pet/", "faq-1-q"): "寵物鑽石需要準備多少毛髮？",
    ("/series/signature/", "intro-title"): "讓每一個決定，都只屬於您的故事",
    ("/series/love/", "capture-title"): "讓思念，有個可以慢慢決定的地方",
    ("/about", "care-1-title"): "專屬託付",
    ("/contact", "form-label-name"): "姓名 *",
}


def main() -> int:
    dsn = (os.environ.get("DATABASE_URL") or "").strip()
    if not dsn:
        print("DATABASE_URL not set")
        return 1
    specs = copy_slot_specs()
    errors: list[str] = []
    with psycopg.connect(dsn, row_factory=dict_row) as conn:
        with conn.cursor() as cur:
            ensure_page_copy_slots_schema(cur)
            seeded = seed_page_copy_slots(cur)
            print(f"seed_page_copy_slots upserted rows: {seeded} (specs: {len(specs)})")

            # Every non-reserved spec must exist with matching default_text.
            cur.execute("select page_key, slot_key, default_text, kind from page_copy_slots")
            rows = {(r["page_key"], r["slot_key"]): r for r in cur.fetchall()}
            missing = [
                (s["page_key"], s["slot_key"])
                for s in specs
                if (s["page_key"], s["slot_key"]) not in rows
            ]
            if missing:
                errors.append(f"missing rows: {missing[:10]} ({len(missing)} total)")
            mismatched = [
                (s["page_key"], s["slot_key"])
                for s in specs
                if (s["page_key"], s["slot_key"]) in rows
                and rows[(s["page_key"], s["slot_key"])]["default_text"] != s["default_text"]
            ]
            if mismatched:
                errors.append(f"default_text mismatch: {mismatched[:10]} ({len(mismatched)} total)")

            cur.execute(
                "select count(*)::int as n from page_copy_slots where page_key like '/jewelry/%%' or page_key = '/jewelry/'"
            )
            jewelry_rows = cur.fetchone()["n"]
            if jewelry_rows:
                errors.append(f"reserved /jewelry rows present: {jewelry_rows}")

            for page in NEW_PAGES:
                cur.execute(
                    "select count(*)::int as n from page_copy_slots where page_key = %s", (page,)
                )
                print(f"  {page}: {cur.fetchone()['n']} rows")

            for (page, key), expect in SPOT_CHECKS.items():
                row = rows.get((page, key))
                if not row:
                    errors.append(f"spot check missing: {page} {key}")
                elif row["default_text"] != expect:
                    errors.append(f"spot check mismatch: {page} {key} -> {row['default_text'][:40]!r}")

    if errors:
        print("FAILURES:")
        for e in errors:
            print(" ", e)
        return 1
    print("All seeding checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
