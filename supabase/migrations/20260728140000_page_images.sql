-- Existing content-image slots per public page (CMS).

create table if not exists page_images (
  page_key text not null,
  slot_key text not null default 'hero',
  label text not null,
  slot_label text not null default '主視覺',
  group_key text not null default 'brand',
  image_url text not null default '',
  image_webp text,
  image_alt text not null default '',
  default_image_url text not null default '',
  default_image_webp text,
  target_w int not null,
  target_h int not null,
  sort_order int not null default 0,
  is_published boolean not null default true,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  primary key (page_key, slot_key)
);

alter table page_images add column if not exists slot_key text;
update page_images
set slot_key = case when page_key = '/about.html' then 'cinema' else 'hero' end
where slot_key is null or btrim(slot_key) = '' or (page_key = '/about.html' and slot_key = 'hero');
alter table page_images alter column slot_key set default 'hero';
alter table page_images alter column slot_key set not null;

alter table page_images add column if not exists slot_label text;
update page_images set slot_label = label
where slot_label is null or btrim(slot_label) = '';
alter table page_images alter column slot_label set default '主視覺';
alter table page_images alter column slot_label set not null;

do $$
declare current_pk text;
declare key_count int;
begin
  select conname, cardinality(conkey) into current_pk, key_count
  from pg_constraint
  where conrelid = 'page_images'::regclass and contype = 'p';
  if current_pk is not null and key_count = 1 then
    execute format('alter table page_images drop constraint %I', current_pk);
    current_pk := null;
  end if;
  if current_pk is null then
    alter table page_images
      add constraint page_images_pkey primary key (page_key, slot_key);
  end if;
end $$;

drop index if exists page_images_group_sort_idx;
create index if not exists page_images_group_sort_idx
  on page_images (group_key, sort_order, page_key, slot_key);
