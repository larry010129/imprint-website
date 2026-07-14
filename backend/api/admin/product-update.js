/* POST {id, ...same fields as admin/products.js POST}: edit an existing
 * product. Variants and images are replaced wholesale (the admin form
 * resends the full current state each save, same as the Flask edit page).
 */
const { sql } = require('../../lib/db');
const { requireAdmin } = require('../../lib/auth');
const { applyCors } = require('../../lib/cors');
const { validateProductFields } = require('../../lib/validation');
const { logAdminAction } = require('../../lib/audit');

module.exports = async function handler(req, res) {
  if (applyCors(req, res)) return;
  if (req.method !== 'POST') return res.status(405).json({ error: 'method not allowed' });

  const userId = await requireAdmin(req, res, sql);
  if (!userId) return;

  const { id } = req.body || {};
  if (!id) return res.status(400).json({ error: 'missing id' });

  const { cleaned, error } = validateProductFields(req.body);
  if (error) return res.status(400).json({ error });

  try {
    const [existing] = await sql`select id, is_published, first_published_at from products where id = ${id}`;
    if (!existing) return res.status(404).json({ error: 'product not found' });

    const firstPublishedAt = existing.first_published_at || (cleaned.isPublished ? new Date().toISOString() : null);

    const [product] = await sql`
      update products set
        category = ${cleaned.category}, name_zh = ${cleaned.nameZh}, name_en = ${cleaned.nameEn},
        description_zh = ${cleaned.descriptionZh}, description_en = ${cleaned.descriptionEn},
        default_color = ${cleaned.defaultColor}, is_published = ${cleaned.isPublished},
        first_published_at = ${firstPublishedAt}, updated_at = now()
      where id = ${id}
      returning *
    `;

    await sql`delete from product_variants where product_id = ${id}`;
    for (const v of cleaned.variants) {
      await sql`
        insert into product_variants (product_id, gold, carat, weight_chin, manual_price_twd)
        values (${id}, ${v.gold}, ${v.carat}, ${v.weightChin}, ${v.manualPriceTwd})
      `;
    }

    await sql`delete from product_images where product_id = ${id}`;
    let sortOrder = 0;
    for (const img of cleaned.images) {
      await sql`
        insert into product_images (product_id, color, file_path, sort_order)
        values (${id}, ${img.color}, ${img.url}, ${sortOrder++})
      `;
    }

    await logAdminAction(sql, { action: 'product_updated', detail: { productId: id, nameZh: product.name_zh } });
    res.status(200).json({ product });
  } catch (err) {
    console.error('[admin/product-update]', err);
    res.status(500).json({ error: '更新失敗' });
  }
};
