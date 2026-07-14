/* GET: merged contact_messages + quote_requests, newest first (admin.html 諮詢名單).
 * POST {type: 'message'|'quote', id}: mark that lead as handled.
 */
const { sql } = require('../../lib/db');
const { requireAdmin } = require('../../lib/auth');
const { applyCors } = require('../../lib/cors');

module.exports = async function handler(req, res) {
  if (applyCors(req, res)) return;

  const userId = await requireAdmin(req, res, sql);
  if (!userId) return;

  if (req.method === 'GET') {
    try {
      const [messages, quotes] = await Promise.all([
        sql`select * from contact_messages order by created_at desc limit 50`,
        sql`select * from quote_requests order by created_at desc limit 50`,
      ]);
      return res.status(200).json({ messages, quotes });
    } catch (err) {
      console.error('[admin/leads GET]', err);
      return res.status(500).json({ error: '載入失敗' });
    }
  }

  if (req.method === 'POST') {
    const { type, id } = req.body || {};
    if (!id || (type !== 'message' && type !== 'quote')) {
      return res.status(400).json({ error: 'invalid lead reference' });
    }
    try {
      if (type === 'message') {
        await sql`update contact_messages set status = 'replied' where id = ${id}`;
      } else {
        await sql`update quote_requests set status = 'contacted' where id = ${id}`;
      }
      return res.status(200).json({ ok: true });
    } catch (err) {
      console.error('[admin/leads POST]', err);
      return res.status(500).json({ error: '更新失敗' });
    }
  }

  res.status(405).json({ error: 'method not allowed' });
};
