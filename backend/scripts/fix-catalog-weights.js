#!/usr/bin/env node
/* One-off correction: product_variants.weight_chin was seeded via a
 * density-ratio guess off the 14K column instead of the price-structure
 * sheet's literal per-metal figure (see the buildWeightTable fix in
 * ../lib/catalog-seed-data.js). This overwrites existing rows to match.
 *
 * Usage: node backend/scripts/fix-catalog-weights.js
 */
const { sql } = require('../lib/db');
const { buildSeedRows } = require('../lib/catalog-seed-data');

async function main() {
  const rows = buildSeedRows();
  let updated = 0;
  let unchanged = 0;
  let missing = 0;

  for (const row of rows) {
    const [product] = await sql`
      select id from products where category = ${row.category} and name_zh = ${row.nameZh}
    `;
    if (!product) {
      console.warn(`  ! no product found for ${row.category}/${row.nameZh}`);
      missing += row.variants.length;
      continue;
    }
    for (const v of row.variants) {
      const [variant] = await sql`
        select weight_chin from product_variants
        where product_id = ${product.id} and gold = ${v.gold} and carat = ${v.carat}
      `;
      if (!variant) {
        console.warn(`  ! no variant row for ${row.category}/${row.nameZh}/${v.gold}/${v.carat}`);
        missing += 1;
        continue;
      }
      if (Number(variant.weight_chin) === v.weightChin) {
        unchanged += 1;
        continue;
      }
      await sql`
        update product_variants set weight_chin = ${v.weightChin}
        where product_id = ${product.id} and gold = ${v.gold} and carat = ${v.carat}
      `;
      console.log(`  ${row.category}/${row.nameZh}/${v.gold}/${v.carat}: ${variant.weight_chin} -> ${v.weightChin}`);
      updated += 1;
    }
  }

  console.log(`Done — ${updated} updated, ${unchanged} already correct, ${missing} missing.`);
  await sql.end();
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
