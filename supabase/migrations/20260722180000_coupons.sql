-- Coupons for checkout discounts + redemptions + order discount columns

create table if not exists coupons (
  id uuid primary key default gen_random_uuid(),
  code text unique not null,
  label text,
  discount_type text not null check (discount_type in ('percent', 'fixed')),
  discount_value numeric not null check (discount_value > 0),
  min_order_amount numeric,
  max_uses int,
  max_uses_per_user int,
  used_count int not null default 0,
  is_active boolean not null default true,
  starts_at timestamptz,
  expires_at timestamptz,
  created_by_id uuid references users(id) on delete set null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists coupon_redemptions (
  id uuid primary key default gen_random_uuid(),
  coupon_id uuid not null references coupons(id) on delete cascade,
  user_id uuid not null references users(id) on delete cascade,
  order_id uuid not null references orders(id) on delete cascade,
  checkout_batch_id uuid not null,
  code text not null,
  discount_amount numeric not null default 0,
  order_subtotal numeric not null default 0,
  order_total numeric not null default 0,
  created_at timestamptz not null default now(),
  unique (coupon_id, order_id)
);

create index if not exists coupon_redemptions_coupon_user_idx
  on coupon_redemptions (coupon_id, user_id);

create index if not exists coupon_redemptions_batch_idx
  on coupon_redemptions (checkout_batch_id);

create index if not exists coupons_code_idx on coupons (code);

alter table orders add column if not exists coupon_code text;
alter table orders add column if not exists discount_amount numeric not null default 0;
alter table orders add column if not exists subtotal_before_discount numeric;
