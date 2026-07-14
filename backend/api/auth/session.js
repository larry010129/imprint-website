const { sql } = require('../../lib/db');
const { getUserId } = require('../../lib/auth');
const { applyCors } = require('../../lib/cors');

module.exports = async function handler(req, res) {
  if (applyCors(req, res)) return;
  if (req.method !== 'GET') return res.status(405).json({ error: 'method not allowed' });

  const userId = getUserId(req);
  if (!userId) return res.status(200).json({ user: null });

  try {
    const [user] = await sql`select id, email from users where id = ${userId}`;
    if (!user) return res.status(200).json({ user: null });

    const [profile] = await sql`select full_name, phone from profiles where id = ${userId}`;
    const [admin] = await sql`select user_id from staff_admins where user_id = ${userId}`;

    res.status(200).json({
      user: { id: user.id, email: user.email },
      profile: profile || null,
      isAdmin: !!admin,
    });
  } catch (err) {
    console.error('[session]', err);
    res.status(500).json({ error: 'session lookup failed' });
  }
};
