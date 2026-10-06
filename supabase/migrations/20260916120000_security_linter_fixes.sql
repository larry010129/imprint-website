-- Fixes for Supabase database linter WARN findings (observed 2026-09-16):
--   1. function_search_path_mutable: product_images_touch_updated_at had no
--      pinned search_path.
--   2. anon/authenticated_security_definer_function_executable: rls_auto_enable()
--      is a SECURITY DEFINER function callable by anon/authenticated via
--      /rest/v1/rpc/rls_auto_enable. It is not defined anywhere in this repo's
--      migrations, so its origin/purpose is unverified. Revoking public EXECUTE
--      here as a precaution; confirm what it does before re-granting.
-- NOT applied to live DB by the agent that added this file — run in Supabase
-- SQL Editor (or your migration tool) against the production database.

create or replace function product_images_touch_updated_at()
returns trigger
language plpgsql
set search_path = ''
as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

revoke execute on function public.rls_auto_enable() from public, anon, authenticated;
