const { sql } = require('../lib/db');
const { applyCors } = require('../lib/cors');

module.exports = async function handler(req, res) {
  if (applyCors(req, res)) return;
  if (req.method !== 'POST') return res.status(405).json({ error: 'method not allowed' });

  const { name, phone, email, message, sourcePage } = req.body || {};
  if (!name || !phone || !message) return res.status(400).json({ error: '請填寫姓名、電話與您的需求' });

  try {
    await sql`
      insert into contact_messages (name, phone, email, message, source_page)
      values (${name}, ${phone}, ${email || null}, ${message}, ${sourcePage || null})
    `;
    res.status(200).json({ ok: true });
  } catch (err) {
    console.error('[contact]', err);
    res.status(500).json({ error: '送出失敗，請稍後再試' });
  }
};
