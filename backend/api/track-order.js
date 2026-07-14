/* Public order lookup by order number + phone (no login needed).
 * Replaces the Supabase RPC `lookup_order`.
 */
const { sql } = require('../lib/db');
const { applyCors } = require('../lib/cors');

module.exports = async function handler(req, res) {
  if (applyCors(req, res)) return;
  if (req.method !== 'POST') return res.status(405).json({ error: 'method not allowed' });

  const { orderNumber, phone } = req.body || {};
  if (!orderNumber || !phone) return res.status(400).json({ error: '請輸入訂單編號與電話' });

  try {
    const rows = await sql`
      select order_number, series, product_type, status, status_note, updated_at
      from orders
      where order_number = ${String(orderNumber).trim()} and customer_phone = ${String(phone).trim()}
    `;
    res.status(200).json({ rows });
  } catch (err) {
    console.error('[track-order]', err);
    res.status(500).json({ error: '查詢失敗，請稍後再試' });
  }
};
