-- Per-category universal addon (品項加價) — NT$ surcharge used as category labor.
-- Chain defaults to 3000 (replaces hardcoded CHAIN_LABOR_FEE_TWD["other"]); others 0.
alter table product_categories
  add column if not exists addon_price_twd int not null default 0;

comment on column product_categories.addon_price_twd is
  'Universal NT$ addon for this category (e.g. chain labor for non-s925). 0 = use default labor.';

update product_categories
set addon_price_twd = 3000
where slug = 'chain' and addon_price_twd = 0;
