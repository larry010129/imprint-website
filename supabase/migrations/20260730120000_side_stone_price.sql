-- Per-variant side-stone (配鑽) price + per-product engraving flag.
alter table product_variants
  add column if not exists side_stone_price_twd numeric;

comment on column product_variants.side_stone_price_twd is
  'Optional fixed side-stone (配鑽) price in TWD; added on top of formula pricing when set.';

alter table products
  add column if not exists allows_engraving boolean not null default true;

comment on column products.allows_engraving is
  'When true, shop shows girdle/band engraving UI for this product.';
