-- Preferred in-store pickup datetime (member schedules when order is ready).
-- Ready = order_fulfillment.fulfillment_method = 'pickup' AND orders.status = 'shipped'.
-- Admin: set status to 「已出貨 / shipped」 when goods are ready for store pickup.

alter table if exists order_fulfillment
  add column if not exists pickup_preferred_at timestamptz;

comment on column order_fulfillment.pickup_preferred_at is
  'Member preferred store-pickup datetime (Asia/Taipei intent); set when status=shipped + method=pickup';
