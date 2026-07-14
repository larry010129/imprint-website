/* GET: list all invite codes.
 * POST {maxUses?, expiresInDays?, grantsAdmin?}: create a new invite code.
 */
const { sql } = require('../../lib/db');
const { requireAdmin } = require('../../lib/auth');
const { applyCors } = require('../../lib/cors');
const { generateInviteCode } = require('../../lib/invites');
const { logAdminAction } = require('../../lib/audit');

module.exports = async function handler(req, res) {
  if (applyCors(req, res)) return;

  const userId = await requireAdmin(req, res, sql);
  if (!userId) return;

  if (req.method === 'GET') {
    try {
      const invites = await sql`select * from invite_codes order by created_at desc`;
      return res.status(200).json({ invites });
    } catch (err) {
      console.error('[admin/invites GET]', err);
      return res.status(500).json({ error: '載入失敗' });
    }
  }

  if (req.method === 'POST') {
    const { maxUses, expiresInDays, grantsAdmin } = req.body || {};
    const code = generateInviteCode();
    const expiresAt = expiresInDays ? new Date(Date.now() + Number(expiresInDays) * 86400000).toISOString() : null;

    try {
      const [invite] = await sql`
        insert into invite_codes (code, created_by_id, max_uses, grants_admin, expires_at)
        values (${code}, ${userId}, ${maxUses || null}, ${!!grantsAdmin}, ${expiresAt})
        returning *
      `;
      await logAdminAction(sql, { action: 'invite_created', detail: { code, grantsAdmin: !!grantsAdmin } });
      res.status(200).json({ invite });
    } catch (err) {
      console.error('[admin/invites POST]', err);
      res.status(500).json({ error: '建立失敗' });
    }
    return;
  }

  res.status(405).json({ error: 'method not allowed' });
};
