/**
 * Fetch + parse Bank of Taiwan 黃金條塊牌價.
 * Used by Render (npm start), local dev, and fetch-gold-quote.mjs.
 */
const { findGoldBarPrices, isBotChallenge } = require('../backend/lib/parseBotGold');

const BOT_URLS = [
  'https://rate.bot.com.tw/gold/quote/recent',
  'https://rate.bot.com.tw/gold?Lang=zh-TW',
];

const BOT_HEADERS = {
  'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
  'Accept-Language': 'zh-TW,zh;q=0.9,en;q=0.8',
  Accept: 'text/html,application/xhtml+xml',
};

const PURITY_MULTIPLIER = { '9k': 0.5, '14k': 0.75, '18k': 0.85, pt950: 1.1, s925: 0.925 };
const METAL_BASE = { '9k': 'XAU', '14k': 'XAU', '18k': 'XAU', pt950: 'XPT', s925: 'XAG' };
const FALLBACK_XPT = 1050;
const FALLBACK_XAG = 30;

function buildAlloyRates(raw) {
  const alloy = {};
  for (const gold of Object.keys(PURITY_MULTIPLIER)) {
    const symbol = METAL_BASE[gold];
    if (raw[symbol] != null) alloy[gold] = raw[symbol] * PURITY_MULTIPLIER[gold];
  }
  return alloy;
}

function formatFetchedAt(date) {
  return date.toLocaleString('zh-TW', { timeZone: 'Asia/Taipei', hour12: false });
}

function buildPayload(parsed, sourceUrl) {
  const now = new Date();
  const raw = { XAU: parsed.perGram, XPT: FALLBACK_XPT, XAG: FALLBACK_XAG };
  return {
    refreshed: true,
    quote: {
      available: true,
      sell: parsed.perGram,
      source: 'bot',
      bot_posted_at: parsed.stamp || null,
      fetched_at: now.toISOString(),
      fetched_at_display: formatFetchedAt(now),
      is_stale: false,
      source_url: sourceUrl,
    },
    alloyRates: buildAlloyRates(raw),
  };
}

async function fetchBotGoldQuote() {
  let lastError = null;
  for (const url of BOT_URLS) {
    try {
      const res = await fetch(url, { headers: BOT_HEADERS, redirect: 'follow' });
      if (!res.ok) throw new Error('HTTP ' + res.status);
      const html = await res.text();
      if (isBotChallenge(html)) throw new Error('BOT challenge');
      const parsed = findGoldBarPrices(html);
      if (!parsed) throw new Error('parse failed');
      return buildPayload(parsed, url);
    } catch (err) {
      lastError = err;
    }
  }
  throw lastError || new Error('BOT scrape failed');
}

module.exports = { fetchBotGoldQuote, buildPayload, buildAlloyRates };
