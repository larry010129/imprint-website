-- Diamond cut / shape registry (built-ins + admin-created cuts).
-- Asscher (阿斯切) seeded; further cuts added via admin API.

create table if not exists diamond_shapes (
  id text primary key,
  label_zh text not null,
  label_en text,
  sort_order int not null default 0,
  is_builtin boolean not null default false,
  created_at timestamptz not null default now()
);

insert into diamond_shapes (id, label_zh, label_en, sort_order, is_builtin) values
  ('round', '圓形', 'Round', 0, true),
  ('marquise', '馬眼型', 'Marquise', 1, true),
  ('oval', '橢圓形', 'Oval', 2, true),
  ('princess', '公主方', 'Princess', 3, true),
  ('trilliant', '三角形', 'Trilliant', 4, true),
  ('emerald', '祖母綠形', 'Emerald', 5, true),
  ('heart', '心形', 'Heart', 6, true),
  ('radiant', '雷地恩形', 'Radiant', 7, true),
  ('pear', '梨形', 'Pear', 8, true),
  ('cushion', '枕形', 'Cushion', 9, true),
  ('asscher', '阿斯切', 'Asscher', 10, true)
on conflict (id) do update set
  label_zh = excluded.label_zh,
  label_en = coalesce(diamond_shapes.label_en, excluded.label_en),
  sort_order = excluded.sort_order,
  is_builtin = true;
