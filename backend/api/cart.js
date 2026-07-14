/* GET: the logged-in user's cart items.
 * POST: add a configured item to the cart (re-validates + re-prices server-side).
 */
const { sql } = require('../lib/db');
const { getUserId } = require('../lib/auth');
const { applyCors } = require('../lib/cors');
const { validateSubmissionFields } = require('../lib/validation');
const { computeOrderPricing } = require('../lib/pricing');

module.exports = async function handler(req, res) {
  if (applyCors(req, res)) return;

  const userId = getUserId(req);
  if (!userId) return res.status(401).json({ error: 'not signed in' });

  if (req.method === 'GET') {
    try {
      const items = await sql`select * from cart_items where user_id = ${userId} order by created_at asc`;
      return res.status(200).json({ items });
    } catch (err) {
      console.error('[cart GET]', err);
      return res.status(500).json({ error: '載入購物車失敗' });
    }
  }

  if (req.method === 'POST') {
    const { cleaned, error } = validateSubmissionFields(req.body);
    if (error) return res.status(400).json({ error });

    try {
      const pricing = await computeOrderPricing(sql, cleaned, { requirePublished: true });
      if (!pricing.ready) return res.status(400).json({ error: pricing.error || 'pricing error' });

      const [product] = pricing.variant
        ? await sql`select name_zh from products where id = ${pricing.variant.product_id}`
        : [null];
      const summary = product ? product.name_zh : `${cleaned.category} ${cleaned.type}`;

      const [item] = await sql`
        insert into cart_items (user_id, product_id, category, style_type, config_json, summary_zh, total_price)
        values (${userId}, ${pricing.variant ? pricing.variant.product_id : null}, ${cleaned.category}, ${cleaned.type},
                ${JSON.stringify(req.body)}::jsonb, ${summary}, ${pricing.total})
        returning *
      `;
      res.status(200).json({ item });
    } catch (err) {
      console.error('[cart POST]', err);
      res.status(500).json({ error: '加入購物車失敗' });
    }
    return;
  }

  res.status(405).json({ error: 'method not allowed' });
};
