-- Split wide orders into orders (header) + order_items (product snapshot).
-- Handles: legacy wide table | json on orders | already split (no-op).

create table if not exists order_items (
  id uuid primary key default gen_random_uuid(),
  order_id uuid not null unique references orders(id) on delete cascade,
  product_id uuid references products(id) on delete set null,
  config_json jsonb not null default '{}',
  pricing_json jsonb not null default '{}',
  summary_zh text,
  sort_order int not null default 0,
  created_at timestamptz not null default now()
);

create index if not exists order_items_product_id_idx on order_items(product_id);

-- Ensure json columns exist on orders for intermediate upgrades.
alter table orders
  add column if not exists config_json jsonb not null default '{}',
  add column if not exists pricing_json jsonb not null default '{}',
  add column if not exists summary_zh text;

do $$
begin
  -- Legacy wide orders → json on orders row
  if exists (
    select 1 from information_schema.columns
    where table_schema = 'public' and table_name = 'orders' and column_name = 'category'
  ) then
    update orders
    set
      config_json = jsonb_strip_nulls(
        jsonb_build_object(
          'category', category,
          'type', case when product_id is not null then product_id::text else product_type end,
          'gold', gold_purity,
          'carat', carat,
          'color', color,
          'diamondKind', diamond_kind,
          'fancyColor', fancy_color,
          'stoneCount', stone_count,
          'diamondShape', diamond_shape,
          'ringSize', ring_size,
          'engravingBand', engraving_band,
          'engravingGirdle', engraving_girdle,
          'includeChain', include_chain,
          'chainGold', chain_gold,
          'chainColor', chain_color,
          'chainLength', case when coalesce(category, '') <> 'chain' then chain_length_cm else null end,
          'lengthCm', case when category = 'chain' then chain_length_cm else null end,
          'series', series,
          'summaryZh', product_type
        )
      ),
      pricing_json = jsonb_strip_nulls(
        jsonb_build_object(
          'weightGrams', weight_grams,
          'diamondPrice', diamond_price_twd,
          'taijinPrice', taijin_price_twd,
          'laborPrice', labor_price_twd,
          'total', total_price,
          'goldRatePerGram', gold_rate_per_gram,
          'priceSource', price_source
        )
      ),
      summary_zh = coalesce(
        nullif(trim(product_type), ''),
        nullif(trim(category), ''),
        '訂製品項'
      )
    where config_json = '{}'::jsonb;

    update orders
    set config_json = config_json || jsonb_build_object('clientPricing', pricing_json)
    where pricing_json <> '{}'::jsonb
      and not (config_json ? 'clientPricing');

    alter table orders drop constraint if exists orders_chain_product_id_fkey;

    alter table orders
      drop column if exists series,
      drop column if exists product_type,
      drop column if exists category,
      drop column if exists carat,
      drop column if exists gold_purity,
      drop column if exists color,
      drop column if exists diamond_kind,
      drop column if exists fancy_color,
      drop column if exists stone_count,
      drop column if exists diamond_shape,
      drop column if exists weight_grams,
      drop column if exists ring_size,
      drop column if exists engraving_band,
      drop column if exists engraving_girdle,
      drop column if exists include_chain,
      drop column if exists chain_product_id,
      drop column if exists chain_gold,
      drop column if exists chain_color,
      drop column if exists chain_length_cm,
      drop column if exists chain_weight_chin,
      drop column if exists chain_total_twd,
      drop column if exists diamond_price_twd,
      drop column if exists taijin_price_twd,
      drop column if exists labor_price_twd,
      drop column if exists tax_amount_twd,
      drop column if exists gold_rate_per_gram,
      drop column if exists price_source;
  end if;

  -- Move json snapshots from orders → order_items (one row per order)
  if exists (
    select 1 from information_schema.columns
    where table_schema = 'public' and table_name = 'orders' and column_name = 'config_json'
  ) then
    insert into order_items (order_id, product_id, config_json, pricing_json, summary_zh)
    select
      o.id,
      o.product_id,
      coalesce(o.config_json, '{}'::jsonb),
      coalesce(o.pricing_json, '{}'::jsonb),
      o.summary_zh
    from orders o
    where not exists (select 1 from order_items i where i.order_id = o.id)
      and (
        o.config_json <> '{}'::jsonb
        or o.pricing_json <> '{}'::jsonb
        or o.summary_zh is not null
        or o.product_id is not null
      );

    alter table orders drop constraint if exists orders_product_id_fkey;
    alter table orders drop column if exists config_json;
    alter table orders drop column if exists pricing_json;
    alter table orders drop column if exists product_id;
  end if;
end $$;

create index if not exists orders_summary_zh_idx on orders (summary_zh);
