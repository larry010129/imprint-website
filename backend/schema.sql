-- 銘印鑽石 IMPRINT DIAMOND — Supabase Postgres schema
-- Plain Postgres tables + app-layer auth (FastAPI / legacy Node api/*.js).
-- Apply via: python scripts/apply_schema.py  OR  cd backend && npm run schema

create extension if not exists pgcrypto;

-- ── auth ──────────────────────────────────────────────────────────────────
create table if not exists users (
  id uuid primary key default gen_random_uuid(),
  email text unique not null,
  password_hash text not null,
  email_verified boolean not null default false,
  is_active boolean not null default true,
  last_login_at timestamptz,
  created_at timestamptz not null default now()
);
-- Session revocation: bumped on logout / admin password reset to invalidate
-- all existing JWTs for a user without a server-side session table.
alter table users add column if not exists token_version integer not null default 0;

create table if not exists profiles (
  id uuid primary key references users(id) on delete cascade,
  full_name text,
  phone text,
  store_name text,
  is_partner boolean not null default false
);

create table if not exists staff_admins (
  user_id uuid primary key references users(id) on delete cascade
);

create table if not exists password_reset_tokens (
  token text primary key,
  user_id uuid not null references users(id) on delete cascade,
  expires_at timestamptz not null,
  used_at timestamptz
);

-- Server-side login/register lockout (Flask kept this in an in-process dict;
-- serverless functions share no memory between invocations, so this needs
-- to live in the DB instead — see lib/rateLimit.js).
create table if not exists login_lockouts (
  lockout_key text primary key, -- e.g. "login:<email>:<ip>" or "register:<ip>"
  fail_count int not null default 0,
  locked_until timestamptz,
  updated_at timestamptz not null default now()
);

-- Simple structured audit trail for admin actions (status changes, deletes,
-- password resets, etc). Flask wrote these to process logs; a table is more
-- useful here since there's an admin dashboard to read them back from.
create table if not exists audit_log (
  id uuid primary key default gen_random_uuid(),
  actor_email text,
  action text not null,
  detail jsonb not null default '{}',
  ip text,
  created_at timestamptz not null default now()
);

-- ── registration invites ──────────────────────────────────────────────────
create table if not exists invite_codes (
  id uuid primary key default gen_random_uuid(),
  code text unique not null,
  label text,
  created_by_id uuid references users(id) on delete set null,
  used_by_id uuid references users(id) on delete set null,
  use_count int not null default 0,
  max_uses int,
  is_active boolean not null default true,
  grants_admin boolean not null default false,
  grants_partner boolean not null default false,
  expires_at timestamptz,
  used_at timestamptz,
  created_at timestamptz not null default now()
);

-- ── product catalog (dynamic — admin-managed, replaces static jewelry/* pages) ──
create table if not exists products (
  id uuid primary key default gen_random_uuid(),
  category text not null, -- 'ring' | 'necklace' | 'earring' | 'bracelet' | 'pendant' | 'chain'
  name_zh text not null,
  name_en text,
  description_zh text,
  description_en text,
  default_color text not null default 'white',
  is_published boolean not null default false,
  first_published_at timestamptz,
  sort_order int not null default 0,
  created_by_id uuid references users(id) on delete set null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists product_variants (
  id uuid primary key default gen_random_uuid(),
  product_id uuid not null references products(id) on delete cascade,
  gold text not null, -- '18k' | '14k' | '9k' | 'pt950' | 'silver' | ...
  carat text not null, -- diamond carat, or '3fen' for plain chain/mounting-only variants
  weight_chin numeric not null, -- 蠟重(錢); metal = wax × WAX_TO_METAL[gold] at pricing time
  manual_price_twd numeric,
  unique (product_id, gold, carat)
);

create table if not exists product_images (
  id uuid primary key default gen_random_uuid(),
  product_id uuid not null references products(id) on delete cascade,
  color text not null,
  file_path text not null,
  sort_order int not null default 0
);

-- ── orders (core header + workflow) ──
create sequence if not exists order_number_seq start 100001;

create table if not exists orders (
  id uuid primary key default gen_random_uuid(),
  user_id uuid references users(id) on delete set null,
  order_number text unique not null default ('ID' || nextval('order_number_seq')),

  summary_zh text,
  total_price numeric,

  status text not null default 'received',
  status_note text,
  cancel_reason text,

  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

-- ── order_contacts (1:1 — customer at checkout) ──
create table if not exists order_contacts (
  order_id uuid primary key references orders(id) on delete cascade,
  customer_name text not null,
  customer_phone text not null,
  customer_email text
);

-- ── order_fulfillment (1:1 — pickup / delivery) ──
create table if not exists order_fulfillment (
  order_id uuid primary key references orders(id) on delete cascade,
  fulfillment_method text not null default 'pickup',
  shipping_address text,
  shipping_city text,
  shipping_postal text,
  order_note text
);

-- ── order_items (1:N — product spec + pricing snapshot) ──
create table if not exists order_items (
  id uuid primary key default gen_random_uuid(),
  order_id uuid not null references orders(id) on delete cascade,
  product_id uuid references products(id) on delete set null,
  config_json jsonb not null default '{}',
  pricing_json jsonb not null default '{}',
  summary_zh text,
  sort_order int not null default 0,
  created_at timestamptz not null default now()
);

-- ── cart / favorites (saved shop configurations) ─────────────────────────
create table if not exists cart_items (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references users(id) on delete cascade,
  product_id uuid references products(id) on delete set null,
  category text not null,
  style_type text not null,
  config_json jsonb not null,
  summary_zh text,
  total_price numeric,
  created_at timestamptz not null default now()
);

create table if not exists favorite_items (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references users(id) on delete cascade,
  product_id uuid references products(id) on delete set null,
  category text not null,
  style_type text not null,
  config_json jsonb not null,
  summary_zh text,
  created_at timestamptz not null default now()
);

-- ── notifications (e.g. "your order was removed by the shop") ────────────
create table if not exists user_notifications (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references users(id) on delete cascade,
  kind text not null default 'order_removed',
  message text not null,
  order_id uuid references orders(id) on delete set null,
  order_summary text,
  is_read boolean not null default false,
  created_at timestamptz not null default now()
);

-- ── leads ─────────────────────────────────────────────────────────────────
create table if not exists contact_messages (
  id uuid primary key default gen_random_uuid(),
  name text not null,
  phone text not null,
  email text,
  message text not null,
  source_page text,
  status text not null default 'new',
  created_at timestamptz not null default now()
);

create table if not exists quote_requests (
  id uuid primary key default gen_random_uuid(),
  name text not null,
  phone text not null,
  email text,
  series text,
  product_type text,
  carat text,
  color text,
  shape text,
  metal text,
  quantity int default 1,
  estimated_price numeric,
  status text not null default 'pending',
  created_at timestamptz not null default now()
);

-- ── pricing / live gold rate ──────────────────────────────────────────────
create table if not exists pricing_settings (
  id int primary key default 1,
  overrides jsonb not null default '{}',
  updated_at timestamptz not null default now(),
  constraint pricing_settings_singleton check (id = 1)
);
insert into pricing_settings (id, overrides) values (1, '{}')
  on conflict (id) do nothing;

create table if not exists gold_price_cache (
  id int primary key default 1,
  xau_per_gram numeric not null,
  xpt_per_gram numeric not null,
  xag_per_gram numeric not null,
  bot_posted_at text,
  source text not null default 'bot',
  source_url text,
  fetched_at timestamptz not null default now(),
  constraint gold_price_cache_singleton check (id = 1)
);
insert into gold_price_cache (id, xau_per_gram, xpt_per_gram, xag_per_gram, source)
  values (1, 4300, 1050, 30, 'fallback')
  on conflict (id) do nothing;

-- ── indexes ────────────────────────────────────────────────────────────────
create index if not exists orders_user_id_idx on orders(user_id);
create index if not exists orders_order_number_phone_idx on orders(order_number);
create index if not exists orders_summary_zh_idx on orders(summary_zh);
create index if not exists order_contacts_phone_idx on order_contacts(customer_phone);
create index if not exists order_items_order_id_idx on order_items(order_id);
create index if not exists order_items_product_id_idx on order_items(product_id);
create index if not exists product_variants_product_id_idx on product_variants(product_id);
create index if not exists product_images_product_id_idx on product_images(product_id);
create index if not exists cart_items_user_id_idx on cart_items(user_id);
create index if not exists favorite_items_user_id_idx on favorite_items(user_id);
create index if not exists user_notifications_user_id_idx on user_notifications(user_id, is_read);
create index if not exists products_category_published_idx on products(category, is_published);
