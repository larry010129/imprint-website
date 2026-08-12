-- Shared CMS key/value store for admin payloads (featured-video, engagement
-- rings, release notes, etc.). Matches app.cms_kv_store.ensure_cms_kv_schema.

create table if not exists cms_kv (
  key text primary key,
  value jsonb not null,
  updated_at timestamptz not null default now()
);
