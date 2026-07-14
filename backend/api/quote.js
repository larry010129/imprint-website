/* POST: real-time price quote for a shop configuration, using actual
 * product-variant gold weight + live gold price (the "臺金" calculation) —
 * not the flat mounting-fee estimate the static pages' js/pricing-config.js
 * uses. This is the server-authoritative price; cart/checkout/orders all
 * recompute through this same path rather than trusting client-sent totals.
 */
const { sql } = require('../lib/db');
const { applyCors } = require('../lib/cors');
const { validateSubmissionFields } = require('../lib/validation');
const { computeOrderPricing } = require('../lib/pricing');

module.exports = async function handler(req, res) {
  if (applyCors(req, res)) return;
  if (req.method !== 'POST') return res.status(405).json({ error: 'method not allowed' });

  const { cleaned, error } = validateSubmissionFields(req.body, { partial: !!req.body?.partial });
  if (error) return res.status(200).json({ ready: false, error });

  try {
    const pricing = await computeOrderPricing(sql, cleaned, { requirePublished: true });
    if (!pricing.ready) return res.status(200).json({ ready: false, error: pricing.error || null });

    if (pricing.manualOverride) {
      return res.status(200).json({ ready: true, manualOverride: true, total: pricing.total });
    }

    res.status(200).json({
      ready: true,
      manualOverride: false,
      diamondPrice: pricing.diamondPrice,
      taijinPrice: pricing.taijinDisplay,
      laborPrice: pricing.laborDisplay,
      chainPrice: pricing.chainDisplay,
      total: pricing.total,
    });
  } catch (err) {
    console.error('[quote]', err);
    res.status(500).json({ ready: false, error: '試算失敗' });
  }
};
