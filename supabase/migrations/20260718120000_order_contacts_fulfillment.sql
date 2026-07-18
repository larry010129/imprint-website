-- Normalize orders: split customer + shipping into child tables (1:1 FK → orders).

create table if not exists order_contacts (
  order_id uuid primary key references orders(id) on delete cascade,
  customer_name text not null,
  customer_phone text not null,
  customer_email text
);

create table if not exists order_fulfillment (
  order_id uuid primary key references orders(id) on delete cascade,
  fulfillment_method text not null default 'pickup',
  shipping_address text,
  shipping_city text,
  shipping_postal text,
  order_note text
);

do $$
begin
  if exists (
    select 1 from information_schema.columns
    where table_schema = 'public' and table_name = 'orders' and column_name = 'customer_name'
  ) then
    insert into order_contacts (order_id, customer_name, customer_phone, customer_email)
    select id, customer_name, customer_phone, customer_email
    from orders
    where not exists (select 1 from order_contacts c where c.order_id = orders.id);

    insert into order_fulfillment (
      order_id, fulfillment_method, shipping_address, shipping_city, shipping_postal, order_note
    )
    select id, fulfillment_method, shipping_address, shipping_city, shipping_postal, order_note
    from orders
    where not exists (select 1 from order_fulfillment f where f.order_id = orders.id);

    alter table orders
      drop column if exists customer_name,
      drop column if exists customer_phone,
      drop column if exists customer_email,
      drop column if exists fulfillment_method,
      drop column if exists shipping_address,
      drop column if exists shipping_city,
      drop column if exists shipping_postal,
      drop column if exists order_note;
  end if;
end $$;

create index if not exists order_contacts_phone_idx on order_contacts (customer_phone);
