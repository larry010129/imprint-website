-- First-party visit counter (matches app.site_visits.ensure_site_visits_schema).
-- Cookieless: unique visitors are a daily-salted hash, no raw IPs stored.
-- RLS on, no policies: only the app's direct DB connection can read/write.
-- NOT applied to live DB by the agent; the app also creates these at startup.

create table if not exists site_visits_daily (
  day date not null,
  path text not null,
  views bigint not null default 0,
  primary key (day, path)
);

create table if not exists site_visit_uniques (
  day date primary key,
  uniques bigint not null default 0
);

create table if not exists site_visitor_days (
  day date not null,
  visitor text not null,
  primary key (day, visitor)
);

alter table site_visits_daily enable row level security;
alter table site_visit_uniques enable row level security;
alter table site_visitor_days enable row level security;
