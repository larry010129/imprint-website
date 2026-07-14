const { sql } = require('../lib/db');
const { applyCors } = require('../lib/cors');

module.exports = async function handler(req, res) {
  if (applyCors(req, res)) return;
  if (req.method !== 'POST') return res.status(405).json({ error: 'method not allowed' });

  const { name, phone, email, series, productType, carat, color, shape, metal, quantity, estimatedPrice } = req.body || {};
  if (!name || !phone) return res.status(400).json({ error: '請填寫姓名與電話' });

  try {
    await sql`
      insert into quote_requests
        (name, phone, email, series, product_type, carat, color, shape, metal, quantity, estimated_price)
      values
        (${name}, ${phone}, ${email || null}, ${series || null}, ${productType || null},
         ${carat || null}, ${color || null}, ${shape || null}, ${metal || null},
         ${quantity || 1}, ${estimatedPrice != null ? estimatedPrice : null})
    `;
    res.status(200).json({ ok: true });
  } catch (err) {
    console.error('[quote-request]', err);
    res.status(500).json({ error: '送出失敗，請稍後再試' });
  }
};
