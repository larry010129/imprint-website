/* POST {order: [productId, ...]}: sets sort_order to match array position. */
const { sql } = require('../../lib/db');
const { requireAdmin } = require('../../lib/auth');
const { applyCors } = require('../../lib/cors');

module.exports = async function handler(req, res) {
  if (applyCors(req, res)) return;
  if (req.method !== 'POST') return res.status(405).json({ error: 'method not allowed' });

  const userId = await requireAdmin(req, res, sql);
  if (!userId) return;

  const { order } = req.body || {};
  if (!Array.isArray(order)) return res.status(400).json({ error: 'order must be an array of product ids' });

  try {
    for (let i = 0; i < order.length; i++) {
      await sql`update products set sort_order = ${i} where id = ${order[i]}`;
    }
    res.status(200).json({ ok: true });
  } catch (err) {
    console.error('[admin/products-reorder]', err);
    res.status(500).json({ error: '排序失敗' });
  }
};
