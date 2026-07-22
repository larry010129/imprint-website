/* Client-side shop pricing — no API. Mirrors backend/lib/pricing.js for the calculator. */
(function (global) {
  'use strict';

  var DIAMOND_PRICE = {
    '0.1': 24000, '0.2': 48000, '0.3': 79000, '0.5': 98000,
    '0.6': 113000, '0.7': 133000, '0.8': 159000, '0.9': 200000,
    '1.0': 250000, '1': 250000, '1.5': 380000, '2.0': 700000, '2': 700000,
    '3.0': 990000, '3': 990000,
  };

  var COLORED_SINGLE_DIAMOND_PRICE = {
    '0.3': 102000, '0.5': 127000, '0.6': 147000, '0.7': 172000,
    '0.8': 206000, '0.9': 260000, '1.0': 325000, '1': 325000,
    '1.5': 494000, '2.0': 910000, '2': 910000, '3.0': 1287000, '3': 1287000,
  };

  var WHITE_MULTI_DIAMOND_PRICE = {
    '0.1': { 2: 45600, 3: 61200, 4: 81000 },
    '0.2': { 2: 86400, 3: 122400, 4: 162000 },
    '0.3': { 2: 142200, 3: 189600, 4: 250000 },
  };

  var COLORED_MULTI_DIAMOND_PRICE = {
    '0.3': { 2: 173400, 3: 244800, 4: 322300 },
  };

  var MULTI_STONE_ABOVE_03_MULTIPLIER = { 2: 0.85, 3: 0.80, 4: 0.75 };
  var VALID_FANCY_COLORS = { yellow: 1, pink: 1, blue: 1 };
  var VALID_STONE_COUNTS = { 2: 1, 3: 1, 4: 1 };
  var STONE_COUNT_CATEGORIES = { earring: 1 };
  var DEFAULT_STONE_COUNT_BY_CATEGORY = { earring: 2, ring: 2, pendant: 2, diamond: 1 };

  var WAX_TO_METAL_CHIN = {
    '9k': 11.5, '14k': 14, '18k': 16, pt950: 24, s925: 11,
  };

  var PURITY_MULTIPLIER = {
    '9k': 0.50, '14k': 0.75, '18k': 0.85, pt950: 1.10, s925: 0.925,
  };
  var METAL_SYMBOL = {
    '9k': 'XAU', '14k': 'XAU', '18k': 'XAU', pt950: 'XPT', s925: 'XAG',
  };
  /** Universal 金工費 (flat NT$, not taxed). Same for every category. */
  var LABOR_FEE_TWD = 5000;
  var TAX_RATE = 0.05;
  var CHIN_TO_GRAMS = 3.75;
  var CHAIN_REFERENCE_LENGTH_CM = 45;
  var BRACELET_REFERENCE_LENGTH_CM = 18;
  var FANCY_MIN_CARAT = 0.3;
  var NON_ROUND_SHAPE_SURCHARGE = 0.10;

  var FALLBACK_METAL_RAW = { XAU: 4300, XPT: 1050, XAG: 30 };

  // Per-purity TWD/gram rates from the live BOT scrape (/api/bot-gold's
  // alloyRates), set once fetched. Falls back to FALLBACK_METAL_RAW until then.
  var liveAlloyRates = null;

  function setLiveGoldRates(rates) {
    liveAlloyRates = rates && typeof rates === 'object' ? rates : null;
  }

  function perGramFor(gold) {
    if (liveAlloyRates && liveAlloyRates[gold] != null) return liveAlloyRates[gold];
    return FALLBACK_METAL_RAW[METAL_SYMBOL[gold]] * PURITY_MULTIPLIER[gold];
  }

  function isShapeCaratAllowed(carat, diamondShape) {
    if ((diamondShape || 'round') === 'round') return true;
    return parseFloat(carat) >= FANCY_MIN_CARAT;
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
      var row = table['0.3'] || {};
      var multiplier = MULTI_STONE_ABOVE_03_MULTIPLIER[stoneCount];
      var baseRow = row[stoneCount];
      return baseRow != null && multiplier ? Math.round(baseRow * multiplier) : null;
    }
    return (table[tier] || {})[stoneCount] ?? null;
  }

  function computeDiamondListPrice(caratKey, opts) {
    opts = opts || {};
    var category = opts.category;
    if (!caratKey || category === 'chain') return null;
    var caratNum = parseFloat(caratKey);
    if (Number.isNaN(caratNum)) return null;
    var stoneCount = opts.stoneCount;
    // Memorial loose diamonds: multi-stone package only when qty ≥ 2
    var multiStone = !!STONE_COUNT_CATEGORIES[category]
      || (category === 'diamond' && VALID_STONE_COUNTS[stoneCount]);
    if (!isShapeCaratAllowed(caratNum, opts.diamondShape)) return null;

    var base = null;
    var diamondKind = opts.diamondKind || 'white';
    var fancyColor = opts.fancyColor;
    var diamondShape = opts.diamondShape || 'round';

    if (diamondKind === 'white') {
      if (multiStone) {
        var count = VALID_STONE_COUNTS[stoneCount] ? stoneCount : (DEFAULT_STONE_COUNT_BY_CATEGORY[category] || 2);
        var tier = multiStoneTier(caratKey, caratNum, WHITE_MULTI_DIAMOND_PRICE);
        if (tier == null) return null;
        base = resolveMultiPrice(WHITE_MULTI_DIAMOND_PRICE, tier, count);
      } else {
        base = DIAMOND_PRICE[caratKey] ?? null;
      }
    } else if (diamondKind === 'fancy') {
      if (!VALID_FANCY_COLORS[fancyColor]) return null;
      if (caratNum < FANCY_MIN_CARAT) return null;
      if (multiStone) {
        var count2 = VALID_STONE_COUNTS[stoneCount] ? stoneCount : (DEFAULT_STONE_COUNT_BY_CATEGORY[category] || 2);
        var tier2 = multiStoneTier(caratKey, caratNum, COLORED_MULTI_DIAMOND_PRICE);
        if (tier2 == null) return null;
        base = resolveMultiPrice(COLORED_MULTI_DIAMOND_PRICE, tier2, count2);
      } else {
        base = COLORED_SINGLE_DIAMOND_PRICE[caratKey]
          ?? (caratKey === '1.0' ? COLORED_SINGLE_DIAMOND_PRICE['1'] : null)
          ?? null;
      }
    } else {
      return null;
    }

    if (base == null) return null;
    var surcharge = shapeSurchargeRate(diamondShape);
    return surcharge ? Math.round(base * (1 + surcharge)) : base;
  }

  function getPerGramPrices() {
    var perGram = {};
    ['9k', '14k', '18k', 'pt950', 's925'].forEach(function (gold) {
      perGram[gold] = perGramFor(gold);
    });
    return perGram;
  }

  // catalog[category] arrays are static once loaded, so index them by id once
  // (keyed off the array reference) instead of re-scanning on every lookup.
  var productIndexCache = typeof WeakMap === 'function' ? new WeakMap() : null;

  function productIndexFor(list) {
    if (productIndexCache && productIndexCache.has(list)) return productIndexCache.get(list);
    var index = {};
    for (var i = 0; i < list.length; i++) {
      index[String(list[i].id)] = list[i];
    }
    if (productIndexCache) productIndexCache.set(list, index);
    return index;
  }

  function findProduct(catalog, category, productId) {
    var list = catalog[category] || [];
    return productIndexFor(list)[String(productId)] || null;
  }

  function waxToMetalChin(waxChin, gold) {
    var factor = WAX_TO_METAL_CHIN[gold];
    if (factor == null) throw new Error('unknown gold: ' + gold);
    return waxChin * factor;
  }

  function lookupWeight(product, category, gold, carat, lengthCm) {
    var wax = product.weights && product.weights[gold] && product.weights[gold][carat];
    if (wax == null) throw new Error('no weight');
    var weight = waxToMetalChin(Number(wax), gold);
    if (category === 'chain' && lengthCm != null) weight *= Number(lengthCm) / CHAIN_REFERENCE_LENGTH_CM;
    else if (category === 'bracelet' && lengthCm != null) weight *= Number(lengthCm) / BRACELET_REFERENCE_LENGTH_CM;
    return weight;
  }

  function perChinFor(gold) {
    return perGramFor(gold) * CHIN_TO_GRAMS;
  }

  function metalPreTax(gold, weightChin) {
    var perChin = perChinFor(gold);
    return { amount: perChin * weightChin, perGram: perGramFor(gold) };
  }

  function computeChainAddon(catalog, chainProductId, chainGold, chainLengthCm) {
    var chainProduct = findProduct(catalog, 'chain', chainProductId);
    if (!chainProduct) throw new Error('invalid chain');
    var weightChin = lookupWeight(chainProduct, 'chain', chainGold, '3fen', chainLengthCm);
    var weightGrams = weightChin * CHIN_TO_GRAMS;
    var manual = chainProduct.manualPrices && chainProduct.manualPrices[chainGold]
      && chainProduct.manualPrices[chainGold]['3fen'];
    if (manual != null) return { chainPreTax: Number(manual), chainWeightChin: weightChin };
    // 搭配鏈條 = metal only; standalone chain still gets LABOR_FEE_TWD in computeOrderPricing
    var metal = metalPreTax(chainGold, weightChin);
    return { chainPreTax: metal.amount, chainWeightChin: weightChin };
  }

  function computeOrderPricing(data, catalog) {
    var category = data.category;
    var carat = data.carat;
    var gold = data.gold;
    var productId = data.type;
    var lengthCm = data.lengthCm;
    var diamondKind = data.diamondKind || 'white';
    var fancyColor = data.fancyColor;
    var stoneCount = data.stoneCount;
    var diamondShape = data.diamondShape || 'round';
    var includeChain = data.includeChain;
    var chainProductId = data.chainProductId;
    var chainGold = data.chainGold;
    var chainLength = data.chainLength;

    if (!category || !carat || !productId) return { ready: false };
    if (category !== 'diamond' && !gold) return { ready: false };
    if ((category === 'chain' || category === 'bracelet') && lengthCm == null) return { ready: false };

    var product = findProduct(catalog, category, productId);
    if (!product) return { ready: false, error: 'product not available' };

    // Diamonds-only memorial series: list price only (no metal / labor)
    if (category === 'diamond') {
      var looseDiamond = computeDiamondListPrice(carat, {
        diamondKind: diamondKind,
        fancyColor: fancyColor,
        stoneCount: stoneCount,
        diamondShape: diamondShape,
        category: category,
      });
      if (looseDiamond == null) return { ready: false };
      return {
        ready: true,
        manualOverride: false,
        diamondPrice: looseDiamond,
        taijinPrice: 0,
        laborPrice: 0,
        metalworkPrice: 0,
        chainPrice: null,
        total: Math.round(looseDiamond),
      };
    }

    var manual = product.manualPrices && product.manualPrices[gold] && product.manualPrices[gold][carat];
    if (manual != null) {
      return { ready: true, total: Number(manual), manualOverride: true };
    }

    var weightChin;
    try {
      weightChin = lookupWeight(product, category, gold, carat, lengthCm);
    } catch (e) {
      return { ready: false, error: 'product not available' };
    }

    var weightGrams = weightChin * CHIN_TO_GRAMS;
    var laborPreTax = LABOR_FEE_TWD;
    var metal = metalPreTax(gold, weightChin);
    var taijinDisplay = Math.round(metal.amount * (1 + TAX_RATE));
    // Labor is flat NT$ — not taxed. Tax only on metal (and 搭配鏈條 metal).
    var laborDisplay = laborPreTax;

    var diamondPrice = null;
    if (category !== 'chain') {
      diamondPrice = computeDiamondListPrice(carat, {
        diamondKind: diamondKind,
        fancyColor: fancyColor,
        stoneCount: stoneCount,
        diamondShape: diamondShape,
        category: category,
      });
      if (diamondPrice == null) return { ready: false };
    }

    var total = (diamondPrice || 0) + taijinDisplay + laborDisplay;
    var chainDisplay = null;

    if (category === 'pendant' && includeChain && chainProductId && chainGold && chainLength) {
      try {
        var addon = computeChainAddon(catalog, chainProductId, chainGold, chainLength);
        chainDisplay = Math.round(addon.chainPreTax * (1 + TAX_RATE));
        total += chainDisplay;
      } catch (e) {
        return { ready: false, error: 'invalid chain option' };
      }
    }

    return {
      ready: true,
      manualOverride: false,
      diamondPrice: diamondPrice,
      taijinPrice: taijinDisplay,
      laborPrice: laborDisplay,
      metalworkPrice: taijinDisplay + laborDisplay,
      chainPrice: chainDisplay,
      total: Math.round(total),
    };
  }

  function pricesPayload() {
    return {
      diamond: {
        '0.1': DIAMOND_PRICE['0.1'],
        '0.3': DIAMOND_PRICE['0.3'],
        '0.5': DIAMOND_PRICE['0.5'],
        '1.0': DIAMOND_PRICE['1.0'],
      },
      perGram: getPerGramPrices(),
      laborFeeTwd: LABOR_FEE_TWD,
      chinToGrams: CHIN_TO_GRAMS,
      taxRate: TAX_RATE,
      waxToMetalChin: WAX_TO_METAL_CHIN,
      ringSizeMin: 5,
      ringSizeMax: 18,
      ringSizeReference: {
        7: { diameter_cm: 1.47, circumference_cm: 4.46, jp: '6', us: '4', eu: '46' },
        8: { diameter_cm: 1.52, circumference_cm: 4.77, jp: '7', us: '4.5', eu: '48' },
        9: { diameter_cm: 1.57, circumference_cm: 4.93, jp: '9', us: '5', eu: '49' },
        10: { diameter_cm: 1.62, circumference_cm: 5.09, jp: '10', us: '5.5', eu: '51' },
        11: { diameter_cm: 1.67, circumference_cm: 5.24, jp: '12', us: '6.5', eu: '52' },
        12: { diameter_cm: 1.72, circumference_cm: 5.40, jp: '13', us: '7', eu: '54' },
        13: { diameter_cm: 1.77, circumference_cm: 5.56, jp: '15', us: '7.5', eu: '56' },
        14: { diameter_cm: 1.82, circumference_cm: 5.71, jp: '16', us: '8', eu: '57' },
        15: { diameter_cm: 1.88, circumference_cm: 5.90, jp: '18', us: '9', eu: '59' },
        16: { diameter_cm: 1.92, circumference_cm: 6.03, jp: '19', us: '9.5', eu: '60' },
        17: { diameter_cm: 1.98, circumference_cm: 6.22, jp: '21', us: '10', eu: '62' },
        18: { diameter_cm: 2.03, circumference_cm: 6.37, jp: '22', us: '10.5', eu: '64' },
      },
      diamondOptions: {
        kinds: [
          { id: 'white', labelZh: '白鑽', labelEn: 'White' },
          { id: 'fancy', labelZh: '彩鑽', labelEn: 'Fancy Color' },
        ],
        diamondColors: [
          { id: 'white', kind: 'white', labelZh: '白鑽', labelEn: 'White', swatch: '#e8e8e8', image: 'diamonds/colors/white.png' },
          { id: 'yellow', kind: 'fancy', labelZh: '黃鑽', labelEn: 'Yellow', swatch: '#e6c200', image: 'diamonds/colors/yellow.png' },
          { id: 'blue', kind: 'fancy', labelZh: '藍鑽', labelEn: 'Blue', swatch: '#7ec8e3', image: 'diamonds/colors/blue.png' },
          { id: 'pink', kind: 'fancy', labelZh: '粉鑽', labelEn: 'Pink', swatch: '#f4a6c8', image: 'diamonds/colors/pink.png' },
        ],
        fancyColors: [
          { id: 'yellow', kind: 'fancy', labelZh: '黃鑽', labelEn: 'Yellow', swatch: '#e6c200', image: 'diamonds/colors/yellow.png' },
          { id: 'blue', kind: 'fancy', labelZh: '藍鑽', labelEn: 'Blue', swatch: '#7ec8e3', image: 'diamonds/colors/blue.png' },
          { id: 'pink', kind: 'fancy', labelZh: '粉鑽', labelEn: 'Pink', swatch: '#f4a6c8', image: 'diamonds/colors/pink.png' },
        ],
        matrixShapes: [
          { id: 'round', labelZh: '圓形', labelEn: 'Round' },
          { id: 'marquise', labelZh: '馬眼型', labelEn: 'Marquise' },
          { id: 'oval', labelZh: '橢圓形', labelEn: 'Oval' },
          { id: 'princess', labelZh: '公主方', labelEn: 'Princess' },
          { id: 'trilliant', labelZh: '三角形', labelEn: 'Trilliant' },
          { id: 'emerald', labelZh: '祖母綠形', labelEn: 'Emerald' },
          { id: 'heart', labelZh: '心形', labelEn: 'Heart' },
          { id: 'radiant', labelZh: '雷地恩形', labelEn: 'Radiant' },
          { id: 'pear', labelZh: '梨形', labelEn: 'Pear' },
          { id: 'cushion', labelZh: '枕形', labelEn: 'Cushion' },
        ],
        shapes: [
          { id: 'round', labelZh: '圓形明亮式', labelEn: 'Round', image: 'diamonds/shapes/round.svg' },
          { id: 'other', labelZh: '其它形狀', labelEn: 'Other (+10%)', image: 'diamonds/shapes/round.svg' },
        ],
        stoneCounts: [1, 2, 3, 4],
        stoneCountCategories: ['earring'],
        fancyMinCarat: '0.3',
        nonRoundShapeMinCarat: '0.3',
        nonRoundShapeSurcharge: 0.10,
        defaultStoneCountByCategory: DEFAULT_STONE_COUNT_BY_CATEGORY,
      },
    };
  }

  global.ShopPricingLocal = {
    computeOrderPricing: computeOrderPricing,
    pricesPayload: pricesPayload,
    setLiveGoldRates: setLiveGoldRates,
    WAX_TO_METAL_CHIN: WAX_TO_METAL_CHIN,
    waxToMetalChin: waxToMetalChin,
    LABOR_FEE_TWD: LABOR_FEE_TWD,
  };
})(window);
