/* GET: latest gold_price_cache + alloy rates for the gold-price page.
 * Legacy shape { price } is preserved; full payload adds quote + alloyRates. */
const { sql } = require('../lib/db');
const { applyCors } = require('../lib/cors');
const { buildGoldQuotePayload } = require('../lib/goldQuotePayload');

module.exports = async function handler(req, res) {
  if (applyCors(req, res)) return;
  if (req.method !== 'GET') return res.status(405).json({ error: 'method not allowed' });

  try {
    const [row] = await sql`
      select xau_per_gram, xpt_per_gram, xag_per_gram, bot_posted_at, source, source_url, fetched_at
      from gold_price_cache where id = 1
    `;
    const payload = buildGoldQuotePayload(row);
    res.status(200).json({
      price: row || null,
      ...payload,
    });
  } catch (err) {
    console.error('[gold-price]', err);
    res.status(500).json({ error: '讀取金價失敗' });
  }
};
