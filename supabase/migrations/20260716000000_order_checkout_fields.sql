-- Checkout confirm-order page: collect fulfillment method, shipping address,
-- and an optional order note before an order is created.
alter table orders
  add column if not exists fulfillment_method text not null default 'pickup',
  add column if not exists shipping_address text,
  add column if not exists shipping_city text,
  add column if not exists shipping_postal text,
  add column if not exists order_note text;
