-- Fixes HTTP 500 on product edit: products.created_by_id pointing at a
-- deleted user violates the FK on any save. Column is nullable/audit-only.
-- NOT applied to live DB by the agent that added this file — run in Supabase
-- SQL Editor (or your migration tool) against the production database.

update products
set created_by_id = null
where created_by_id is not null
  and not exists (
    select 1 from users u where u.id = products.created_by_id
  );
