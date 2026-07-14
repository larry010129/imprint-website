/* GET ?q=: list orders (admin.html 訂單與製作進度), optional free-text search
 * across order number/category/status/carat/metal/customer name/phone —
 * ported from imprint-calculator's order_search.py (apply_submission_search).
 * POST: create a new order, returns the generated order_number.
 */
const { sql } = require('../../lib/db');
const { requireAdmin } = require('../../lib/auth');
const { applyCors } = require('../../lib/cors');

module.exports = async function handler(req, res) {
  if (applyCors(req, res)) return;

  const userId = await requireAdmin(req, res, sql);
  if (!userId) return;

  if (req.method === 'GET') {
    const q = (req.query && req.query.q || '').trim();
    try {
      const orders = q
        ? await sql`
            select * from orders
            where order_number ilike ${'%' + q + '%'}
               or category ilike ${'%' + q + '%'}
               or status ilike ${'%' + q + '%'}
               or carat ilike ${'%' + q + '%'}
               or gold_purity ilike ${'%' + q + '%'}
               or color ilike ${'%' + q + '%'}
               or customer_name ilike ${'%' + q + '%'}
               or customer_phone ilike ${'%' + q + '%'}
               or series ilike ${'%' + q + '%'}
               or product_type ilike ${'%' + q + '%'}
            order by created_at desc limit 200
          `
        : await sql`select * from orders order by created_at desc limit 100`;
      return res.status(200).json({ orders });
    } catch (err) {
      console.error('[admin/orders GET]', err);
      return res.status(500).json({ error: '載入失敗' });
    }
  }

  if (req.method === 'POST') {
    const { customerName, customerPhone, customerEmail, series, productType } = req.body || {};
    if (!customerName || !customerPhone) {
      return res.status(400).json({ error: '請填寫客戶姓名與電話' });
    }
    try {
      const [order] = await sql`
        insert into orders (customer_name, customer_phone, customer_email, series, product_type)
        values (${customerName}, ${customerPhone}, ${customerEmail || null}, ${series || null}, ${productType || null})
        returning order_number
      `;
      return res.status(200).json({ orderNumber: order.order_number });
    } catch (err) {
      console.error('[admin/orders POST]', err);
      return res.status(500).json({ error: '建立失敗' });
    }
  }

  res.status(405).json({ error: 'method not allowed' });
};
