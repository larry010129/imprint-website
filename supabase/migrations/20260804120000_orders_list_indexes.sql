-- Admin order list + dashboard hot paths: date sort and status filters.
-- Source of truth: supabase/migrations (sync obvious bits into backend/schema.sql).

create index if not exists orders_created_at_desc_idx
  on orders (created_at desc);

create index if not exists orders_status_created_at_idx
  on orders (status, created_at desc);
