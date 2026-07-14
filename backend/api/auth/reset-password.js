const { sql } = require('../../lib/db');
const { hashPassword } = require('../../lib/auth');
const { applyCors } = require('../../lib/cors');

module.exports = async function handler(req, res) {
  if (applyCors(req, res)) return;
  if (req.method !== 'POST') return res.status(405).json({ error: 'method not allowed' });

  const { token, newPassword } = req.body || {};
  if (!token || !newPassword) return res.status(400).json({ error: '缺少必要欄位' });
  if (String(newPassword).length < 6) return res.status(400).json({ error: '密碼至少需要 6 碼' });

  try {
    const [row] = await sql`
      select user_id, expires_at, used_at from password_reset_tokens where token = ${token}
    `;
    if (!row || row.used_at || new Date(row.expires_at) < new Date()) {
      return res.status(400).json({ error: '重設連結已失效，請重新申請' });
    }

    const passwordHash = await hashPassword(newPassword);
    await sql`update users set password_hash = ${passwordHash} where id = ${row.user_id}`;
    await sql`update password_reset_tokens set used_at = now() where token = ${token}`;

    res.status(200).json({ ok: true });
  } catch (err) {
    console.error('[reset-password]', err);
    res.status(500).json({ error: '重設失敗，請稍後再試' });
  }
};
