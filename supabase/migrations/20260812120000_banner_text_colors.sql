-- Per-role home banner text colors (eyebrow / title / lead).
-- Backfill from legacy single `tone` so existing banners keep their look.

alter table home_banners
  add column if not exists eyebrow_color text not null default 'white';

alter table home_banners
  add column if not exists title_color text not null default 'white';

alter table home_banners
  add column if not exists lead_color text not null default 'white';

update home_banners
set
  eyebrow_color = coalesce(nullif(trim(tone), ''), 'white'),
  title_color = coalesce(nullif(trim(tone), ''), 'white'),
  lead_color = coalesce(nullif(trim(tone), ''), 'white')
where eyebrow_color = 'white'
  and title_color = 'white'
  and lead_color = 'white'
  and coalesce(nullif(trim(tone), ''), 'white') <> 'white';
