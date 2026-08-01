-- TOTP authenticator 2FA (RFC 6238) — optional for members, required for admins.

alter table users add column if not exists totp_secret text;
alter table users add column if not exists totp_enabled boolean not null default false;
alter table users add column if not exists totp_backup_codes jsonb;

comment on column users.totp_secret is 'Base32 TOTP secret; set during enroll, cleared on disable';
comment on column users.totp_backup_codes is 'JSON array of bcrypt hashes for one-time backup codes';
