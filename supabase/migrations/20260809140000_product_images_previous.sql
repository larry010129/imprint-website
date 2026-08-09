-- One-deep previous image temp for admin replace/restore.
alter table product_images
  add column if not exists previous_file_path text;

comment on column product_images.previous_file_path is
  'Prior file_path kept for one-step restore after replace; null when none.';
