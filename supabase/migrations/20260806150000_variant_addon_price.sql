-- Per-variant 品項加價 — overrides category addon_price_twd when set; folded into labor.
alter table product_variants
  add column if not exists addon_price_twd numeric;

comment on column product_variants.addon_price_twd is
  'Optional per-row 品項加價 in TWD; when null, pricing falls back to product_categories.addon_price_twd.';
