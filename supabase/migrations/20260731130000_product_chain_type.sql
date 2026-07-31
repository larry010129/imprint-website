-- Necklace pricing type for chain-only products (e.g. 抖圓鏈).
alter table products add column if not exists chain_type text;

update products
set chain_type = 'douyuan'
where category = 'chain' and chain_type is null;
