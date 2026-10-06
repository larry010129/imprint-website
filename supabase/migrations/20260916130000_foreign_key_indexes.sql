-- Covering indexes for unindexed foreign keys (Supabase linter WARN,
-- observed 2026-09-16, lint=0001_unindexed_foreign_keys).
--
-- Uses CONCURRENTLY so index builds don't lock out writes on these tables.
-- IMPORTANT: CREATE INDEX CONCURRENTLY cannot run inside a transaction block.
-- Run each statement individually (SQL Editor: execute one at a time, or use
-- `psql -f` / a client with autocommit) rather than as one pasted block or
-- via a tool that wraps the whole file in BEGIN/COMMIT.
-- NOT applied to live DB by the agent that added this file — run in Supabase
-- SQL Editor (or your migration tool) against the production database.

create index concurrently if not exists cart_items_product_id_idx
  on cart_items (product_id);

create index concurrently if not exists coupon_redemptions_order_id_idx
  on coupon_redemptions (order_id);

create index concurrently if not exists coupon_redemptions_user_id_idx
  on coupon_redemptions (user_id);

create index concurrently if not exists coupons_created_by_id_idx
  on coupons (created_by_id);

create index concurrently if not exists favorite_items_product_id_idx
  on favorite_items (product_id);

create index concurrently if not exists invite_codes_created_by_id_idx
  on invite_codes (created_by_id);

create index concurrently if not exists invite_codes_used_by_id_idx
  on invite_codes (used_by_id);

create index concurrently if not exists password_reset_tokens_user_id_idx
  on password_reset_tokens (user_id);

create index concurrently if not exists products_created_by_id_idx
  on products (created_by_id);

create index concurrently if not exists user_notifications_order_id_idx
  on user_notifications (order_id);
