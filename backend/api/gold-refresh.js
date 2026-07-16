/* POST: fetch latest BOT 黃金條塊牌價 and update gold_price_cache.
 * Uses cheerio parser (same rules as gold-price-scraper). May fail when BOT
 * serves a bot-challenge page — in that case the cache is left unchanged. */
const { applyCors } = require('../lib/cors');
const { findGoldBarPrices, isBotChallenge } = require('../lib/parseBotGold');
const { sql } = require('../lib/db');
const { buildGoldQuotePayload, BOT_SOURCE_URL } = require('../lib/goldQuotePayload');

const BOT_RECENT_URL = 'https://rate.bot.com.tw/gold/quote/recent';
const BOT_LIVE_URL = 'https://rate.bot.com.tw/gold?Lang=zh-TW';
const FALLBACK_TWD = { XPT: 1050, XAG: 30 };

const BOT_HEADERS = {
  'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
  'Accept-Language': 'zh-TW,zh;q=0.9,en;q=0.8',
  Accept: 'text/html,application/xhtml+xml',
};

async function fetchBotHtml(url) {
  const res = await fetch(url, { headers: BOT_HEADERS, redirect: 'follow' });
  if (!res.ok) throw new Error(`BOT HTTP ${res.status}`);
  return res.text();
}

async function scrapeBotGold() {
  let lastError = null;
  for (const url of [BOT_RECENT_URL, BOT_LIVE_URL]) {
    try {
      const html = await fetchBotHtml(url);
      if (isBotChallenge(html)) {
        lastError = new Error('BOT challenge page — use gold-price-scraper cron for headless fetch');
        continue;
      }
      const parsed = findGoldBarPrices(html);
      if (!parsed) {
        lastError = new Error('黃金條塊 sell price not found');
        continue;
      }
      return { ...parsed, sourceUrl: url };
    } catch (err) {
      lastError = err;
    }
  }
  throw lastError || new Error('BOT scrape failed');
}

module.exports = async function handler(req, res) {
  if (applyCors(req, res)) return;
  if (req.method !== 'POST') return res.status(405).json({ error: 'method not allowed' });

  try {
    const { perGram, stamp, sourceUrl } = await scrapeBotGold();

    const [row] = await sql`
      insert into gold_price_cache (id, xau_per_gram, xpt_per_gram, xag_per_gram, bot_posted_at, source, source_url, fetched_at)
      values (1, ${perGram}, ${FALLBACK_TWD.XPT}, ${FALLBACK_TWD.XAG}, ${stamp || null}, 'bot', ${sourceUrl || BOT_SOURCE_URL}, now())
      on conflict (id) do update set
        xau_per_gram = excluded.xau_per_gram,
        bot_posted_at = excluded.bot_posted_at,
        source = excluded.source,
        source_url = excluded.source_url,
        fetched_at = excluded.fetched_at
      returning xau_per_gram, xpt_per_gram, xag_per_gram, bot_posted_at, source, source_url, fetched_at
    `;

    const payload = buildGoldQuotePayload(row);
    res.status(200).json({ refreshed: true, ...payload });
  } catch (err) {
    console.error('[gold-refresh]', err);
    try {
      const [row] = await sql`select xau_per_gram, xpt_per_gram, xag_per_gram, bot_posted_at, source, source_url, fetched_at from gold_price_cache where id = 1`;
      const payload = buildGoldQuotePayload(row);
      res.status(200).json({
        refreshed: false,
        message: String(err.message || err),
        ...payload,
      });
    } catch (readErr) {
      console.error('[gold-refresh read]', readErr);
      res.status(502).json({ refreshed: false, error: String(err.message || err) });
    }
  }
};
