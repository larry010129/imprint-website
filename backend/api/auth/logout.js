const { clearSessionCookie } = require('../../lib/auth');
const { applyCors } = require('../../lib/cors');

module.exports = async function handler(req, res) {
  if (applyCors(req, res)) return;
  if (req.method !== 'POST') return res.status(405).json({ error: 'method not allowed' });
  clearSessionCookie(res);
  res.status(200).json({ ok: true });
};
