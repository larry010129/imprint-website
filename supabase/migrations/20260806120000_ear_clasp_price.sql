-- Per-variant 耳扣價錢 (earring findings) — earring styles only; folded into labor / 金工價格.
alter table product_variants
  add column if not exists ear_clasp_price_twd numeric;

comment on column product_variants.ear_clasp_price_twd is
  'Optional earring-only 耳扣價錢 in TWD; added into labor/金工價格 for that metal×carat row.';
