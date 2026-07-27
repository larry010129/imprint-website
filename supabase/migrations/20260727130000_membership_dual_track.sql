-- Dual-track membership: referral + imprint flags + editable membership_settings

alter table profiles add column if not exists referral_code text;
alter table profiles add column if not exists referred_by uuid references profiles(id) on delete set null;
alter table profiles add column if not exists referred_at timestamptz;
alter table profiles add column if not exists imprint_invited boolean not null default false;
alter table profiles add column if not exists partner_imprint_invited boolean not null default false;

create unique index if not exists profiles_referral_code_uidx
  on profiles (referral_code)
  where referral_code is not null;

create index if not exists profiles_referred_by_idx
  on profiles (referred_by)
  where referred_by is not null;

create table if not exists membership_settings (
  id integer primary key,
  config_json jsonb not null default '{}'::jsonb,
  updated_at timestamptz not null default now(),
  constraint membership_settings_singleton check (id = 1)
);

insert into membership_settings (id, config_json)
values (1, '{}'::jsonb)
on conflict (id) do nothing;
