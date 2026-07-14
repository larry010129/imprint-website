/* GET: the logged-in user's saved favorite configurations.
 * POST: save a shop configuration as a favorite (deduped by identical config).
 */
const { sql } = require('../lib/db');
const { getUserId } = require('../lib/auth');
const { applyCors } = require('../lib/cors');
const { validateSubmissionFields } = require('../lib/validation');

module.exports = async function handler(req, res) {
  if (applyCors(req, res)) return;

  const userId = getUserId(req);
  if (!userId) return res.status(401).json({ error: 'not signed in' });

  if (req.method === 'GET') {
    try {
      const items = await sql`select * from favorite_items where user_id = ${userId} order by created_at desc`;
      return res.status(200).json({ items });
    } catch (err) {
      console.error('[favorites GET]', err);
      return res.status(500).json({ error: '載入最愛失敗' });
    }
  }

  if (req.method === 'POST') {
    const { cleaned, error } = validateSubmissionFields(req.body);
    if (error) return res.status(400).json({ error });

    try {
      const [product] = await sql`select id, name_zh, is_published from products where id = ${cleaned.type}`;
      if (!product || !product.is_published) return res.status(400).json({ error: 'product not available' });

      const canonical = JSON.stringify(cleaned, Object.keys(cleaned).sort());
      const [existing] = await sql`select * from favorite_items where user_id = ${userId} and config_json = ${canonical}::jsonb`;
      if (existing) return res.status(200).json({ item: existing });

      const [item] = await sql`
        insert into favorite_items (user_id, product_id, category, style_type, config_json, summary_zh)
        values (${userId}, ${product.id}, ${cleaned.category}, ${cleaned.type}, ${canonical}::jsonb, ${product.name_zh})
        returning *
      `;
      res.status(200).json({ item });
    } catch (err) {
      console.error('[favorites POST]', err);
      res.status(500).json({ error: '加入最愛失敗' });
    }
    return;
  }

  res.status(405).json({ error: 'method not allowed' });
};
