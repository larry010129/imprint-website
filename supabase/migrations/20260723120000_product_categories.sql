-- Dynamic product categories (品項) for admin 商品上架 and shop step-1 tiles
create table if not exists product_categories (
  slug text primary key,
  label_zh text not null,
  label_en text,
  thumb_path text,
  sort_order int not null default 0,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

insert into product_categories (slug, label_zh, label_en, sort_order) values
  ('pendant', '項墜', 'Pendant', 0),
  ('ring', '戒指', 'Ring', 1),
  ('earring', '耳環', 'Earring', 2),
  ('bracelet', '手鍊', 'Bracelet', 3),
  ('chain', '鏈條', 'Chain', 4)
on conflict (slug) do nothing;
