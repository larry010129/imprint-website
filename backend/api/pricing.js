/* GET: public, read pricing_settings.overrides (js/pricing-config.js).
 * POST: admin-only, save overrides ({overrides: {...}}) or reset ({reset: true}).
 */
const { sql } = require('../lib/db');
const { requireAdmin } = require('../lib/auth');
const { applyCors } = require('../lib/cors');

module.exports = async function handler(req, res) {
  if (applyCors(req, res)) return;

  if (req.method === 'GET') {
    try {
      const [row] = await sql`select overrides from pricing_settings where id = 1`;
      return res.status(200).json({ overrides: (row && row.overrides) || {} });
    } catch (err) {
      console.error('[pricing GET]', err);
      return res.status(500).json({ error: '讀取價格設定失敗' });
    }
  }

  if (req.method === 'POST') {
    const userId = await requireAdmin(req, res, sql);
    if (!userId) return; // requireAdmin already wrote the response

    const { overrides, reset } = req.body || {};
    const nextOverrides = reset ? {} : (overrides || {});

    try {
      await sql`
        update pricing_settings
        set overrides = ${JSON.stringify(nextOverrides)}::jsonb, updated_at = now()
        where id = 1
      `;
      return res.status(200).json({ ok: true });
    } catch (err) {
      console.error('[pricing POST]', err);
      return res.status(500).json({ error: '儲存失敗' });
    }
  }

  res.status(405).json({ error: 'method not allowed' });
};
