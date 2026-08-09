-- List-surface hot paths: admin leads, member history, catalog, accounts.
-- Source of truth: supabase/migrations (mirror into backend/schema.sql).

create index if not exists contact_messages_status_created_at_idx
  on contact_messages (status, created_at desc);

create index if not exists contact_messages_created_at_desc_idx
  on contact_messages (created_at desc);

create index if not exists quote_requests_status_created_at_idx
  on quote_requests (status, created_at desc);

create index if not exists quote_requests_created_at_desc_idx
  on quote_requests (created_at desc);

create index if not exists orders_user_id_created_at_desc_idx
  on orders (user_id, created_at desc);

create index if not exists products_published_sort_created_idx
  on products (is_published, sort_order, created_at);

create index if not exists users_created_at_desc_idx
  on users (created_at desc);
