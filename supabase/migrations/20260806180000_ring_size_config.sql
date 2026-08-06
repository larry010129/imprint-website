-- Per-product ring size config: starting size + size→品項加價 (separate from category/variant addon).
alter table products
  add column if not exists ring_size_config jsonb;

comment on column products.ring_size_config is
  'Ring-only JSON: {startSize, sizes:[{size, addonPriceTwd}]}. Size addon stacks on labor; null = shop defaults.';
