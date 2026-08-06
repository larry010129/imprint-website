-- Memorial diamond (紀念鑽石) as first product category tab
insert into product_categories (slug, label_zh, label_en, sort_order, addon_price_twd)
values ('diamond', '紀念鑽石', 'Memorial diamond', 0, 0)
on conflict (slug) do update set
  sort_order = 0,
  label_zh = excluded.label_zh,
  label_en = coalesce(product_categories.label_en, excluded.label_en),
  updated_at = now();

update product_categories set sort_order = 1, updated_at = now() where slug = 'pendant';
update product_categories set sort_order = 2, updated_at = now() where slug = 'ring';
update product_categories set sort_order = 3, updated_at = now() where slug = 'earring';
update product_categories set sort_order = 4, updated_at = now() where slug = 'bracelet';
update product_categories set sort_order = 5, updated_at = now() where slug = 'chain';
