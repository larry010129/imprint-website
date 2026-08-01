-- First-login onboarding gate: null means member must complete profile.
alter table profiles add column if not exists onboarding_completed_at timestamptz;
