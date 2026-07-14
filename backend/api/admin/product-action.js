/* POST {id, action: 'publish'|'unpublish'|'delete'|'duplicate'} */
const { sql } = require('../../lib/db');
const { requireAdmin } = require('../../lib/auth');
const { applyCors } = require('../../lib/cors');
const { logAdminAction } = require('../../lib/audit');

const ACTIONS = new Set(['publish', 'unpublish', 'delete', 'duplicate']);

module.exports = async function handler(req, res) {
  if (applyCors(req, res)) return;
  if (req.method !== 'POST') return res.status(405).json({ error: 'method not allowed' });

  const userId = await requireAdmin(req, res, sql);
  if (!userId) return;

  const { id, action } = req.body || {};
  if (!id || !ACTIONS.has(action)) return res.status(400).json({ error: 'invalid id/action' });

  try {
    const [product] = await sql`select * from products where id = ${id}`;
    if (!product) return res.status(404).json({ error: 'product not found' });

    if (action === 'publish') {
      const [variantCount] = await sql`select count(*) from product_variants where product_id = ${id}`;
      const [imageCount] = await sql`select count(*) from product_images where product_id = ${id}`;
      if (Number(variantCount.count) === 0) return res.status(400).json({ error: '請先新增至少一個款式選項' });
      if (Number(imageCount.count) === 0) return res.status(400).json({ error: '請先上傳至少一張商品照片' });
      const [defaultColorImage] = await sql`select 1 from product_images where product_id = ${id} and color = ${product.default_color} limit 1`;
      if (!defaultColorImage) return res.status(400).json({ error: '預設顏色必須至少有一張商品照片' });

      const firstPublishedAt = product.first_published_at || new Date().toISOString();
      await sql`update products set is_published = true, first_published_at = ${firstPublishedAt}, updated_at = now() where id = ${id}`;
    } else if (action === 'unpublish') {
      await sql`update products set is_published = false, updated_at = now() where id = ${id}`;
    } else if (action === 'delete') {
      await sql`delete from products where id = ${id}`;
    } else if (action === 'duplicate') {
      const [copy] = await sql`
        insert into products (category, name_zh, name_en, description_zh, description_en, default_color, is_published, created_by_id)
        values (${product.category}, ${product.name_zh + ' (複製)'}, ${product.name_en}, ${product.description_zh}, ${product.description_en},
                ${product.default_color}, false, ${userId})
        returning *
      `;
      const variants = await sql`select * from product_variants where product_id = ${id}`;
      for (const v of variants) {
        await sql`insert into product_variants (product_id, gold, carat, weight_chin, manual_price_twd) values (${copy.id}, ${v.gold}, ${v.carat}, ${v.weight_chin}, ${v.manual_price_twd})`;
      }
      const images = await sql`select * from product_images where product_id = ${id} order by sort_order`;
      for (const img of images) {
        await sql`insert into product_images (product_id, color, file_path, sort_order) values (${copy.id}, ${img.color}, ${img.file_path}, ${img.sort_order})`;
      }
      await logAdminAction(sql, { action: 'product_duplicated', detail: { fromId: id, toId: copy.id } });
      return res.status(200).json({ ok: true, product: copy });
    }

    await logAdminAction(sql, { action: `product_${action}`, detail: { productId: id, nameZh: product.name_zh } });
    res.status(200).json({ ok: true });
  } catch (err) {
    console.error('[admin/product-action]', err);
    res.status(500).json({ error: '操作失敗' });
  }
};
