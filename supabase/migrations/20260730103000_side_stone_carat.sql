-- Per-variant side-stone (配鑽) carat weight for display / catalog.
alter table product_variants
  add column if not exists side_stone_carat numeric;

comment on column product_variants.side_stone_carat is
  'Optional side-stone (配鑽) total carat weight; display/info only, does not replace side_stone_price_twd.';
