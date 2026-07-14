/* GET: list ALL products (published + drafts) for the admin dashboard.
 * POST: create a new product with its variants + images.
 */
const { sql } = require('../../lib/db');
const { requireAdmin, getUserId } = require('../../lib/auth');
const { applyCors } = require('../../lib/cors');
const { validateProductFields } = require('../../lib/validation');
const { logAdminAction } = require('../../lib/audit');

module.exports = async function handler(req, res) {
  if (applyCors(req, res)) return;

  const userId = await requireAdmin(req, res, sql);
  if (!userId) return;

  if (req.method === 'GET') {
    try {
      const products = await sql`select * from products order by sort_order, created_at desc`;
      const productIds = products.map((p) => p.id);
      const [variants, images] = productIds.length
        ? await Promise.all([
            sql`select * from product_variants where product_id = any(${productIds})`,
            sql`select * from product_images where product_id = any(${productIds}) order by sort_order`,
          ])
        : [[], []];
      const variantsByProduct = {};
      for (const v of variants) (variantsByProduct[v.product_id] ||= []).push(v);
      const imagesByProduct = {};
      for (const img of images) (imagesByProduct[img.product_id] ||= []).push(img);

      return res.status(200).json({
        products: products.map((p) => ({ ...p, variants: variantsByProduct[p.id] || [], images: imagesByProduct[p.id] || [] })),
      });
    } catch (err) {
      console.error('[admin/products GET]', err);
      return res.status(500).json({ error: '載入失敗' });
    }
  }

  if (req.method === 'POST') {
    const { cleaned, error } = validateProductFields(req.body);
    if (error) return res.status(400).json({ error });

    const firstPublishedAt = cleaned.isPublished ? new Date().toISOString() : null;

    try {
      const [product] = await sql`
        insert into products (category, name_zh, name_en, description_zh, description_en, default_color, is_published, first_published_at, created_by_id)
        values (${cleaned.category}, ${cleaned.nameZh}, ${cleaned.nameEn}, ${cleaned.descriptionZh}, ${cleaned.descriptionEn},
                ${cleaned.defaultColor}, ${cleaned.isPublished}, ${firstPublishedAt}, ${userId})
        returning *
      `;

      for (const v of cleaned.variants) {
        await sql`
          insert into product_variants (product_id, gold, carat, weight_chin, manual_price_twd)
          values (${product.id}, ${v.gold}, ${v.carat}, ${v.weightChin}, ${v.manualPriceTwd})
        `;
      }
      let sortOrder = 0;
      for (const img of cleaned.images) {
        await sql`
          insert into product_images (product_id, color, file_path, sort_order)
          values (${product.id}, ${img.color}, ${img.url}, ${sortOrder++})
        `;
      }

      await logAdminAction(sql, { actorEmail: null, action: 'product_created', detail: { productId: product.id, nameZh: product.name_zh } });
      res.status(200).json({ product });
    } catch (err) {
      console.error('[admin/products POST]', err);
      res.status(500).json({ error: '建立失敗' });
    }
    return;
  }

  res.status(405).json({ error: 'method not allowed' });
};
