-- Journal posts CMS (brand timeline / 日誌)

create table if not exists journal_posts (
  id uuid primary key default gen_random_uuid(),
  title text not null,
  body text not null default '',
  posted_at date not null,
  image_url text,
  is_archived boolean not null default false,
  is_published boolean not null default true,
  sort_order int not null default 0,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists journal_posts_published_posted_idx
  on journal_posts (is_published, posted_at desc, sort_order);

-- Seed current hardcoded Journal.tsx ENTRIES (idempotent when table empty)
insert into journal_posts (title, body, posted_at, image_url, is_archived, is_published, sort_order)
select * from (values
  (
    '如果有一種方式，能把「牠」永遠留在你身邊，你會選擇嗎？',
    '',
    date '2026-03-18',
    null::text,
    false,
    true,
    0
  ),
  (
    '寵物展活動記錄',
    '',
    date '2023-12-01',
    null::text,
    false,
    true,
    1
  ),
  (
    '銘印鑽石將在台北寵物用品博覽會暨台北貓展與您見面',
    $b$展出地點：台北南港展覽館二館｜11568 台北市南港區經貿二路 2 號　攤位號碼：P1024
展出日期：2023/11/24（五）至 2023/11/27（一）　展出時間：10:00–18:00$b$,
    date '2023-11-01',
    null::text,
    true,
    true,
    2
  ),
  (
    '甚麼是實驗室生長鑽石（又稱未來鑽石、人造鑽石、培育鑽石）？與天然鑽石有何不同？',
    $b$人們自數百年前就嘗試合成鑽石，經過無數次的失敗，在上個世紀終於在實驗室合成出鑽石。目前合成寶石級鑽石的方法有兩種：一是高溫高壓法（HPHT），另一則是化學氣相沉積法（CVD）。$b$,
    date '2023-08-02',
    null::text,
    false,
    true,
    3
  )
) as v(title, body, posted_at, image_url, is_archived, is_published, sort_order)
where not exists (select 1 from journal_posts limit 1);
