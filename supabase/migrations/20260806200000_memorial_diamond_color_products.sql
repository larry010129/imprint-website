-- Memorial diamond: one product row per gem color (白/黃/藍/粉鑽).
-- Idempotent — safe on DBs that already ran Python ensure_memorial_diamond_products.

alter table products add column if not exists style_key text;

create unique index if not exists products_style_key_uidx
  on products (style_key)
  where style_key is not null;

create table if not exists memorial_diamond_style_tombstones (
  style_key text primary key,
  deleted_at timestamptz not null default now()
);

-- Retire old 滿月/寵物/… series rows (keep for order history).
update products
set is_published = false,
    style_key = null,
    updated_at = now()
where category = 'diamond'
  and style_key in (
    'diamond-first-love',
    'diamond-pet',
    'diamond-love',
    'diamond-family',
    'diamond-heirloom'
  );

insert into products (
  category, name_zh, name_en, description_zh, default_color,
  allows_engraving, allows_fancy_shapes, allows_pendant_only, allows_with_chain,
  is_published, first_published_at, sort_order, style_key
)
select
  'diamond', v.name_zh, v.name_en, v.description_zh, v.color,
  false, true, true, true,
  true, now(), v.sort_order, v.style_key
from (
  values
    (0, 'diamond-white', 'white', '白鑽', 'White Diamond', '紀念白鑽（裸鑽試算，不含鑲嵌）'),
    (1, 'diamond-yellow', 'yellow', '黃鑽', 'Yellow Diamond', '紀念黃鑽（裸鑽試算，不含鑲嵌）'),
    (2, 'diamond-blue', 'blue', '藍鑽', 'Blue Diamond', '紀念藍鑽（裸鑽試算，不含鑲嵌）'),
    (3, 'diamond-pink', 'pink', '粉鑽', 'Pink Diamond', '紀念粉鑽（裸鑽試算，不含鑲嵌）')
) as v(sort_order, style_key, color, name_zh, name_en, description_zh)
where not exists (
  select 1 from products p where p.style_key = v.style_key
)
and not exists (
  select 1 from memorial_diamond_style_tombstones t where t.style_key = v.style_key
);

-- Shape matrix images per color product (round, oval, … × white/yellow/blue/pink).
insert into product_images (product_id, color, file_path, sort_order)
select
  p.id,
  s.shape,
  '/static/images/diamonds/matrix/' || s.shape || '-' || p.default_color || '.png',
  s.sort_order
from products p
cross join (
  values
    ('round', 0),
    ('marquise', 1),
    ('oval', 2),
    ('princess', 3),
    ('trilliant', 4),
    ('emerald', 5),
    ('heart', 6),
    ('radiant', 7),
    ('pear', 8),
    ('cushion', 9)
) as s(shape, sort_order)
where p.category = 'diamond'
  and p.style_key in ('diamond-white', 'diamond-yellow', 'diamond-blue', 'diamond-pink')
  and not exists (
    select 1
    from product_images pi
    where pi.product_id = p.id
      and pi.color = s.shape
  );
