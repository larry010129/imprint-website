/* POST {id, status, statusNote}: update an order's progress (admin.html). */
const { sql } = require('../../lib/db');
const { requireAdmin } = require('../../lib/auth');
const { applyCors } = require('../../lib/cors');

module.exports = async function handler(req, res) {
  if (applyCors(req, res)) return;
  if (req.method !== 'POST') return res.status(405).json({ error: 'method not allowed' });

  const userId = await requireAdmin(req, res, sql);
  if (!userId) return;

  const { id, status, statusNote } = req.body || {};
  if (!id || !status) return res.status(400).json({ error: 'missing id/status' });

  try {
    await sql`
      update orders set status = ${status}, status_note = ${statusNote || null}, updated_at = now()
      where id = ${id}
    `;
    res.status(200).json({ ok: true });
  } catch (err) {
    console.error('[admin/order-update]', err);
    res.status(500).json({ error: '更新失敗' });
  }
};
