/* POST {id, action: 'toggle-active'|'clear-lockout'|'delete'|'reset-password',
 *       newPassword?}: admin account management actions.
 */
const { sql } = require('../../lib/db');
const { requireAdmin, hashPassword } = require('../../lib/auth');
const { applyCors } = require('../../lib/cors');
const { clearLoginLockout } = require('../../lib/rateLimit');
const { logAdminAction } = require('../../lib/audit');

const ACTIONS = new Set(['toggle-active', 'clear-lockout', 'delete', 'reset-password']);

module.exports = async function handler(req, res) {
  if (applyCors(req, res)) return;
  if (req.method !== 'POST') return res.status(405).json({ error: 'method not allowed' });

  const adminId = await requireAdmin(req, res, sql);
  if (!adminId) return;

  const { id, action, newPassword } = req.body || {};
  if (!id || !ACTIONS.has(action)) return res.status(400).json({ error: 'invalid id/action' });

  try {
    const [user] = await sql`select id, email, is_active from users where id = ${id}`;
    if (!user) return res.status(404).json({ error: 'account not found' });

    if (action === 'toggle-active') {
      await sql`update users set is_active = ${!user.is_active} where id = ${id}`;
    } else if (action === 'clear-lockout') {
      await clearLoginLockout(sql, user.email);
    } else if (action === 'delete') {
      await sql`delete from users where id = ${id}`;
    } else if (action === 'reset-password') {
      if (!newPassword || String(newPassword).length < 6) {
        return res.status(400).json({ error: '密碼至少需要 6 碼' });
      }
      const hash = await hashPassword(newPassword);
      await sql`update users set password_hash = ${hash} where id = ${id}`;
    }

    await logAdminAction(sql, { action: `account_${action}`, detail: { userId: id, email: user.email } });
    res.status(200).json({ ok: true });
  } catch (err) {
    console.error('[admin/account-action]', err);
    res.status(500).json({ error: '操作失敗' });
  }
};
