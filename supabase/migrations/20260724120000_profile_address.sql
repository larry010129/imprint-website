-- Saved shipping address on member profile (prefills checkout).
alter table profiles add column if not exists shipping_postal text;
alter table profiles add column if not exists shipping_city text;
alter table profiles add column if not exists shipping_address text;
