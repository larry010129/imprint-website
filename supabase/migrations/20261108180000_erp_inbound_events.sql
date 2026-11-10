-- ERP Inbound Events and Nonce Storage for ERP Inbound Pull Integration

create table if not exists erp_inbound_events (
    id uuid primary key,
    event_type text not null,
    idempotency_key text not null unique,
    occurred_at timestamptz not null default now(),
    payload jsonb not null,
    status text not null default 'pending',
    attempts int not null default 0,
    last_error text,
    created_at timestamptz not null default now(),
    acked_at timestamptz,
    seq bigserial
);

create index if not exists erp_inbound_events_status_seq_idx on erp_inbound_events (status, seq);
create index if not exists erp_inbound_events_created_at_idx on erp_inbound_events (created_at);

create table if not exists erp_inbound_nonces (
    key_id text not null,
    nonce text not null,
    created_at timestamptz not null default now(),
    primary key (key_id, nonce)
);

create index if not exists erp_inbound_nonces_created_at_idx on erp_inbound_nonces (created_at);
