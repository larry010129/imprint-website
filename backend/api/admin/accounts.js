/* GET: list all user accounts (admin.html 帳號管理). */
const { sql } = require('../../lib/db');
const { requireAdmin } = require('../../lib/auth');
const { applyCors } = require('../../lib/cors');

module.exports = async function handler(req, res) {
  if (applyCors(req, res)) return;
  if (req.method !== 'GET') return res.status(405).json({ error: 'method not allowed' });

  const userId = await requireAdmin(req, res, sql);
  if (!userId) return;

  try {
    const accounts = await sql`
      select u.id, u.email, u.is_active, u.last_login_at, u.created_at,
             p.full_name, p.phone, p.store_name,
             (sa.user_id is not null) as is_admin
      from users u
      left join profiles p on p.id = u.id
      left join staff_admins sa on sa.user_id = u.id
      order by u.created_at desc
    `;
    res.status(200).json({ accounts });
  } catch (err) {
    console.error('[admin/accounts]', err);
    res.status(500).json({ error: '載入失敗' });
  }
};
