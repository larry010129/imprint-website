-- Built-in admin plugin registry (v1 toggles — not a marketplace)

create table if not exists admin_plugins (
  slug text primary key,
  enabled boolean not null default true,
  config jsonb not null default '{}'::jsonb,
  updated_at timestamptz not null default now()
);

insert into admin_plugins (slug, enabled, config) values
  ('seo-tools', true, '{}'::jsonb),
  ('media-optimize', true, '{}'::jsonb),
  ('analytics', true, '{}'::jsonb),
  ('cms-content', true, '{}'::jsonb),
  ('pricing-tools', true, '{}'::jsonb)
on conflict (slug) do nothing;
