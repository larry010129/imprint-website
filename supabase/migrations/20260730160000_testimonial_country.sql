-- Free-text country / region when testimonial city is「其他」.

alter table testimonials
  add column if not exists country text not null default '';
