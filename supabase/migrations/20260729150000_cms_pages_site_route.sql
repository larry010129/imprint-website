-- Link fixed site routes to modular CMS host pages (section stack under live templates)

alter table cms_pages
  add column if not exists site_route text;

create unique index if not exists cms_pages_site_route_uidx
  on cms_pages (site_route)
  where site_route is not null;
