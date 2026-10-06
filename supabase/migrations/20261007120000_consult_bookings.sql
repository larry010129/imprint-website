-- 預約諮詢日曆 (matches app.consult_bookings.ensure_consult_bookings_schema).
-- One non-cancelled booking per slot; RLS on with no policies so only the
-- app's direct DB connection can read/write.
-- NOT applied to live DB by the agent; the app also creates this at startup.

create table if not exists consult_bookings (
  id uuid primary key default gen_random_uuid(),
  slot_start timestamptz not null,
  name text not null,
  phone text not null default '',
  email text,
  note text,
  lead_id uuid references contact_messages(id) on delete set null,
  status text not null default 'confirmed'
    check (status in ('confirmed', 'done', 'cancelled')),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create unique index if not exists consult_bookings_one_per_slot
  on consult_bookings (slot_start) where status <> 'cancelled';

create index if not exists consult_bookings_lead_idx on consult_bookings (lead_id);

alter table consult_bookings enable row level security;
