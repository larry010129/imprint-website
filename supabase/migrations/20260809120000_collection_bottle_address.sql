-- DNA / memorial collection bottle ship-to address (separate from finished-goods fulfillment).

alter table if exists order_fulfillment
  add column if not exists collection_bottle_address text,
  add column if not exists collection_bottle_city text,
  add column if not exists collection_bottle_postal text;

comment on column order_fulfillment.collection_bottle_address is
  'Street address for shipping the DNA/collection sample bottle';
comment on column order_fulfillment.collection_bottle_city is
  'City for collection bottle shipping';
comment on column order_fulfillment.collection_bottle_postal is
  'Postal code for collection bottle shipping';
