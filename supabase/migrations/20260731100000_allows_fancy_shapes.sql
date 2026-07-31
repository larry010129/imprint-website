-- Per-product fancy-cut toggle: when false, shop hides 「其它形狀 +10%」 and forces round.
alter table products
  add column if not exists allows_fancy_shapes boolean not null default true;

comment on column products.allows_fancy_shapes is
  'When true, shop shows non-round diamond cut (+10%) options for this style.';
