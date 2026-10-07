-- Short share links for the calculator's 分享摘要 (matches app.share_links.ensure_share_links_schema).
-- RLS on with no policies: only the app's direct DB connection can read/write.
-- NOT applied to live DB by the agent; the app also creates/alters this at startup.

create table if not exists share_links (
  code text primary key,
  config jsonb not null,
  config_hash text not null unique,
  created_at timestamptz not null default now()
);

alter table share_links enable row level security;

-- Expiry: links nobody opens for a year are deleted (see app/share_links.py).
alter table share_links add column if not exists last_opened_at timestamptz;

create index if not exists share_links_last_seen_idx
  on share_links ((coalesce(last_opened_at, created_at)));
