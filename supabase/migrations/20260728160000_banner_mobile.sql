-- Add mobile crop URL to home_banners for portrait-viewport carousel.
-- Desktop stays image_url (landscape 16:9); mobile gets image_url_mobile (portrait 9:16).

alter table home_banners
  add column if not exists image_url_mobile text not null default '';
