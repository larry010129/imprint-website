/* GET ?id=: one cart item with full pricing breakdown.
 * PUT/POST {id, ...config}: update a cart item's configuration + re-price.
 * DELETE ?id= or {id}: remove a cart item.
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

  const id = (req.query && req.query.id) || (req.body && req.body.id);
  if (!id) return res.status(400).json({ error: 'missing id' });

  const [item] = await sql`select * from cart_items where id = ${id} and user_id = ${userId}`;
  if (!item) return res.status(404).json({ error: 'not found' });

  if (req.method === 'GET') {
    const config = item.config_json;
    const { cleaned, error } = validateSubmissionFields(config);
    let breakdown = {};
    if (!error) {
      const pricing = await computeOrderPricing(sql, cleaned, { requirePublished: false });
      if (pricing.ready) {
        breakdown = pricing.manualOverride
          ? { total: pricing.total, manualOverride: true }
          : {
              diamondPrice: pricing.diamondPrice, taijinPrice: pricing.taijinDisplay,
              laborPrice: pricing.laborDisplay, chainPrice: pricing.chainDisplay,
              taxAmount: pricing.taxAmount, total: pricing.total,
            };
      }
    }
    return res.status(200).json({ item, breakdown, taxRate: 0.05 });
  }

  if (req.method === 'PUT' || req.method === 'POST') {
    const { cleaned, error } = validateSubmissionFields(req.body);
    if (error) return res.status(400).json({ error });

    try {
      const pricing = await computeOrderPricing(sql, cleaned, { requirePublished: true });
      if (!pricing.ready) return res.status(400).json({ error: pricing.error || 'pricing error' });

      const [product] = pricing.variant
        ? await sql`select name_zh from products where id = ${pricing.variant.product_id}`
        : [null];
      const summary = product ? product.name_zh : `${cleaned.category} ${cleaned.type}`;

      const [updated] = await sql`
        update cart_items set
          product_id = ${pricing.variant ? pricing.variant.product_id : null},
          category = ${cleaned.category}, style_type = ${cleaned.type},
          config_json = ${JSON.stringify(req.body)}::jsonb, summary_zh = ${summary}, total_price = ${pricing.total}
        where id = ${id} and user_id = ${userId}
        returning *
      `;
      return res.status(200).json({ item: updated });
    } catch (err) {
      console.error('[cart-item PUT]', err);
      return res.status(500).json({ error: '更新失敗' });
    }
  }

  if (req.method === 'DELETE') {
    await sql`delete from cart_items where id = ${id} and user_id = ${userId}`;
    return res.status(200).json({ ok: true });
  }

  res.status(405).json({ error: 'method not allowed' });
};
