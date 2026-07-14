/* GET: the logged-in customer's own orders (account.html). */
const { sql } = require('../lib/db');
const { getUserId } = require('../lib/auth');
const { applyCors } = require('../lib/cors');

module.exports = async function handler(req, res) {
  if (applyCors(req, res)) return;
  if (req.method !== 'GET') return res.status(405).json({ error: 'method not allowed' });

  const userId = getUserId(req);
  if (!userId) return res.status(401).json({ error: 'not signed in' });

  try {
    const orders = await sql`
      select order_number, product_type, series, status, status_note, created_at, updated_at
      from orders
      where user_id = ${userId}
      order by created_at desc
    `;
    res.status(200).json({ orders });
  } catch (err) {
    console.error('[orders]', err);
    res.status(500).json({ error: '載入訂單失敗' });
  }
};
