/* Build gold quote + alloy rates for the public gold-price page. */
const { PURITY_MULTIPLIER, METAL_SYMBOL, LABOR_FEE, TAX_RATE, CHIN_TO_GRAMS } = require('./pricing');

const BOT_SOURCE_URL = 'https://rate.bot.com.tw/gold/quote/recent';
const STALE_HOURS = 24;

const VALID_GOLDS = ['9k', '14k', '18k', 'pt950', 's925'];

function formatFetchedAt(iso) {
  if (!iso) return null;
  try {
    return new Date(iso).toLocaleString('zh-TW', { timeZone: 'Asia/Taipei', hour12: false });
  } catch (_) {
    return String(iso);
  }
}

function isStale(fetchedAt) {
  if (!fetchedAt) return true;
  const ms = Date.now() - new Date(fetchedAt).getTime();
  return ms > STALE_HOURS * 60 * 60 * 1000;
}

function buildGoldQuotePayload(row) {
  if (!row) {
    return {
      quote: {
        available: false,
        source_url: BOT_SOURCE_URL,
      },
      alloyRates: {},
      formula: formulaMeta(),
    };
  }

  const raw = {
    XAU: Number(row.xau_per_gram),
    XPT: Number(row.xpt_per_gram),
    XAG: Number(row.xag_per_gram),
  };

  const alloyRates = {};
  for (const gold of VALID_GOLDS) {
    const symbol = METAL_SYMBOL[gold];
    if (raw[symbol] != null) alloyRates[gold] = raw[symbol] * PURITY_MULTIPLIER[gold];
  }

  const source = row.source || 'fallback';
  const fetchedAt = row.fetched_at;

  const alloyRatesPerChin = {};
  for (const gold of VALID_GOLDS) {
    if (alloyRates[gold] != null) alloyRatesPerChin[gold] = alloyRates[gold] * CHIN_TO_GRAMS;
  }

  return {
    quote: {
      available: true,
      sell: raw.XAU,
      sellPerChin: raw.XAU * CHIN_TO_GRAMS,
      source,
      bot_posted_at: row.bot_posted_at || null,
      fetched_at: fetchedAt,
      fetched_at_display: formatFetchedAt(fetchedAt),
      is_stale: isStale(fetchedAt) || source === 'fallback',
      source_url: row.source_url || BOT_SOURCE_URL,
    },
    alloyRates,
    alloyRatesPerChin,
    formula: formulaMeta(),
  };
}

function formulaMeta() {
  return {
    taxRate: TAX_RATE,
    chinToGrams: CHIN_TO_GRAMS,
    laborFee: LABOR_FEE,
    purityMultiplier: PURITY_MULTIPLIER,
    metalSymbol: METAL_SYMBOL,
    notes: [
      '台金（含稅）= 金屬重（錢）× 成色金價（元/錢）× 5% 營業稅',
      '金工費（含稅）= 品項金工費 × 5% 營業稅',
      '鍊條品項：金屬成本 × 2（雙股）',
      '總價 = 鑽石牌價 + 台金 + 金工費（鑽石牌價已含稅，不再加稅）',
    ],
  };
}

module.exports = { buildGoldQuotePayload, BOT_SOURCE_URL, VALID_GOLDS };
