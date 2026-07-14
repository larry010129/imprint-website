/* Parses Bank of Taiwan (BOT) 黃金條塊 (gold bar) 本行賣出 price from HTML.
 * Ported from imprint-calculator's diamond_calculator/application/bot_metal_feed.py
 * (Python + BeautifulSoup) to JS + cheerio. Parsing rules are unchanged;
 * only the HTML-query API differs.
 */
const cheerio = require('cheerio');

const GOLD_BAR_ANCHOR = '黃金條塊';
const BAR_DERIVED_GRAM_MIN = 3500;
const BAR_DERIVED_GRAM_MAX = 5500;

const WEIGHT_HEADER_PATTERNS = [
  [/1\s*公斤/, 1000],
  [/500\s*公克/, 500],
  [/250\s*公克/, 250],
  [/100\s*公克/, 100],
];

function textOf($el) {
  return $el.text().replace(/\s+/g, ' ').trim();
}

function parseTwdAmount(text) {
  const cleaned = (text || '').replace(/[^\d,.]/g, '');
  if (!cleaned) return null;
  const n = parseFloat(cleaned.replace(/,/g, ''));
  return Number.isFinite(n) ? n : null;
}

function cellAmount($, td) {
  if (!td || !td.length) return null;
  return parseTwdAmount(textOf($(td)));
}

function gramsFromHeaderText(text) {
  const normalized = (text || '').replace(/\s+/g, '');
  for (const [pattern, grams] of WEIGHT_HEADER_PATTERNS) {
    if (pattern.test(text || '') || pattern.test(normalized)) return grams;
  }
  return null;
}

function isBarDerivedGramPrice(amount) {
  return amount != null && amount >= BAR_DERIVED_GRAM_MIN && amount <= BAR_DERIVED_GRAM_MAX;
}

function parseBotDatetime(stamp) {
  if (!stamp) return null;
  const m = /(\d{4})\/(\d{2})\/(\d{2})\s+(\d{2}):(\d{2})/.exec(stamp);
  if (!m) return null;
  return m.slice(1, 6).map(Number);
}

function extractPageStamp($) {
  const text = textOf($('body'));
  for (const pattern of [
    /掛牌時間[：:]\s*(\d{4}\/\d{2}\/\d{2}\s+\d{2}:\d{2})/,
    /牌價時間[：:]\s*(\d{4}\/\d{2}\/\d{2}\s+\d{2}:\d{2})/,
  ]) {
    const m = pattern.exec(text);
    if (m) return m[1].trim();
  }
  const timeSpan = $('span.time').first();
  if (timeSpan.length) {
    const m = /(\d{4}\/\d{2}\/\d{2}\s+\d{2}:\d{2})/.exec(textOf(timeSpan));
    if (m) return m[1];
  }
  const timeCell = $('td[data-table="牌價時間"]').first();
  if (timeCell.length) {
    const m = /(\d{4}\/\d{2}\/\d{2}\s+\d{2}:\d{2})/.exec(textOf(timeCell));
    if (m) return m[1];
  }
  return null;
}

function extractStampFromRow($, row) {
  const timeCell = $(row).find('td[data-table*="牌價時間"]').first();
  if (timeCell.length) {
    const m = /(\d{4}\/\d{2}\/\d{2}\s+\d{2}:\d{2})/.exec(textOf(timeCell));
    if (m) return m[1];
  }
  const m = /(\d{4}\/\d{2}\/\d{2}\s+\d{2}:\d{2})/.exec(textOf($(row)));
  return m ? m[1] : null;
}

function weightColumnsFromTable($, table) {
  const rows = $(table).find('tr');
  for (const row of rows.toArray()) {
    const cols = {};
    $(row).find('td, th').each((idx, cell) => {
      const grams = gramsFromHeaderText(textOf($(cell)));
      if (grams) cols[idx] = grams;
    });
    if (Object.keys(cols).length) return cols;
  }
  return {};
}

function perGramFromBarSellRow($, row, weightCols) {
  const cells = $(row).find('td, th').toArray();
  const candidates = [];
  for (const [idxStr, grams] of Object.entries(weightCols)) {
    const idx = Number(idxStr);
    if (idx >= cells.length) continue;
    const amount = cellAmount($, $(cells[idx]));
    if (amount == null || amount < 10000) continue;
    const perGram = amount / grams;
    if (isBarDerivedGramPrice(perGram)) candidates.push([perGram, grams]);
  }
  if (!candidates.length) return null;
  candidates.sort((a, b) => b[1] - a[1]);
  return candidates[0][0];
}

function isGoldBarTable($, table) {
  let found = false;
  $(table).find('td').each((_, td) => {
    if (textOf($(td)) === GOLD_BAR_ANCHOR) found = true;
  });
  if (found) return true;
  const summary = $(table).attr('summary') || $(table).attr('title') || '';
  if (summary.includes(GOLD_BAR_ANCHOR) && !summary.includes('存摺')) return true;
  if (['黃金條塊歷史牌價', '黃金條塊牌價', '黃金條塊表格'].some((s) => summary.includes(s))) return true;
  return false;
}

function findGoldBarAnchor($) {
  let anchor = null;
  $('td').each((_, td) => {
    if (!anchor && textOf($(td)) === GOLD_BAR_ANCHOR) anchor = td;
  });
  return anchor;
}

function quotesFromLiveGoldBarBlock($, pageStamp) {
  const anchor = findGoldBarAnchor($);
  if (!anchor) return [];
  const table = $(anchor).closest('table');
  if (!table.length) return [];

  const weightCols = weightColumnsFromTable($, table);
  if (!Object.keys(weightCols).length) return [];

  const anchorRow = $(anchor).closest('tr').get(0);
  const quotes = [];
  let started = !anchorRow;

  for (const row of table.find('tr').toArray()) {
    if (row === anchorRow) {
      started = true;
    } else if (!started) {
      continue;
    }
    const rowText = textOf($(row));
    if (rowText.includes('轉換')) continue;
    if (!rowText.includes('本行賣出') && !$(row).find('td[data-table="本行賣出"]').length) continue;

    const perGram = perGramFromBarSellRow($, row, weightCols);
    if (perGram != null) {
      quotes.push([perGram, pageStamp || extractPageStamp($)]);
      break;
    }
  }
  return quotes;
}

function quotesFromHistoryTables($) {
  const quotes = [];
  $('table').each((_, table) => {
    const summary = $(table).attr('summary') || $(table).attr('title') || '';
    if (!isGoldBarTable($, table)) return;
    if (summary.includes('黃金存摺') && !summary.includes('黃金條塊')) return;

    const weightCols = weightColumnsFromTable($, table);
    if (!Object.keys(weightCols).length) return;

    $(table).find('tr').each((__, row) => {
      const rowText = textOf($(row));
      if (rowText.includes('轉換')) return;
      const stamp = extractStampFromRow($, row);
      const perGram = perGramFromBarSellRow($, row, weightCols);
      if (perGram == null) return;
      if (rowText.includes('本行賣出') || stamp) quotes.push([perGram, stamp]);
    });
  });
  return quotes;
}

function pickLatestQuote(quotes) {
  let best = null;
  let bestKey = null;
  for (const [sell, stamp] of quotes) {
    if (sell == null) continue;
    const key = parseBotDatetime(stamp) || [0, 0, 0, 0, 0];
    if (!best || compareKey(key, bestKey) >= 0) {
      best = [sell, stamp];
      bestKey = key;
    }
  }
  return best;
}

function compareKey(a, b) {
  for (let i = 0; i < a.length; i++) {
    if (a[i] !== b[i]) return a[i] - b[i];
  }
  return 0;
}

/** Parses BOT gold-quote HTML. Returns { perGram, stamp } or null if not found. */
function findGoldBarPrices(html) {
  const $ = cheerio.load(html);
  const pageStamp = extractPageStamp($);
  const quotes = [
    ...quotesFromLiveGoldBarBlock($, pageStamp),
    ...quotesFromHistoryTables($),
  ];
  if (!quotes.length) return null;

  const [sell, stampRaw] = pickLatestQuote(quotes) || [];
  if (sell == null) return null;
  return { perGram: sell, stamp: stampRaw || pageStamp };
}

/** True when the response is BOT's bot-challenge page rather than real content. */
function isBotChallenge(html) {
  if (!html || html.length < 10000) return true;
  const lowered = html.toLowerCase();
  return lowered.includes('challenge validation') || lowered.includes('<title>challenge');
}

module.exports = { findGoldBarPrices, isBotChallenge, GOLD_BAR_ANCHOR };
