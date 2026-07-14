/* GET: the logged-in user's recent notifications (e.g. "your order was
 * removed by the shop"). POST {id}: mark one as read.
 */
const { sql } = require('../lib/db');
const { getUserId } = require('../lib/auth');
const { applyCors } = require('../lib/cors');

module.exports = async function handler(req, res) {
  if (applyCors(req, res)) return;

  const userId = getUserId(req);
  if (!userId) return res.status(401).json({ error: 'not signed in' });

  if (req.method === 'GET') {
    try {
      const items = await sql`
        select * from user_notifications where user_id = ${userId}
        order by created_at desc limit 20
      `;
      return res.status(200).json({ notifications: items });
    } catch (err) {
      console.error('[notifications GET]', err);
      return res.status(500).json({ error: '載入通知失敗' });
    }
  }

  if (req.method === 'POST') {
    const { id } = req.body || {};
    if (!id) return res.status(400).json({ error: 'missing id' });
    await sql`update user_notifications set is_read = true where id = ${id} and user_id = ${userId}`;
    return res.status(200).json({ ok: true });
  }

  res.status(405).json({ error: 'method not allowed' });
};
