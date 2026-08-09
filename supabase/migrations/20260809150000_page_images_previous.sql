-- One-deep previous image temp for page_images replace/restore (same as shop products).
alter table page_images
  add column if not exists previous_image_url text,
  add column if not exists previous_image_webp text;

comment on column page_images.previous_image_url is
  'Prior image_url kept for one-step restore after replace; null when none.';
comment on column page_images.previous_image_webp is
  'Prior image_webp kept with previous_image_url; null when none.';
