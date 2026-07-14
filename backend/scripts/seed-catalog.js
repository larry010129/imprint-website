#!/usr/bin/env node
/* Seed published legacy catalog rows into Neon (13 style slots + 3 chains).
 *
 * Usage (from repo root or backend/):
 *   set DATABASE_URL=postgresql://...   (Windows)
 *   export DATABASE_URL=postgresql://... (macOS/Linux)
 *   node backend/scripts/seed-catalog.js
 *
 * Prerequisite: run backend/schema.sql on the Neon database first.
 */
const { sql } = require('../lib/db');
const { buildSeedRows } = require('../lib/catalog-seed-data');

async function seedCatalog() {
  const [{ count }] = await sql`select count(*)::int as count from products`;
  if (count > 0) {
    console.log(`products table already has ${count} row(s) — skipping.`);
    return 0;
  }

  const rows = buildSeedRows();
  let created = 0;

  for (const row of rows) {
    const [product] = await sql`
      insert into products (
        category, name_zh, default_color, is_published, first_published_at, sort_order
      ) values (
        ${row.category},
        ${row.nameZh},
        ${row.defaultColor},
        true,
        now(),
        ${row.sortOrder}
      )
      returning id
    `;

    for (const v of row.variants) {
      await sql`
        insert into product_variants (product_id, gold, carat, weight_chin)
        values (${product.id}, ${v.gold}, ${v.carat}, ${v.weightChin})
      `;
    }

    for (const img of row.images) {
      await sql`
        insert into product_images (product_id, color, file_path, sort_order)
        values (${product.id}, ${img.color}, ${img.filePath}, 0)
      `;
    }

    created += 1;
    console.log(`  + ${row.category} ${row.style} — ${row.nameZh}`);
  }

  return created;
}

async function main() {
  console.log('Seeding legacy catalog into Neon…');
  const n = await seedCatalog();
  console.log(n ? `Done — ${n} product(s) created.` : 'Nothing to do.');
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
