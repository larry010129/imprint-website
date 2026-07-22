-- Content CMS: testimonials + FAQ

create table if not exists testimonials (
  id uuid primary key default gen_random_uuid(),
  name text not null,
  role text not null default '',
  category text not null default '',
  city text not null default '',
  text text not null,
  rating int not null default 5 check (rating >= 1 and rating <= 5),
  sort_order int not null default 0,
  is_published boolean not null default true,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists faq_categories (
  id text primary key,
  title text not null,
  sort_order int not null default 0
);

create table if not exists faq_items (
  id text primary key,
  category_id text not null references faq_categories(id) on delete cascade,
  question text not null,
  answer text not null,
  sort_order int not null default 0,
  is_published boolean not null default true,
  show_in_teaser boolean not null default false,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists testimonials_published_sort_idx
  on testimonials (is_published, sort_order, created_at);
create index if not exists faq_items_category_idx on faq_items (category_id);
create index if not exists faq_items_published_idx on faq_items (is_published, sort_order);
