-- Google Identity Services sign-in (Google's stable per-account subject id).
alter table users add column if not exists google_id text unique;
