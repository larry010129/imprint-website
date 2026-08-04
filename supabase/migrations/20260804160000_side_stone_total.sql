-- Optional fixed 配鑽價錢 total (overrides carat × 一克拉價格 when set).
alter table product_variants
  add column if not exists side_stone_total_twd numeric;

comment on column product_variants.side_stone_total_twd is
  'Optional fixed side-stone (配鑽價錢) total in TWD; when set, pricing uses this instead of side_stone_carat × side_stone_price_twd.';

comment on column product_variants.side_stone_price_twd is
  'Optional side-stone price-per-carat (一克拉價格) in TWD; formula total = side_stone_carat × this unless side_stone_total_twd is set.';
