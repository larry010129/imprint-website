-- Shop linking key for memorial diamond styles (diamond-first-love, …)
alter table products add column if not exists style_key text;

create unique index if not exists products_style_key_uidx
  on products (style_key)
  where style_key is not null;

comment on column products.style_key is
  'Stable shop style key (e.g. diamond-first-love). Null for letter-SKU jewelry.';
