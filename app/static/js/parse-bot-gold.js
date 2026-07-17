/* Browser parser for Bank of Taiwan 黃金條塊 本行賣出 (gold bar sell) price. */
(function (global) {
  'use strict';

  var GOLD_BAR_ANCHOR = '黃金條塊';
  var BAR_DERIVED_GRAM_MIN = 3500;
  var BAR_DERIVED_GRAM_MAX = 5500;
  var WEIGHT_HEADER_PATTERNS = [
    [/1\s*公斤/, 1000],
    [/500\s*公克/, 500],
    [/250\s*公克/, 250],
    [/100\s*公克/, 100],
  ];

  function textOf(el) {
    return (el && el.textContent || '').replace(/\s+/g, ' ').trim();
  }

  function parseTwdAmount(text) {
    var cleaned = (text || '').replace(/[^\d,.]/g, '');
    if (!cleaned) return null;
    var n = parseFloat(cleaned.replace(/,/g, ''));
    return Number.isFinite(n) ? n : null;
  }

  function cellAmount(cell) {
    if (!cell) return null;
    return parseTwdAmount(textOf(cell));
  }

  function gramsFromHeaderText(text) {
    var normalized = (text || '').replace(/\s+/g, '');
    for (var i = 0; i < WEIGHT_HEADER_PATTERNS.length; i++) {
      var pattern = WEIGHT_HEADER_PATTERNS[i][0];
      var grams = WEIGHT_HEADER_PATTERNS[i][1];
      if (pattern.test(text || '') || pattern.test(normalized)) return grams;
    }
    return null;
  }

  function isBarDerivedGramPrice(amount) {
    return amount != null && amount >= BAR_DERIVED_GRAM_MIN && amount <= BAR_DERIVED_GRAM_MAX;
  }

  function parseBotDatetime(stamp) {
    if (!stamp) return null;
    var m = /(\d{4})\/(\d{2})\/(\d{2})\s+(\d{2}):(\d{2})/.exec(stamp);
    if (!m) return null;
    return [Number(m[1]), Number(m[2]), Number(m[3]), Number(m[4]), Number(m[5])];
  }

  function compareKey(a, b) {
    for (var i = 0; i < a.length; i++) {
      if (a[i] !== b[i]) return a[i] - b[i];
    }
    return 0;
  }

  function extractPageStamp(doc) {
    var bodyText = textOf(doc.body);
    var patterns = [
      /掛牌時間[：:]\s*(\d{4}\/\d{2}\/\d{2}\s+\d{2}:\d{2})/,
      /牌價時間[：:]\s*(\d{4}\/\d{2}\/\d{2}\s+\d{2}:\d{2})/,
    ];
    for (var i = 0; i < patterns.length; i++) {
      var m = patterns[i].exec(bodyText);
      if (m) return m[1].trim();
    }
    var timeSpan = doc.querySelector('span.time');
    if (timeSpan) {
      m = /(\d{4}\/\d{2}\/\d{2}\s+\d{2}:\d{2})/.exec(textOf(timeSpan));
      if (m) return m[1];
    }
    var timeCell = doc.querySelector('td[data-table="牌價時間"]');
    if (timeCell) {
      m = /(\d{4}\/\d{2}\/\d{2}\s+\d{2}:\d{2})/.exec(textOf(timeCell));
      if (m) return m[1];
    }
    return null;
  }

  function extractStampFromRow(row) {
    var timeCell = row.querySelector('td[data-table*="牌價時間"]');
    if (timeCell) {
      var m = /(\d{4}\/\d{2}\/\d{2}\s+\d{2}:\d{2})/.exec(textOf(timeCell));
      if (m) return m[1];
    }
    var m2 = /(\d{4}\/\d{2}\/\d{2}\s+\d{2}:\d{2})/.exec(textOf(row));
    return m2 ? m2[1] : null;
  }

  function weightColumnsFromTable(table) {
    var rows = table.querySelectorAll('tr');
    for (var i = 0; i < rows.length; i++) {
      var cols = {};
      var cells = rows[i].querySelectorAll('td, th');
      for (var j = 0; j < cells.length; j++) {
        var grams = gramsFromHeaderText(textOf(cells[j]));
        if (grams) cols[j] = grams;
      }
      if (Object.keys(cols).length) return cols;
    }
    return {};
  }

  var PREFERRED_GRAM_ORDER = [100, 250, 500, 1000];

  function perGramFromBarSellRow(row, weightCols) {
    var cells = row.querySelectorAll('td, th');
    var candidates = {};
    Object.keys(weightCols).forEach(function (idxStr) {
      var idx = Number(idxStr);
      if (idx >= cells.length) return;
      var amount = cellAmount(cells[idx]);
      if (amount == null || amount < 10000) return;
      var perGram = amount / weightCols[idxStr];
      if (isBarDerivedGramPrice(perGram)) candidates[weightCols[idxStr]] = perGram;
    });
    for (var i = 0; i < PREFERRED_GRAM_ORDER.length; i++) {
      var grams = PREFERRED_GRAM_ORDER[i];
      if (candidates[grams] != null) return candidates[grams];
    }
    return null;
  }

  function isGoldBarTable(table) {
    var found = false;
    table.querySelectorAll('td').forEach(function (td) {
      if (textOf(td) === GOLD_BAR_ANCHOR) found = true;
    });
    if (found) return true;
    var summary = table.getAttribute('summary') || table.getAttribute('title') || '';
    if (summary.indexOf(GOLD_BAR_ANCHOR) >= 0 && summary.indexOf('存摺') < 0) return true;
    return ['黃金條塊歷史牌價', '黃金條塊牌價', '黃金條塊表格'].some(function (s) {
      return summary.indexOf(s) >= 0;
    });
  }

  function findGoldBarAnchor(doc) {
    var anchor = null;
    doc.querySelectorAll('td').forEach(function (td) {
      if (!anchor && textOf(td) === GOLD_BAR_ANCHOR) anchor = td;
    });
    return anchor;
  }

  function quotesFromLiveGoldBarBlock(doc, pageStamp) {
    var anchor = findGoldBarAnchor(doc);
    if (!anchor) return [];
    var table = anchor.closest('table');
    if (!table) return [];

    var weightCols = weightColumnsFromTable(table);
    if (!Object.keys(weightCols).length) return [];

    var anchorRow = anchor.closest('tr');
    var quotes = [];
    var started = !anchorRow;
    var rows = table.querySelectorAll('tr');

    for (var i = 0; i < rows.length; i++) {
      var row = rows[i];
      if (row === anchorRow) started = true;
      else if (!started) continue;

      var rowText = textOf(row);
      if (rowText.indexOf('轉換') >= 0) continue;
      if (rowText.indexOf('本行賣出') < 0 && !row.querySelector('td[data-table="本行賣出"]')) continue;

      var perGram = perGramFromBarSellRow(row, weightCols);
      if (perGram != null) {
        quotes.push([perGram, pageStamp || extractPageStamp(doc)]);
        break;
      }
    }
    return quotes;
  }

  function quotesFromHistoryTables(doc) {
    var quotes = [];
    doc.querySelectorAll('table').forEach(function (table) {
      var summary = table.getAttribute('summary') || table.getAttribute('title') || '';
      if (!isGoldBarTable(table)) return;
      if (summary.indexOf('黃金存摺') >= 0 && summary.indexOf('黃金條塊') < 0) return;

      var weightCols = weightColumnsFromTable(table);
      if (!Object.keys(weightCols).length) return;

      table.querySelectorAll('tr').forEach(function (row) {
        var rowText = textOf(row);
        if (rowText.indexOf('轉換') >= 0) return;
        var stamp = extractStampFromRow(row);
        var perGram = perGramFromBarSellRow(row, weightCols);
        if (perGram == null) return;
        if (rowText.indexOf('本行賣出') >= 0 || stamp) quotes.push([perGram, stamp]);
      });
    });
    return quotes;
  }

  function pickLatestQuote(quotes) {
    var best = null;
    var bestKey = null;
    quotes.forEach(function (entry) {
      var sell = entry[0];
      var stamp = entry[1];
      if (sell == null) return;
      var key = parseBotDatetime(stamp) || [0, 0, 0, 0, 0];
      if (!best || compareKey(key, bestKey) >= 0) {
        best = [sell, stamp];
        bestKey = key;
      }
    });
    return best;
  }

  function isBotChallenge(html) {
    if (!html || html.length < 10000) return true;
    var lowered = html.toLowerCase();
    return lowered.indexOf('challenge validation') >= 0 || lowered.indexOf('<title>challenge') >= 0;
  }

  function findGoldBarPrices(html) {
    var doc = new DOMParser().parseFromString(html, 'text/html');
    var pageStamp = extractPageStamp(doc);
    var quotes = quotesFromLiveGoldBarBlock(doc, pageStamp).concat(quotesFromHistoryTables(doc));
    if (!quotes.length) return null;

    var picked = pickLatestQuote(quotes);
    if (!picked || picked[0] == null) return null;
    return { perGram: picked[0], stamp: picked[1] || pageStamp };
  }

  global.parseBotGold = {
    findGoldBarPrices: findGoldBarPrices,
    isBotChallenge: isBotChallenge,
  };
})(window);
