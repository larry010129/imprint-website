/* Client-side shop pricing — no API. Preview only; server uses app/pricing.py. */
// ponytail: thin calculator mirror of app/pricing.py; upgrade = drop local
// tables when calculator always hits /api quote for totals.
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

  /** price.html multi packages for 0.1/0.2/0.3; above 0.3 → unit×qty×discount. */
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
  var STONE_COUNT_CATEGORIES = {};
  var DEFAULT_STONE_COUNT_BY_CATEGORY = { ring: 2, pendant: 2, diamond: 1 };
  var EARRING_QUANTITY_MIN = 1;
  var EARRING_QUANTITY_MAX = 2;

  var WAX_TO_METAL_CHIN = {
    '9k': 11.5, '14k': 14, '18k': 16, pt950: 24, s925: 11,
  };

  var PURITY_MULTIPLIER = {
    '9k': 0.50, '14k': 0.75, '18k': 0.85, pt950: 1.10, s925: 0.925,
  };
  var METAL_SYMBOL = {
    '9k': 'XAU', '14k': 'XAU', '18k': 'XAU', pt950: 'XPT', s925: 'XAG',
  };
  /** Default flat labor; standalone chains use metal-specific labor below. */
  var LABOR_FEE_TWD = 5000;
  var CHAIN_LABOR_FEE_TWD = { s925: 500, other: 3000 };
  /** Per-category 品項加價 (NT$). Replaces base labor when > 0; from catalog /prices. */
  var categoryAddonPrices = {};
  var DEFAULT_ATTACHED_CHAIN_THICKNESS = '1.0mm';
  var CHAIN_WAX_WEIGHT_CHIN = {
    '1.0mm': {36: 0.014, 41: 0.016, 46: 0.018, 51: 0.020, 61: 0.024, 76: 0.030, 80: 0.032},
    '1.5mm': {36: 0.026, 41: 0.030, 46: 0.033, 51: 0.037, 61: 0.043, 76: 0.054, 80: 0.057},
    '2.0mm': {36: 0.040, 41: 0.046, 46: 0.051, 51: 0.056, 61: 0.066, 76: 0.083, 80: 0.087},
    '2.5mm': {36: 0.047, 41: 0.053, 46: 0.059, 51: 0.065, 61: 0.076, 76: 0.095, 80: 0.100},
    '3.0mm': {36: 0.052, 41: 0.060, 46: 0.066, 51: 0.074, 61: 0.086, 76: 0.110, 80: 0.120},
  };
  /** Excel 鍊條價格.xlsx O字鍊／抖圓鏈 wax table (slug douyuan). */
  var NECKLACE_TYPE_WAX = {
    douyuan: CHAIN_WAX_WEIGHT_CHIN,
  };

  function lengthWeightsForChainType(chainType) {
    var table = NECKLACE_TYPE_WAX[chainType || 'douyuan'] || NECKLACE_TYPE_WAX.douyuan;
    if (!table) return {};
    var out = {};
    Object.keys(table).forEach(function (thick) {
      out[thick] = Object.assign({}, table[thick]);
    });
    return out;
  }

  function chainWaxFromTypeCatalog(chainType, carat, lengthCm) {
    var table = NECKLACE_TYPE_WAX[chainType || 'douyuan'] || NECKLACE_TYPE_WAX.douyuan;
    if (!table) return null;
    var byLength = table[carat];
    if (!byLength) return null;
    var wax = byLength[parseInt(lengthCm, 10)];
    return wax == null ? null : Number(wax);
  }
  var TAX_RATE = 0.05;
  var CHIN_TO_GRAMS = 3.75;
  var BRACELET_REFERENCE_LENGTH_CM = 18;
  var FANCY_MIN_CARAT = 0.3;
  var NON_ROUND_SHAPE_SURCHARGE = 0.10;

  var FALLBACK_METAL_RAW = { XAU: 4300, XPT: 1050, XAG: 61 };

  // Per-purity TWD/gram rates from gold_price_cache (/api/bot-gold, same as orders).
  // Set once fetched; falls back to FALLBACK_METAL_RAW until then.
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

  function asStoneCount(value) {
    var n = parseInt(value, 10);
    return VALID_STONE_COUNTS[n] ? n : null;
  }

  function asEarringQuantity(value) {
    var n = parseInt(value, 10);
    if (Number.isNaN(n)) return EARRING_QUANTITY_MIN;
    return Math.max(EARRING_QUANTITY_MIN, Math.min(EARRING_QUANTITY_MAX, n));
  }

  /** Match app.pricing_overrides.canonical_carat ('0.10'→'0.1', '1'→'1.0'). */
  function canonicalCarat(key) {
    var n = parseFloat(key);
    if (Number.isNaN(n)) return null;
    if (n === Math.floor(n)) return String(Math.floor(n)) + '.0';
    return String(parseFloat(String(n)));
  }

  function lookupSinglePrice(table, caratKey) {
    var ck = canonicalCarat(caratKey) || caratKey;
    if (table[ck] != null) return table[ck];
    if (table[caratKey] != null) return table[caratKey];
    if (ck === '1.0' && table['1'] != null) return table['1'];
    return null;
  }

  function applyShapeSurcharge(amount, diamondShape) {
    var surcharge = shapeSurchargeRate(diamondShape);
    return surcharge ? Math.round(amount * (1 + surcharge)) : amount;
  }

  function computeDiamondListPrice(caratKey, opts) {
    opts = opts || {};
    var category = opts.category;
    if (!caratKey || category === 'chain') return null;
    var caratNum = parseFloat(caratKey);
    if (Number.isNaN(caratNum)) return null;
    // Earrings: single-stone list price; quantity applied in computeOrderPricing.
    var multiCount = category === 'diamond' ? asStoneCount(opts.stoneCount) : null;
    if (!isShapeCaratAllowed(caratNum, opts.diamondShape)) return null;

    var base = null;
    var diamondKind = opts.diamondKind || 'white';
    var fancyColor = opts.fancyColor;
    var diamondShape = opts.diamondShape || 'round';
    var ck = canonicalCarat(caratKey) || caratKey;

    if (diamondKind === 'white') {
      base = lookupSinglePrice(DIAMOND_PRICE, caratKey);
    } else if (diamondKind === 'fancy') {
      if (!VALID_FANCY_COLORS[fancyColor]) return null;
      base = lookupSinglePrice(COLORED_SINGLE_DIAMOND_PRICE, caratKey);
      // Fancy table starts at 0.3; jewelry may still offer 0.1/0.2 — fall back to white.
      if (base == null && category !== 'diamond') {
        base = lookupSinglePrice(DIAMOND_PRICE, caratKey);
      }
    } else {
      return null;
    }

    if (multiCount) {
      var multiTable = diamondKind === 'fancy'
        ? COLORED_MULTI_DIAMOND_PRICE
        : WHITE_MULTI_DIAMOND_PRICE;
      var row = multiTable[ck] || multiTable[caratKey];
      var packagePrice = row && row[multiCount] != null ? row[multiCount] : null;
      if (packagePrice != null) {
        return applyShapeSurcharge(packagePrice, diamondShape);
      }
      // price.html: above 0.30ct → 單顆價 × 顆數 × discount
      if (caratNum > FANCY_MIN_CARAT && base != null) {
        var discount = MULTI_STONE_ABOVE_03_MULTIPLIER[multiCount];
        if (!discount) return null;
        return applyShapeSurcharge(
          Math.round(base * multiCount * discount),
          diamondShape
        );
      }
      return null;
    }

    if (base == null) return null;
    return applyShapeSurcharge(base, diamondShape);
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

  function normalizeGold(gold) {
    var g = String(gold || '').trim().toLowerCase();
    if (g === 'pt' || g === 'pt950') return 'pt950';
    if (g === 'silver925' || g === 's925') return 's925';
    return g;
  }

  function caratLookupKeys(carat) {
    var keys = [];
    function add(key) {
      if (key != null && key !== '' && keys.indexOf(String(key)) < 0) keys.push(String(key));
    }
    add(carat);
    var n = parseFloat(carat);
    if (!Number.isNaN(n)) {
      add(n.toFixed(1));
      if (n === Math.floor(n)) add(String(Math.floor(n)) + '.0');
      if (n === Math.floor(n)) add(String(Math.floor(n)));
    }
    return keys;
  }

  function chainWaxChin(thickness, lengthCm) {
    var length = parseInt(lengthCm, 10);
    var table = CHAIN_WAX_WEIGHT_CHIN[thickness];
    var wax = table && table[length];
    if (wax == null) throw new Error('unsupported chain thickness or length');
    return wax;
  }

  function waxToMetalChin(waxChin, gold) {
    var factor = WAX_TO_METAL_CHIN[gold];
    if (factor == null) throw new Error('unknown gold: ' + gold);
    return waxChin * factor;
  }

  function lookupWeight(product, category, gold, carat, lengthCm) {
    gold = normalizeGold(gold);
    var wax = null;
    if (category === 'chain') {
      wax = product.lengthWeights && product.lengthWeights[carat]
        && product.lengthWeights[carat][String(lengthCm)];
      if (wax == null) {
        wax = chainWaxFromTypeCatalog(product.chainType || 'douyuan', carat, lengthCm);
      }
    } else {
      var byGold = product.weights && product.weights[gold];
      if (byGold) {
        var caratKeys = caratLookupKeys(carat);
        for (var i = 0; i < caratKeys.length; i++) {
          if (byGold[caratKeys[i]] != null) {
            wax = byGold[caratKeys[i]];
            break;
          }
        }
      }
    }
    if (wax == null) throw new Error('no weight');
    var weight = waxToMetalChin(Number(wax), gold);
    if (category === 'bracelet' && lengthCm != null) weight *= Number(lengthCm) / BRACELET_REFERENCE_LENGTH_CM;
    return weight;
  }

  /** Effective 品項加價: row addonPrices[gold][carat] when > 0, else category. */
  function resolveAddonPrice(category, product, gold, carat) {
    gold = normalizeGold(gold);
    var table = product && product.addonPrices && product.addonPrices[gold];
    if (!table && product && product.addonPrices && gold === 's925') {
      table = product.addonPrices.silver925;
    }
    if (table) {
      var caratKeys = caratLookupKeys(carat);
      for (var i = 0; i < caratKeys.length; i++) {
        var raw = table[caratKeys[i]];
        if (raw == null || raw === '') continue;
        var row = Number(raw);
        // 0 = unset (follow category); same as server _effective_addon_price.
        if (Number.isFinite(row) && row > 0) return Math.round(row);
      }
    }
    var cat = Number(categoryAddonPrices[category]);
    return Number.isFinite(cat) && cat >= 0 ? Math.round(cat) : 0;
  }

  /** Ring-size 品項加價: step formula, else legacy sizes[] lookup. */
  function resolveRingSizeAddon(product, ringSize) {
    if (ringSize == null || ringSize === '') return 0;
    var size = Math.round(Number(ringSize));
    if (!Number.isFinite(size)) return 0;
    var cfg = product && (product.ringSizeConfig || product.ring_size_config);
    if (!cfg || typeof cfg !== 'object') return 0;

    var stepRaw = cfg.pricePerSizeTwd != null ? cfg.pricePerSizeTwd : cfg.price_per_size_twd;
    if (stepRaw != null && stepRaw !== '') {
      var minRaw = cfg.minSize != null ? cfg.minSize
        : (cfg.min_size != null ? cfg.min_size
          : (cfg.startSize != null ? cfg.startSize : cfg.start_size));
      var minSize = Math.round(Number(minRaw));
      var step = Number(stepRaw);
      if (!Number.isFinite(minSize) || !Number.isFinite(step) || step < 0) return 0;
      var addon = Math.max(0, (size - minSize) * step);
      return Math.round(addon);
    }

    var rows = cfg.sizes;
    if (Array.isArray(rows)) {
      for (var i = 0; i < rows.length; i += 1) {
        var r = rows[i];
        if (!r) continue;
        if (Math.round(Number(r.size)) !== size) continue;
        var rowAddon = r.addonPriceTwd != null ? r.addonPriceTwd : r.addon_price_twd;
        var n = Number(rowAddon);
        return Number.isFinite(n) && n > 0 ? Math.round(n) : 0;
      }
    }
    return 0;
  }

  function laborFee(category, gold, addonPriceTwd) {
    // 品項加價 > 0 replaces base labor; 0 keeps base. Folded into 金工價格.
    var base = LABOR_FEE_TWD;
    if (category === 'chain' && gold === 's925') base = CHAIN_LABOR_FEE_TWD.s925;
    else if (category === 'chain') base = CHAIN_LABOR_FEE_TWD.other;
    var addon = addonPriceTwd != null ? Number(addonPriceTwd) : Number(categoryAddonPrices[category]);
    var add = Number.isFinite(addon) && addon > 0 ? Math.round(addon) : 0;
    return add > 0 ? add : base;
  }

  function setCategoryAddons(map) {
    if (!map || typeof map !== 'object') return;
    Object.keys(map).forEach(function (slug) {
      var n = Number(map[slug]);
      if (Number.isFinite(n) && n >= 0) categoryAddonPrices[slug] = Math.round(n);
    });
  }

  function perChinFor(gold) {
    return perGramFor(gold) * CHIN_TO_GRAMS;
  }

  function metalPreTax(gold, weightChin) {
    var perChin = perChinFor(gold);
    return { amount: perChin * weightChin, perGram: perGramFor(gold) };
  }

  function computeChainAddon(catalog, chainProductId, chainGold, chainLengthCm, chainThickness) {
    // Full standalone O字鍊 quote for 搭配鏈條 (metal+tax + labor/addon, or manual).
    var chainProduct = findProduct(catalog, 'chain', chainProductId);
    if (!chainProduct) throw new Error('invalid chain');
    var carat = chainThickness || DEFAULT_ATTACHED_CHAIN_THICKNESS;
    chainGold = normalizeGold(chainGold);
    var manual = chainProduct.manualPrices && chainProduct.manualPrices[chainGold]
      && chainProduct.manualPrices[chainGold][carat];
    if (manual != null) return { chainPrice: Number(manual) };
    var weightChin = lookupWeight(chainProduct, 'chain', chainGold, carat, chainLengthCm);
    var metal = metalPreTax(chainGold, weightChin);
    var labor = laborFee(
      'chain', chainGold, resolveAddonPrice('chain', chainProduct, chainGold, carat)
    );
    return {
      chainPrice: Math.round(metal.amount * (1 + TAX_RATE)) + labor,
      chainWeightChin: weightChin,
    };
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
    var chainThickness = data.chainThickness || DEFAULT_ATTACHED_CHAIN_THICKNESS;
    var earringQty = category === 'earring' ? asEarringQuantity(data.quantity) : 1;

    if (!category || !carat || !productId) return { ready: false };
    if (category !== 'diamond' && !gold) return { ready: false };
    gold = normalizeGold(gold);
    if (chainGold) chainGold = normalizeGold(chainGold);
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
    // 手動定價: fixed unit total for every metal category (incl. standalone chain).
    if (manual != null) {
      var manualRingAddon = category === 'ring' ? resolveRingSizeAddon(product, data.ringSize) : 0;
      return {
        ready: true,
        total: (Number(manual) + manualRingAddon) * earringQty,
        manualOverride: true,
        ringSizePrice: manualRingAddon || undefined,
        quantity: category === 'earring' ? earringQty : undefined,
      };
    }

    var weightChin;
    try {
      weightChin = lookupWeight(product, category, gold, carat, lengthCm);
    } catch (e) {
      return { ready: false, error: 'product not available' };
    }

    var weightGrams = weightChin * CHIN_TO_GRAMS;
    var laborPreTax = laborFee(category, gold, resolveAddonPrice(category, product, gold, carat));
    var ringSizeAddon = 0;
    if (category === 'ring') {
      ringSizeAddon = resolveRingSizeAddon(product, data.ringSize);
    }
    var metal = metalPreTax(gold, weightChin);
    var taijinDisplay = Math.round(metal.amount * (1 + TAX_RATE));
    // Labor is flat NT$ — not taxed. Tax only on metal.
    // 搭配鏈條 uses full O字鍊 quote (taxed metal + chain labor/addon or manual).
    // Earring per-row 耳扣價錢 folds into labor / 金工價格 (with 品項加價).
    // Ring size 品項加價 stacks on top of category/variant labor addon.
    var laborDisplay = laborPreTax;
    if (category === 'earring') {
      var claspTable = product.earClaspPrices && product.earClaspPrices[gold];
      var claspRaw = claspTable && claspTable[carat] != null ? Number(claspTable[carat]) : 0;
      if (Number.isFinite(claspRaw) && claspRaw > 0) laborDisplay = laborPreTax + Math.round(claspRaw);
    } else if (category === 'ring' && ringSizeAddon > 0) {
      laborDisplay = laborPreTax + ringSizeAddon;
    }

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

    // 配鑽: fixed total wins; else 克拉數 × 一克拉價格 (sideStonePrices = ppc)
    var sideStonePpc = null;
    var sideTable = product.sideStonePrices && product.sideStonePrices[gold];
    if (category !== 'chain' && sideTable && sideTable[carat] != null) {
      sideStonePpc = Number(sideTable[carat]);
    }
    var sideStoneCarat = null;
    var sideCaratTable = product.sideStoneCarats && product.sideStoneCarats[gold];
    if (category !== 'chain' && sideCaratTable && sideCaratTable[carat] != null) {
      sideStoneCarat = Number(sideCaratTable[carat]);
    }
    var sideStonePrice = null;
    var sideTotalTable = product.sideStoneTotals && product.sideStoneTotals[gold];
    if (category !== 'chain' && sideTotalTable && sideTotalTable[carat] != null) {
      sideStonePrice = Math.round(Number(sideTotalTable[carat]));
    } else if (sideStonePpc != null && sideStoneCarat != null) {
      sideStonePrice = Math.round(sideStoneCarat * sideStonePpc);
    }

    if (earringQty > 1) {
      if (diamondPrice != null) diamondPrice = diamondPrice * earringQty;
      if (sideStonePrice != null) sideStonePrice = sideStonePrice * earringQty;
      taijinDisplay = Math.round(taijinDisplay * earringQty);
      laborDisplay = laborDisplay * earringQty;
      weightGrams = weightGrams * earringQty;
    }

    var total = (diamondPrice || 0) + (sideStonePrice || 0) + taijinDisplay + laborDisplay;
    var chainDisplay = null;

    if (category === 'pendant' && includeChain && chainProductId && chainGold && chainLength) {
      try {
        var addon = computeChainAddon(
          catalog, chainProductId, chainGold, chainLength, chainThickness
        );
        chainDisplay = Math.round(addon.chainPrice);
        total += chainDisplay;
      } catch (e) {
        return { ready: false, error: 'invalid chain option' };
      }
    }

    return {
      ready: true,
      manualOverride: false,
      diamondPrice: diamondPrice,
      sideStonePrice: sideStonePrice,
      sideStoneCarat: sideStoneCarat,
      taijinPrice: taijinDisplay,
      laborPrice: laborDisplay,
      metalworkPrice: taijinDisplay + laborDisplay,
      ringSizePrice: ringSizeAddon || undefined,
      chainPrice: chainDisplay,
      total: Math.round(total),
      quantity: category === 'earring' ? earringQty : undefined,
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
        stoneCountCategories: [],
        fancyMinCarat: '0.3',
        nonRoundShapeMinCarat: '0.3',
        nonRoundShapeSurcharge: 0.10,
        defaultStoneCountByCategory: DEFAULT_STONE_COUNT_BY_CATEGORY,
        earringQuantityMin: EARRING_QUANTITY_MIN,
        earringQuantityMax: EARRING_QUANTITY_MAX,
      },
    };
  }

  global.ShopPricingLocal = {
    computeOrderPricing: computeOrderPricing,
    pricesPayload: pricesPayload,
    setLiveGoldRates: setLiveGoldRates,
    setCategoryAddons: setCategoryAddons,
    WAX_TO_METAL_CHIN: WAX_TO_METAL_CHIN,
    waxToMetalChin: waxToMetalChin,
    LABOR_FEE_TWD: LABOR_FEE_TWD,
    CHAIN_LABOR_FEE_TWD: CHAIN_LABOR_FEE_TWD,
    lengthWeightsForChainType: lengthWeightsForChainType,
  };
})(window);
