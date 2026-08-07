-- Category-level ring size policy (min/max/per-size). Product ring_size_config remains legacy fallback.
alter table product_categories
  add column if not exists ring_size_config jsonb;

comment on column product_categories.ring_size_config is
  'Ring category JSON: {minSize, maxSize, pricePerSizeTwd, startSize}. Preferred over products.ring_size_config.';
