/* DELETE ?id= or {id}: remove a favorite. */
const { sql } = require('../lib/db');
const { getUserId } = require('../lib/auth');
const { applyCors } = require('../lib/cors');

module.exports = async function handler(req, res) {
  if (applyCors(req, res)) return;
  if (req.method !== 'DELETE') return res.status(405).json({ error: 'method not allowed' });

  const userId = getUserId(req);
  if (!userId) return res.status(401).json({ error: 'not signed in' });

  const id = (req.query && req.query.id) || (req.body && req.body.id);
  if (!id) return res.status(400).json({ error: 'missing id' });

  await sql`delete from favorite_items where id = ${id} and user_id = ${userId}`;
  res.status(200).json({ ok: true });
};
