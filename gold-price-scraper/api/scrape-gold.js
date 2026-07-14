/* Vercel serverless function: scrapes Bank of Taiwan (BOT) 黃金條塊 (gold bar)
 * 本行賣出 price using a headless browser, then writes it to Neon Postgres
 * (same DATABASE_URL/table the /backend project reads from via /api/gold-price).
 *
 * JS/Node port of imprint-calculator's bot_metal_feed.py (Python + Playwright).
 * Same problem the Python version solves: BOT's gold-quote page sits behind a
 * bot-challenge (redirect + sec_cpt cookie) that a plain fetch() cannot pass,
 * so this also needs a real headless browser — puppeteer-core + @sparticuz/chromium
 * is the Node/serverless equivalent of Python's Playwright + chromium.
 *
 * Trigger: Vercel Cron (see vercel.json), hourly 08:00-22:00 Asia/Taipei.
 * Auth: Vercel Cron automatically sends `Authorization: Bearer <CRON_SECRET>`
 * when a `CRON_SECRET` env var is set on the project — this checks that, so
 * the endpoint can't be triggered by anyone who finds the public URL.
 * https://vercel.com/docs/cron-jobs/manage-cron-jobs#securing-cron-jobs
 */
const chromium = require('@sparticuz/chromium');
const puppeteer = require('puppeteer-core');
const { neon } = require('@neondatabase/serverless');
const { findGoldBarPrices, isBotChallenge } = require('../lib/parseBotGold');

const BOT_LIVE_URL = 'https://rate.bot.com.tw/gold?Lang=zh-TW';
const BOT_RECENT_URL = 'https://rate.bot.com.tw/gold/quote/recent';
const CHALLENGE_MAX_WAIT_MS = 75_000;
const CHALLENGE_POLL_MS = 5_000;
const FALLBACK_TWD_PER_GRAM = { XAU: 4300, XPT: 1050, XAG: 30 };

async function fetchPageHtml(url) {
  const browser = await puppeteer.launch({
    args: [...chromium.args, '--disable-blink-features=AutomationControlled'],
    defaultViewport: { width: 1280, height: 900 },
    executablePath: await chromium.executablePath(),
    headless: chromium.headless,
  });
  try {
    const page = await browser.newPage();
    await page.setUserAgent(
      'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 ' +
      '(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    );
    await page.setExtraHTTPHeaders({ 'Accept-Language': 'zh-TW,zh;q=0.9,en;q=0.8' });
    await page.evaluateOnNewDocument(() => {
      Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
    });
    await page.goto(url, { waitUntil: 'load', timeout: 30_000 });

    let html = await page.content();
    let waited = 0;
    while (isBotChallenge(html) && waited < CHALLENGE_MAX_WAIT_MS) {
      await new Promise((r) => setTimeout(r, CHALLENGE_POLL_MS));
      waited += CHALLENGE_POLL_MS;
      html = await page.content();
    }
    return html;
  } finally {
    await browser.close();
  }
}

async function downloadBotHtml() {
  let lastError = null;
  for (const url of [BOT_LIVE_URL, BOT_RECENT_URL]) {
    try {
      const html = await fetchPageHtml(url);
      if (isBotChallenge(html)) {
        lastError = new Error(`${url}: bot challenge did not clear within ${CHALLENGE_MAX_WAIT_MS / 1000}s`);
        continue;
      }
      const result = findGoldBarPrices(html);
      if (!result) {
        lastError = new Error(`${url}: 黃金條塊 sell price not found on page`);
        continue;
      }
      return { ...result, sourceUrl: url };
    } catch (err) {
      lastError = err;
    }
  }
  throw lastError || new Error('黃金條塊 sell price not found on BOT pages');
}

module.exports = async function handler(req, res) {
  if (req.headers['authorization'] !== `Bearer ${process.env.CRON_SECRET}`) {
    res.status(401).json({ error: 'unauthorized' });
    return;
  }

  const sql = neon(process.env.DATABASE_URL);

  try {
    const { perGram, stamp, sourceUrl } = await downloadBotHtml();

    await sql`
      insert into gold_price_cache (id, xau_per_gram, xpt_per_gram, xag_per_gram, bot_posted_at, source, source_url, fetched_at)
      values (1, ${perGram}, ${FALLBACK_TWD_PER_GRAM.XPT}, ${FALLBACK_TWD_PER_GRAM.XAG}, ${stamp || null}, 'bot', ${sourceUrl}, now())
      on conflict (id) do update set
        xau_per_gram = excluded.xau_per_gram,
        bot_posted_at = excluded.bot_posted_at,
        source = excluded.source,
        source_url = excluded.source_url,
        fetched_at = excluded.fetched_at
    `;

    res.status(200).json({ ok: true, xauPerGram: perGram, botPostedAt: stamp });
  } catch (err) {
    // Deliberately do NOT overwrite gold_price_cache on failure — keep the
    // last known-good value in Neon, same defensive behavior as the
    // Python version (never wipe a good cache just because one fetch failed).
    console.error('gold scrape failed:', err);
    res.status(502).json({ ok: false, error: String(err && err.message || err) });
  }
};
