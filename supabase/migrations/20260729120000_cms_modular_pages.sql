-- Modular editable pages (section stack) + copy slots + media library

create table if not exists cms_pages (
  id uuid primary key default gen_random_uuid(),
  slug text not null unique,
  title text not null default '',
  meta_description text not null default '',
  status text not null default 'draft'
    check (status in ('draft', 'published')),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists cms_page_sections (
  id uuid primary key default gen_random_uuid(),
  page_id uuid not null references cms_pages(id) on delete cascade,
  sort_order int not null default 0,
  type text not null,
  props jsonb not null default '{}'::jsonb,
  is_visible boolean not null default true,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists cms_page_sections_page_sort_idx
  on cms_page_sections (page_id, sort_order, id);
create index if not exists cms_pages_status_idx
  on cms_pages (status, updated_at desc);

create table if not exists page_copy_slots (
  page_key text not null,
  slot_key text not null,
  kind text not null check (kind in ('text', 'button')),
  label text not null default '',
  text_value text not null default '',
  href text not null default '',
  default_text text not null default '',
  default_href text not null default '',
  sort_order int not null default 0,
  is_published boolean not null default true,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  primary key (page_key, slot_key)
);

create index if not exists page_copy_slots_page_sort_idx
  on page_copy_slots (page_key, sort_order, slot_key);

create table if not exists cms_media (
  id uuid primary key default gen_random_uuid(),
  url text not null,
  alt text not null default '',
  filename text not null default '',
  created_at timestamptz not null default now()
);

create index if not exists cms_media_created_idx on cms_media (created_at desc);

-- Never allow shop/jewelry/price rows in copy slots
delete from page_copy_slots
where page_key like '/shop/%'
   or page_key like '/jewelry/%'
   or page_key = '/jewelry/'
   or page_key = '/price.html';
