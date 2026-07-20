-- Session revocation: bump token_version to invalidate all existing JWTs for
-- a user (logout, admin password reset) without a server-side session table.

alter table users add column if not exists token_version integer not null default 0;
