-- Per-step status timestamps for order progress UI (M/D under each step).
alter table orders
  add column if not exists status_timestamps jsonb not null default '{}'::jsonb;

-- Backfill: received ← created_at
update orders
set status_timestamps = status_timestamps
  || jsonb_build_object('received', to_jsonb(created_at))
where not (status_timestamps ? 'received');

-- Backfill: current flow status ← updated_at (leave unknown middle steps empty)
update orders
set status_timestamps = status_timestamps
  || jsonb_build_object(status, to_jsonb(updated_at))
where status in (
    'order_confirming',
    'deposit_confirmed',
    'dna_lab',
    'in_production',
    'quality_check',
    'shipped',
    'completed'
  )
  and not (status_timestamps ? status);
