/* 銘印鑽石｜完整計價引擎 — JS 版本，邏輯移植自 imprint-calculator (Flask)：
 *   diamond_calculator/application/pricing.py
 *   diamond_calculator/application/diamond_options.py
 *   diamond_calculator/application/order_pricing.py
 *
 * 跟 js/pricing-config.js 的差異：這支檔案是「伺服器端、以資料庫真實克重計算」
 * 的完整版本(含金屬克重 × 即時金價 × 純度係數 + 工錢，即「臺金」計價)，
 * 是訂單/購物車/最愛送出時的權威計算依據 — 不能信任前端算出的金額。
 * js/pricing-config.js 是純前端試算(給訪客看數字用)，故意保留較簡化的
 * mounting 估算表，因為靜態商品頁沒有逐款真實克重資料。
 */

const DIAMOND_PRICE = {
  '0.1': 24000, '0.2': 48000, '0.3': 79000, '0.5': 98000,
  '0.6': 113000, '0.7': 133000, '0.8': 159000, '0.9': 200000,
  '1.0': 250000, '1': 250000, '1.5': 380000, '2.0': 700000, '2': 700000,
  '3.0': 990000, '3': 990000,
};

const COLORED_SINGLE_DIAMOND_PRICE = {
  '0.3': 102000, '0.5': 127000, '0.6': 147000, '0.7': 172000,
  '0.8': 206000, '0.9': 260000, '1.0': 325000, '1': 325000,
  '1.5': 494000, '2.0': 910000, '2': 910000, '3.0': 1287000, '3': 1287000,
};

const WHITE_MULTI_DIAMOND_PRICE = {
  '0.1': { 2: 45600, 3: 61200, 4: 81000 },
  '0.2': { 2: 86400, 3: 122400, 4: 162000 },
  '0.3': { 2: 142200, 3: 189600, 4: 250000 },
};

const COLORED_MULTI_DIAMOND_PRICE = {
  '0.3': { 2: 173400, 3: 244800, 4: 322300 },
};

const MULTI_STONE_ABOVE_03_MULTIPLIER = { 2: 0.85, 3: 0.80, 4: 0.75 };

const VALID_DIAMOND_KINDS = new Set(['white', 'fancy']);
const VALID_FANCY_COLORS = new Set(['yellow', 'pink', 'blue']);
const VALID_STONE_COUNTS = new Set([2, 3, 4]);

const FANCY_MIN_CARAT = 0.3;
const NON_ROUND_SHAPE_MIN_CARAT = 0.3;
const NON_ROUND_SHAPE_SURCHARGE = 0.10;

const DEFAULT_STONE_COUNT_BY_CATEGORY = { earring: 2, ring: 2, pendant: 2 };
const STONE_COUNT_CATEGORIES = new Set(['earring']);

const PURITY_MULTIPLIER = {
  '9k': 0.50, '14k': 0.75, '18k': 0.85, pt950: 1.10, s925: 0.925,
  '999': 0.999, pt: 1.0, silver925: 0.925,
};
const METAL_SYMBOL = {
  '9k': 'XAU', '14k': 'XAU', '18k': 'XAU', pt950: 'XPT', s925: 'XAG',
  '999': 'XAU', pt: 'XPT', silver925: 'XAG',
};
const LABOR_FEE = { pendant: 5000, ring: 5000, bracelet: 5000, earring: 5000, chain: 5000 };

const TAX_RATE = 0.05;
const CHIN_TO_GRAMS = 3.75;
const CHAIN_REFERENCE_LENGTH_CM = 45;
const BRACELET_REFERENCE_LENGTH_CM = 18;

function isShapeCaratAllowed(carat, diamondShape) {
  const shape = diamondShape || 'round';
  if (shape === 'round') return true;
  return carat >= FANCY_MIN_CARAT;
}

function shapeSurchargeRate(diamondShape) {
  return (diamondShape || 'round') === 'round' ? 0 : NON_ROUND_SHAPE_SURCHARGE;
}

function multiStoneTier(caratKey, caratNum, table) {
  if (table[caratKey] != null) return caratKey;
  if (caratNum > 0.3) return '0.3_plus';
  return null;
}

function resolveMultiPrice(table, tier, stoneCount) {
  if (tier === '0.3_plus') {
    const row = table['0.3'] || {};
    const multiplier = MULTI_STONE_ABOVE_03_MULTIPLIER[stoneCount];
    const baseRow = row[stoneCount];
    return baseRow != null && multiplier ? Math.round(baseRow * multiplier) : null;
  }
  return (table[tier] || {})[stoneCount] ?? null;
}

/** Diamond list price in TWD, or null if the combination can't be made. */
function computeDiamondListPrice(caratKey, {
  diamondKind = 'white', fancyColor = null, stoneCount = null, diamondShape = 'round', category = null,
} = {}) {
  if (!caratKey || category === 'chain') return null;
  const caratNum = parseFloat(caratKey);
  if (Number.isNaN(caratNum)) return null;

  const multiStone = STONE_COUNT_CATEGORIES.has(category);
  if (!isShapeCaratAllowed(caratNum, diamondShape)) return null;

  let base = null;

  if (diamondKind === 'white') {
    if (multiStone) {
      const count = VALID_STONE_COUNTS.has(stoneCount) ? stoneCount : (DEFAULT_STONE_COUNT_BY_CATEGORY[category] || 2);
      const tier = multiStoneTier(caratKey, caratNum, WHITE_MULTI_DIAMOND_PRICE);
      if (tier == null) return null;
      base = resolveMultiPrice(WHITE_MULTI_DIAMOND_PRICE, tier, count);
    } else {
      base = DIAMOND_PRICE[caratKey] ?? null;
    }
  } else if (diamondKind === 'fancy') {
    if (!VALID_FANCY_COLORS.has(fancyColor)) return null;
    if (caratNum < FANCY_MIN_CARAT) return null;
    if (multiStone) {
      const count = VALID_STONE_COUNTS.has(stoneCount) ? stoneCount : (DEFAULT_STONE_COUNT_BY_CATEGORY[category] || 2);
      const tier = multiStoneTier(caratKey, caratNum, COLORED_MULTI_DIAMOND_PRICE);
      if (tier == null) return null;
      base = resolveMultiPrice(COLORED_MULTI_DIAMOND_PRICE, tier, count);
    } else {
      base = COLORED_SINGLE_DIAMOND_PRICE[caratKey] ?? (caratKey === '1.0' ? COLORED_SINGLE_DIAMOND_PRICE['1'] : null) ?? null;
    }
  } else {
    return null;
  }

  if (base == null) return null;
  const surcharge = shapeSurchargeRate(diamondShape);
  return surcharge ? Math.round(base * (1 + surcharge)) : base;
}

/** {XAU,XPT,XAG} TWD/gram from gold_price_cache (falls back to a constant if empty). */
async function getMetalPrices(sql) {
  const [row] = await sql`select xau_per_gram, xpt_per_gram, xag_per_gram from gold_price_cache where id = 1`;
  if (!row) return { XAU: 4300, XPT: 1050, XAG: 30 };
  return { XAU: Number(row.xau_per_gram), XPT: Number(row.xpt_per_gram), XAG: Number(row.xag_per_gram) };
}

/** Looks up the ProductVariant row for a listing + config. Throws if not found. */
async function getProductVariant(sql, { category, productId, gold, carat, requirePublished = true }) {
  const rows = requirePublished
    ? await sql`
        select pv.* from product_variants pv
        join products p on p.id = pv.product_id
        where p.id = ${productId} and p.category = ${category}
          and pv.gold = ${gold} and pv.carat = ${carat} and p.is_published = true
      `
    : await sql`
        select pv.* from product_variants pv
        join products p on p.id = pv.product_id
        where p.id = ${productId} and p.category = ${category}
          and pv.gold = ${gold} and pv.carat = ${carat}
      `;
  const [variant] = rows;
  if (!variant) throw new Error('no matching product variant');
  return variant;
}

/** Weight in chin for a product's variant, scaled by length for chain/bracelet. */
async function lookupWeight(sql, { category, productId, gold, carat, lengthCm, requirePublished = true }) {
  const variant = await getProductVariant(sql, { category, productId, gold, carat, requirePublished });
  let weight = Number(variant.weight_chin);
  if (category === 'chain' && lengthCm != null) weight *= Number(lengthCm) / CHAIN_REFERENCE_LENGTH_CM;
  else if (category === 'bracelet' && lengthCm != null) weight *= Number(lengthCm) / BRACELET_REFERENCE_LENGTH_CM;
  return weight;
}

async function metalPreTax(sql, goldPrices, gold, weightGrams, category) {
  const perGram = goldPrices[METAL_SYMBOL[gold]] * PURITY_MULTIPLIER[gold];
  const multiplier = category === 'chain' ? 2 : 1;
  return { amount: perGram * weightGrams * multiplier, perGram };
}

/** Pre-tax chain total (metal×2 + labor) for a pendant's optional chain add-on. */
async function computeChainAddon(sql, goldPrices, { chainProductId, chainGold, chainLengthCm, requirePublished = true }) {
  const variant = await getProductVariant(sql, { category: 'chain', productId: chainProductId, gold: chainGold, carat: '3fen', requirePublished });
  const weightChin = await lookupWeight(sql, { category: 'chain', productId: chainProductId, gold: chainGold, carat: '3fen', lengthCm: chainLengthCm, requirePublished });
  const weightGrams = weightChin * CHIN_TO_GRAMS;

  let prTax;
  if (variant.manual_price_twd != null) {
    prTax = Number(variant.manual_price_twd);
  } else {
    const { amount } = await metalPreTax(sql, goldPrices, chainGold, weightGrams, 'chain');
    prTax = amount + (LABOR_FEE.chain || 5000);
  }
  return { chainPreTax: prTax, chainWeightChin: weightChin, chainVariant: variant };
}

/** Full order pricing — the single source of truth for quote/cart/checkout.
 * Mirrors imprint-calculator's compute_order_pricing() exactly: diamond price
 * is a tax-inclusive list price (untaxed here); only metal (taijin) + labor
 * get the 5% tax added at display time. Returns { ready, error, ...breakdown }.
 */
async function computeOrderPricing(sql, data, { requirePublished = true } = {}) {
  const {
    category, carat, gold, ringSize, lengthCm,
    diamondKind = 'white', fancyColor = null, stoneCount = null, diamondShape = 'round',
    includeChain = false, chainProductId = null, chainGold = null, chainLength = null,
  } = data;
  const productId = data.productId || data.type;

  if (!category || !carat || !gold || !productId) return { ready: false };
  if ((category === 'chain' || category === 'bracelet') && lengthCm == null) return { ready: false };

  let variant;
  let weightChin;
  try {
    variant = await getProductVariant(sql, { category, productId, gold, carat, requirePublished });
    weightChin = await lookupWeight(sql, { category, productId, gold, carat, lengthCm, requirePublished });
  } catch (err) {
    return { ready: false, error: 'product not available' };
  }

  const weightGrams = weightChin * CHIN_TO_GRAMS;
  const laborPreTax = LABOR_FEE[category] || 5000;

  if (variant.manual_price_twd != null) {
    const goldPrices = await getMetalPrices(sql);
    return {
      ready: true,
      total: Number(variant.manual_price_twd),
      manualOverride: true,
      goldRatePerGram: goldPrices[METAL_SYMBOL[gold]] * PURITY_MULTIPLIER[gold],
      priceSource: 'manual',
      variant, weightChin, weightGrams,
    };
  }

  const goldPrices = await getMetalPrices(sql);
  const { amount: taijinPreTax, perGram: rateUsed } = await metalPreTax(sql, goldPrices, gold, weightGrams, category);
  const taijinDisplay = Math.round(taijinPreTax * (1 + TAX_RATE));
  const laborDisplay = Math.round(laborPreTax * (1 + TAX_RATE));
  let taxAmount = (taijinDisplay - taijinPreTax) + (laborDisplay - laborPreTax);

  let diamondPrice = null;
  if (category !== 'chain') {
    diamondPrice = computeDiamondListPrice(carat, { diamondKind, fancyColor, stoneCount, diamondShape, category });
    if (diamondPrice == null) return { ready: false };
  }

  let total = (diamondPrice || 0) + taijinDisplay + laborDisplay;
  let chainDisplay = null;
  let chainPreTax = null;
  let chainVariant = null;
  let chainWeightChin = null;

  if (category === 'pendant' && includeChain && chainProductId && chainGold && chainLength) {
    try {
      const addon = await computeChainAddon(sql, goldPrices, { chainProductId, chainGold, chainLengthCm: chainLength, requirePublished });
      chainPreTax = addon.chainPreTax;
      chainWeightChin = addon.chainWeightChin;
      chainVariant = addon.chainVariant;
      chainDisplay = Math.round(chainPreTax * (1 + TAX_RATE));
      taxAmount += chainDisplay - chainPreTax;
      total += chainDisplay;
    } catch (err) {
      return { ready: false, error: 'invalid chain option' };
    }
  }

  return {
    ready: true,
    diamondPrice,
    taijinPreTax, taijinDisplay,
    laborPreTax, laborDisplay,
    chainDisplay, chainPreTax, chainVariant, chainWeightChin,
    taxAmount: Math.round(taxAmount),
    total: Math.round(total),
    goldRatePerGram: rateUsed,
    priceSource: 'bot',
    variant, weightChin, weightGrams,
    manualOverride: false,
  };
}

module.exports = {
  DIAMOND_PRICE, COLORED_SINGLE_DIAMOND_PRICE, WHITE_MULTI_DIAMOND_PRICE, COLORED_MULTI_DIAMOND_PRICE,
  MULTI_STONE_ABOVE_03_MULTIPLIER, PURITY_MULTIPLIER, METAL_SYMBOL, LABOR_FEE,
  TAX_RATE, CHIN_TO_GRAMS, CHAIN_REFERENCE_LENGTH_CM, BRACELET_REFERENCE_LENGTH_CM,
  computeDiamondListPrice, getMetalPrices, getProductVariant, lookupWeight,
  computeChainAddon, computeOrderPricing,
};
