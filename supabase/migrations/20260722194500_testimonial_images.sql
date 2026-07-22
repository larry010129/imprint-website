-- Add image_url to testimonials for CMS avatar / product photo

alter table testimonials
  add column if not exists image_url text not null default '';
