-- Admin-only internal product code (e.g. "N-001"). Never surfaced to the
-- public shop API/pages — see app/catalog.py build_catalog_product(_lite).
-- NOT applied to live DB by the agent that added this file — run in Supabase
-- SQL Editor (or your migration tool) against the production database.

alter table products add column if not exists custom_id text;

create index if not exists products_custom_id_idx on products (custom_id);
