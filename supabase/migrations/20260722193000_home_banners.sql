-- Homepage hero carousel banners

create table if not exists home_banners (
  id uuid primary key default gen_random_uuid(),
  eyebrow text not null default '',
  title text not null,
  lead text not null default '',
  image_url text not null,
  image_webp text,
  image_alt text not null default '',
  cta_primary_label text not null default '',
  cta_primary_href text not null default '',
  cta_secondary_label text not null default '',
  cta_secondary_href text not null default '',
  tone text not null default 'warm',
  sort_order int not null default 0,
  is_published boolean not null default true,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists home_banners_published_sort_idx
  on home_banners (is_published, sort_order, created_at);
