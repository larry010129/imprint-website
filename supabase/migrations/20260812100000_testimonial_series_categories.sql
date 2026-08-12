-- Remap legacy testimonial category labels to current 六大系列 names.
-- 初生鑽石 → 滿月鑽石 (/series/first-love/)
-- 毛髮鑽石 → 真我鑽石 (/series/signature/)

update testimonials
set
  category = '滿月鑽石',
  role = regexp_replace(role, '^初生鑽石', '滿月鑽石')
where category = '初生鑽石';

update testimonials
set
  category = '真我鑽石',
  role = regexp_replace(role, '^毛髮鑽石', '真我鑽石')
where category = '毛髮鑽石';
