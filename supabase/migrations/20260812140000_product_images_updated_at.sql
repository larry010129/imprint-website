-- Cache-bust token for admin/public product thumbs (?v=updated_at).
-- NOT applied to live DB by the agent that added this file — run migrate/apply separately.

alter table product_images
  add column if not exists updated_at timestamptz not null default now();

comment on column product_images.updated_at is
  'Row touch time for image cache-busting (?v=); kept current on insert/update.';

create or replace function product_images_touch_updated_at()
returns trigger
language plpgsql
as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

drop trigger if exists product_images_touch_updated_at on product_images;
create trigger product_images_touch_updated_at
  before update on product_images
  for each row
  execute function product_images_touch_updated_at();
