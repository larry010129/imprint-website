/* POST {itemIds?: [id,...]}: converts cart items into real orders (re-prices
 * each server-side), then clears those cart items. Omit itemIds to check
 * out the entire cart.
 */
const { sql } = require('../lib/db');
const { getUserId } = require('../lib/auth');
const { applyCors } = require('../lib/cors');
const { validateSubmissionFields } = require('../lib/validation');
const { computeOrderPricing } = require('../lib/pricing');

module.exports = async function handler(req, res) {
  if (applyCors(req, res)) return;
  if (req.method !== 'POST') return res.status(405).json({ error: 'method not allowed' });

  const userId = getUserId(req);
  if (!userId) return res.status(401).json({ error: 'not signed in' });

  const { itemIds } = req.body || {};

  try {
    const items = itemIds && itemIds.length
      ? await sql`select * from cart_items where user_id = ${userId} and id = any(${itemIds}) order by created_at asc`
      : await sql`select * from cart_items where user_id = ${userId} order by created_at asc`;

    if (!items.length) return res.status(400).json({ error: 'cart is empty' });
    if (itemIds && items.length !== new Set(itemIds).size) return res.status(400).json({ error: 'invalid item selection' });

    const [profile] = await sql`select p.full_name, p.phone, u.email from profiles p join users u on u.id = p.id where p.id = ${userId}`;

    const createdOrderNumbers = [];
    for (const item of items) {
      const config = item.config_json;
      const { cleaned, error } = validateSubmissionFields(config);
      if (error) return res.status(400).json({ error });

      const pricing = await computeOrderPricing(sql, cleaned, { requirePublished: true });
      if (!pricing.ready) return res.status(400).json({ error: pricing.error || 'pricing error' });

      const [order] = await sql`
        insert into orders (
          user_id, product_id, customer_name, customer_phone, customer_email,
          category, carat, gold_purity, color, diamond_kind, fancy_color, stone_count, diamond_shape,
          weight_grams, ring_size, engraving_band, engraving_girdle,
          include_chain, chain_product_id, chain_gold, chain_color, chain_length_cm, chain_weight_chin, chain_total_twd,
          diamond_price_twd, taijin_price_twd, labor_price_twd, tax_amount_twd, total_price, gold_rate_per_gram, price_source
        ) values (
          ${userId}, ${pricing.variant ? pricing.variant.product_id : null},
          ${profile ? profile.full_name : ''}, ${profile ? profile.phone : ''}, ${profile ? profile.email : null},
          ${cleaned.category}, ${cleaned.carat}, ${cleaned.gold}, ${cleaned.color || null},
          ${cleaned.diamondKind || 'white'}, ${cleaned.fancyColor || null}, ${cleaned.stoneCount || null}, ${cleaned.diamondShape || 'round'},
          ${pricing.weightGrams}, ${cleaned.ringSize || null}, ${cleaned.engravingBand || null}, ${cleaned.engravingGirdle || null},
          ${!!cleaned.includeChain}, ${pricing.chainVariant ? pricing.chainVariant.product_id : null}, ${cleaned.chainGold || null},
          ${cleaned.chainColor || null}, ${cleaned.category === 'chain' || cleaned.category === 'bracelet' ? cleaned.lengthCm : (cleaned.chainLength || null)},
          ${pricing.chainWeightChin || null}, ${pricing.chainDisplay},
          ${pricing.diamondPrice}, ${pricing.taijinDisplay}, ${pricing.laborDisplay}, ${pricing.taxAmount}, ${pricing.total},
          ${pricing.goldRatePerGram}, ${pricing.priceSource}
        )
        returning order_number
      `;
      createdOrderNumbers.push(order.order_number);
    }

    const checkedOutIds = items.map((i) => i.id);
    await sql`delete from cart_items where id = any(${checkedOutIds})`;

    res.status(200).json({ ok: true, orderNumbers: createdOrderNumbers });
  } catch (err) {
    console.error('[cart-checkout]', err);
    res.status(500).json({ error: '結帳失敗，請稍後再試' });
  }
};
