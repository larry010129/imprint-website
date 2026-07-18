-- =============================================================================
-- IMPRINT DIAMOND — Normalize wide public.orders → 4 tables (PK / FK)
-- Run in Supabase: Dashboard → SQL Editor → New query → Paste → Run
-- Safe to re-run: skips steps already applied.
-- =============================================================================

-- ── 1. Child tables ─────────────────────────────────────────────────────────

create table if not exists public.order_contacts (
  order_id uuid primary key references public.orders(id) on delete cascade,
  customer_name text not null,
  customer_phone text not null,
  customer_email text
);

create table if not exists public.order_fulfillment (
  order_id uuid primary key references public.orders(id) on delete cascade,
  fulfillment_method text not null default 'pickup',
  shipping_address text,
  shipping_city text,
  shipping_postal text,
  order_note text
);

create table if not exists public.order_items (
  id uuid primary key default gen_random_uuid(),
  order_id uuid not null references public.orders(id) on delete cascade,
  product_id uuid references public.products(id) on delete set null,
  config_json jsonb not null default '{}',
  pricing_json jsonb not null default '{}',
  summary_zh text,
  sort_order int not null default 0,
  created_at timestamptz not null default now()
);

-- ── 2. Migrate legacy wide columns → json, then into child tables ───────────

alter table public.orders
  add column if not exists config_json jsonb not null default '{}',
  add column if not exists pricing_json jsonb not null default '{}',
  add column if not exists summary_zh text;

do $$
begin
  -- A) Wide spec/pricing columns still on orders → pack into json on orders row
  if exists (
    select 1 from information_schema.columns
    where table_schema = 'public' and table_name = 'orders' and column_name = 'category'
  ) then
    update public.orders
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
          'chainProductId', chain_product_id,
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
          'chainTotal', chain_total_twd,
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

    update public.orders
    set config_json = config_json || jsonb_build_object('clientPricing', pricing_json)
    where pricing_json <> '{}'::jsonb
      and not (config_json ? 'clientPricing');

    alter table public.orders drop constraint if exists orders_chain_product_id_fkey;

    alter table public.orders
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

  -- B) Json on orders → order_items
  if exists (
    select 1 from information_schema.columns
    where table_schema = 'public' and table_name = 'orders' and column_name = 'config_json'
  ) then
    insert into public.order_items (order_id, product_id, config_json, pricing_json, summary_zh)
    select
      o.id,
      o.product_id,
      coalesce(o.config_json, '{}'::jsonb),
      coalesce(o.pricing_json, '{}'::jsonb),
      o.summary_zh
    from public.orders o
    where not exists (select 1 from public.order_items i where i.order_id = o.id)
      and (
        o.config_json <> '{}'::jsonb
        or o.pricing_json <> '{}'::jsonb
        or o.summary_zh is not null
        or o.product_id is not null
      );

    alter table public.orders drop constraint if exists orders_product_id_fkey;
    alter table public.orders drop column if exists config_json;
    alter table public.orders drop column if exists pricing_json;
    alter table public.orders drop column if exists product_id;
  end if;

  -- C) Customer + shipping on orders → child tables
  if exists (
    select 1 from information_schema.columns
    where table_schema = 'public' and table_name = 'orders' and column_name = 'customer_name'
  ) then
    insert into public.order_contacts (order_id, customer_name, customer_phone, customer_email)
    select id, customer_name, customer_phone, customer_email
    from public.orders
    where not exists (select 1 from public.order_contacts c where c.order_id = orders.id);

    insert into public.order_fulfillment (
      order_id, fulfillment_method, shipping_address, shipping_city, shipping_postal, order_note
    )
    select id, fulfillment_method, shipping_address, shipping_city, shipping_postal, order_note
    from public.orders
    where not exists (select 1 from public.order_fulfillment f where f.order_id = orders.id);

    alter table public.orders
      drop column if exists customer_name,
      drop column if exists customer_phone,
      drop column if exists customer_email,
      drop column if exists fulfillment_method,
      drop column if exists shipping_address,
      drop column if exists shipping_city,
      drop column if exists shipping_postal,
      drop column if exists order_note;
  end if;
end $$;

-- ── 3. Indexes (replace old phone index on orders) ────────────────────────

drop index if exists public.orders_order_number_phone_idx;

create index if not exists orders_user_id_idx on public.orders (user_id);
create index if not exists orders_summary_zh_idx on public.orders (summary_zh);
create index if not exists order_contacts_phone_idx on public.order_contacts (customer_phone);
create index if not exists order_items_order_id_idx on public.order_items (order_id);
create index if not exists order_items_product_id_idx on public.order_items (product_id);

-- Done. public.orders should now have ~12 columns:
-- id, user_id, order_number, summary_zh, total_price, status, status_note,
-- cancel_reason, created_at, updated_at
