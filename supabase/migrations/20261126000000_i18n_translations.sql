-- Machine translations of public CMS content (see app/i18n_store.py).
-- Corrections are made in the CMS 「翻譯」 tab (or by editing "translated" here).
-- The automatic sync never overwrites an existing row.
create table if not exists i18n_translations (
  source_hash text not null,
  lang text not null check (lang in ('en', 'ja', 'ko')),
  source text not null,
  translated text not null,
  updated_at timestamptz not null default now(),
  -- null = machine translation; set when an admin saves a correction
  edited_at timestamptz,
  primary key (source_hash, lang)
);

-- Server-only table: block Supabase's public API roles.
alter table i18n_translations enable row level security;
