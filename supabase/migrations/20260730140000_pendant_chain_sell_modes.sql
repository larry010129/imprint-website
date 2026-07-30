-- Per-product necklace/pendant sell modes: 僅墜子 and/or 含鍊賣.
alter table products
  add column if not exists allows_pendant_only boolean not null default true;

alter table products
  add column if not exists allows_with_chain boolean not null default true;

comment on column products.allows_pendant_only is
  'When true (pendant category), shop allows 僅墜子 (pendant without chain).';

comment on column products.allows_with_chain is
  'When true (pendant category), shop allows 含鍊賣 (pendant with chain length options).';
