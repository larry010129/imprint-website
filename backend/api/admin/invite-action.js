/* POST {id, action: 'revoke'|'delete'} */
const { sql } = require('../../lib/db');
const { requireAdmin } = require('../../lib/auth');
const { applyCors } = require('../../lib/cors');
const { logAdminAction } = require('../../lib/audit');

module.exports = async function handler(req, res) {
  if (applyCors(req, res)) return;
  if (req.method !== 'POST') return res.status(405).json({ error: 'method not allowed' });

  const userId = await requireAdmin(req, res, sql);
  if (!userId) return;

  const { id, action } = req.body || {};
  if (!id || !['revoke', 'delete'].includes(action)) return res.status(400).json({ error: 'invalid id/action' });

  try {
    if (action === 'revoke') {
      await sql`update invite_codes set is_active = false where id = ${id}`;
    } else {
      await sql`delete from invite_codes where id = ${id}`;
    }
    await logAdminAction(sql, { action: `invite_${action}`, detail: { inviteId: id } });
    res.status(200).json({ ok: true });
  } catch (err) {
    console.error('[admin/invite-action]', err);
    res.status(500).json({ error: '操作失敗' });
  }
};
