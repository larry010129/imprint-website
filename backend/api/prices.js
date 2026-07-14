/* GET: live metal + diamond pricing metadata for the shop frontend.
 * Ported from imprint-calculator /api/prices (routes.py). */
const { sql } = require('../lib/db');
const { applyCors } = require('../lib/cors');
const {
  DIAMOND_PRICE, LABOR_FEE, TAX_RATE, CHIN_TO_GRAMS,
  PURITY_MULTIPLIER, METAL_SYMBOL, getMetalPrices,
} = require('../lib/pricing');
const { diamondOptionsPayload } = require('../lib/diamond-options');
const { RING_SIZE_MIN, RING_SIZE_MAX, RING_SIZE_REFERENCE } = require('../lib/ring-sizes');

const VALID_GOLDS = ['9k', '14k', '18k', 'pt950', 's925'];
const SHOP_DIAMOND_CARATS = ['0.1', '0.3', '0.5', '1.0'];
const CATEGORY_DISPLAY_ORDER = ['pendant', 'ring', 'earring', 'bracelet', 'chain'];

module.exports = async function handler(req, res) {
  if (applyCors(req, res)) return;
  if (req.method !== 'GET') return res.status(405).json({ error: 'method not allowed' });

  try {
    const raw = await getMetalPrices(sql);
    const perGram = {};
    for (const gold of VALID_GOLDS) {
      const symbol = METAL_SYMBOL[gold];
      if (raw[symbol] != null) perGram[gold] = raw[symbol] * PURITY_MULTIPLIER[gold];
    }

    const [cache] = await sql`
      select bot_posted_at, bank_sell from gold_price_cache where id = 1
    `;

    res.status(200).json({
      diamond: DIAMOND_PRICE,
      shopDiamondCarats: SHOP_DIAMOND_CARATS,
      perGram,
      source: 'bot',
      lastUpdated: cache ? cache.bot_posted_at : null,
      bankSell: cache ? cache.bank_sell : null,
      laborFee: LABOR_FEE,
      chinToGrams: CHIN_TO_GRAMS,
      taxRate: TAX_RATE,
      ringSizeMin: RING_SIZE_MIN,
      ringSizeMax: RING_SIZE_MAX,
      ringSizeReference: RING_SIZE_REFERENCE,
      diamondOptions: diamondOptionsPayload(),
      categoryOrder: CATEGORY_DISPLAY_ORDER,
    });
  } catch (err) {
    console.error('[prices]', err);
    res.status(500).json({ error: '讀取價格失敗' });
  }
};
