/* Gold price page — BOT quote via /api/bot-gold or embedded/static fallback (no imprint API). */
(function (global) {
  'use strict';

  var CHIN_TO_GRAMS = 3.75;
  var GOLD_UNITS = ['g', 'chin', 'tael'];
  var BOT_JSON = '/api/bot-gold';
  var BOT_PHP = '/api/bot-gold.php';
  var BOT_PROXY = '/bot-gold';
  var BOT_PUBLIC_RECENT = 'https://rate.bot.com.tw/gold/quote/recent';
  var CACHE_KEY = 'imprintGoldQuoteCache';
  var STATIC_QUOTE_URL = 'data/gold-quote.json';

  var BOT_SOURCES = [
    { path: '/gold/quote/recent', sourceUrl: BOT_PUBLIC_RECENT },
    { path: '/gold?Lang=zh-TW', sourceUrl: 'https://rate.bot.com.tw/gold?Lang=zh-TW' },
  ];

  var PURITY_LABELS = {
    '9k': '9K 金',
    '14k': '14K 金',
    '18k': '18K 金',
    pt950: 'Pt950',
    s925: 'S925 銀',
  };
  var PURITY_MULTIPLIER = { '9k': 0.5, '14k': 0.75, '18k': 0.85, pt950: 1.1, s925: 0.925 };
  var METAL_BASE = { '9k': 'XAU', '14k': 'XAU', '18k': 'XAU', pt950: 'XPT', s925: 'XAG' };
  var FALLBACK_XAU = 4300;
  var FALLBACK_XPT = 1050;
  var FALLBACK_XAG = 30;
  var liveReady = false;

  var SOURCE_PILL = {
    bot: { cls: 'source-pill--bot', label: '台銀牌價' },
    cached: { cls: 'source-pill--cached', label: '沿用上次牌價' },
    fallback: { cls: 'source-pill--fallback', label: '備援牌價' },
  };

  function canFetchHttp() {
    return global.location && /^https?:$/i.test(global.location.protocol);
  }

  function staticQuoteUrl() {
    try {
      return new URL(STATIC_QUOTE_URL, global.location.href).href;
    } catch (_) {
      return STATIC_QUOTE_URL;
    }
  }

  function formatTwd(value) {
    return 'NT$ ' + Math.round(value).toLocaleString('en-US');
  }

  function formatFetchedAt(date) {
    try {
      return date.toLocaleString('zh-TW', { timeZone: 'Asia/Taipei', hour12: false });
    } catch (_) {
      return '';
    }
  }

  function buildAlloyRates(raw) {
    var alloy = {};
    Object.keys(PURITY_LABELS).forEach(function (gold) {
      var symbol = METAL_BASE[gold];
      if (raw[symbol] != null) alloy[gold] = raw[symbol] * PURITY_MULTIPLIER[gold];
    });
    return alloy;
  }

  function buildPayloadFromQuote(quote, alloyRates, extra) {
    extra = extra || {};
    return {
      refreshed: !!extra.refreshed,
      fromCache: !!extra.fromCache,
      fromStatic: !!extra.fromStatic,
      fromBootstrap: !!extra.fromBootstrap,
      fromFallback: !!extra.fromFallback,
      quote: quote,
      alloyRates: alloyRates,
    };
  }

  function buildPayloadFromBot(parsed, extra) {
    extra = extra || {};
    var raw = { XAU: parsed.perGram, XPT: FALLBACK_XPT, XAG: FALLBACK_XAG };
    var now = new Date();
    return buildPayloadFromQuote({
      available: true,
      sell: parsed.perGram,
      source: 'bot',
      bot_posted_at: parsed.stamp || null,
      fetched_at: now.toISOString(),
      fetched_at_display: formatFetchedAt(now),
      is_stale: false,
      source_url: extra.sourceUrl || BOT_PUBLIC_RECENT,
    }, buildAlloyRates(raw), { refreshed: true });
  }

  function fallbackPayload() {
    return buildPayloadFromQuote({
      available: true,
      sell: FALLBACK_XAU,
      source: 'fallback',
      bot_posted_at: null,
      fetched_at_display: null,
      is_stale: true,
      source_url: BOT_PUBLIC_RECENT,
    }, buildAlloyRates({ XAU: FALLBACK_XAU, XPT: FALLBACK_XPT, XAG: FALLBACK_XAG }), { fromFallback: true });
  }

  function readBootstrap() {
    var data = global.__GOLD_QUOTE_BOOTSTRAP__;
    if (!data || !data.quote || !data.quote.available) return null;
    var quote = Object.assign({}, data.quote, {
      source: 'cached',
      is_stale: true,
    });
    return buildPayloadFromQuote(quote, data.alloyRates, { fromBootstrap: true });
  }

  function readCache() {
    try {
      var raw = localStorage.getItem(CACHE_KEY);
      if (!raw) return null;
      var data = JSON.parse(raw);
      if (!data || !data.quote || !data.quote.available) return null;
      return buildPayloadFromQuote(data.quote, data.alloyRates, { fromCache: true });
    } catch (_) {
      return null;
    }
  }

  function writeCache(data) {
    if (!data || !data.quote || !data.quote.available) return;
    try {
      localStorage.setItem(CACHE_KEY, JSON.stringify({
        quote: data.quote,
        alloyRates: data.alloyRates,
        saved_at: new Date().toISOString(),
      }));
    } catch (_) {}
  }

  function parseHtmlToPayload(html, sourceUrl) {
    if (!global.parseBotGold) throw new Error('parser missing');
    if (global.parseBotGold.isBotChallenge(html)) throw new Error('BOT challenge');
    var parsed = global.parseBotGold.findGoldBarPrices(html);
    if (!parsed) throw new Error('parse failed');
    var payload = buildPayloadFromBot(parsed, { sourceUrl: sourceUrl || BOT_PUBLIC_RECENT });
    writeCache(payload);
    return payload;
  }

  function fetchBotJsonEndpoint() {
    if (!canFetchHttp()) return Promise.reject(new Error('no http'));
    return fetch(BOT_JSON, { cache: 'no-store' })
      .then(function (res) {
        if (!res.ok) throw new Error('HTTP ' + res.status);
        return res.json();
      })
      .then(function (data) {
        if (data.error || !data.quote || !data.quote.available) {
          throw new Error(data.error || '無法取得台銀牌價');
        }
        writeCache(data);
        return Object.assign({}, data, { refreshed: true });
      });
  }

  function fetchBotPhpEndpoint() {
    if (!canFetchHttp()) return Promise.reject(new Error('no http'));
    return fetch(BOT_PHP, { cache: 'no-store' })
      .then(function (res) {
        if (!res.ok) throw new Error('HTTP ' + res.status);
        return res.json();
      })
      .then(function (data) {
        if (data.error || !data.html) throw new Error(data.error || 'PHP fetch failed');
        return parseHtmlToPayload(data.html, data.source_url);
      });
  }

  function fetchBotHtml(relativePath) {
    return fetch(BOT_PROXY + relativePath, {
      credentials: 'same-origin',
      cache: 'no-store',
      headers: {
        'Accept-Language': 'zh-TW,zh;q=0.9,en;q=0.8',
        Accept: 'text/html,application/xhtml+xml',
      },
    }).then(function (res) {
      if (!res.ok) throw new Error('台銀 HTTP ' + res.status);
      return res.text();
    });
  }

  function fetchFromBotProxy() {
    if (!canFetchHttp() || !global.parseBotGold) {
      return Promise.reject(new Error('proxy unavailable'));
    }

    var lastError = null;

    function trySource(index) {
      if (index >= BOT_SOURCES.length) {
        return Promise.reject(lastError || new Error('無法取得台銀牌價'));
      }
      var src = BOT_SOURCES[index];
      return fetchBotHtml(src.path)
        .then(function (html) {
          return parseHtmlToPayload(html, src.sourceUrl);
        })
        .catch(function (err) {
          lastError = err;
          return trySource(index + 1);
        });
    }

    return trySource(0);
  }

  function fetchStaticQuote() {
    if (!canFetchHttp()) return Promise.reject(new Error('no http'));
    return fetch(staticQuoteUrl() + '?t=' + Date.now(), { cache: 'no-store' })
      .then(function (res) {
        if (!res.ok) throw new Error('static quote missing');
        return res.json();
      })
      .then(function (data) {
        if (!data || !data.quote || !data.quote.available) throw new Error('static quote invalid');
        writeCache(data);
        var quote = Object.assign({}, data.quote, {
          source: 'cached',
          is_stale: true,
        });
        return buildPayloadFromQuote(quote, data.alloyRates, { fromStatic: true });
      });
  }

  function resolveQuoteChain(liveFirst) {
    var chain = liveFirst
      ? [fetchBotJsonEndpoint, fetchBotPhpEndpoint, fetchFromBotProxy, fetchStaticQuote, readCache, readBootstrap, fallbackPayload]
      : [fetchStaticQuote, readCache, readBootstrap, fetchBotJsonEndpoint, fetchBotPhpEndpoint, fetchFromBotProxy, fallbackPayload];

    function next(i) {
      if (i >= chain.length) return Promise.resolve(fallbackPayload());
      var step = chain[i];
      var result = typeof step === 'function' ? step() : step;
      if (!result || typeof result.then !== 'function') {
        if (result && result.quote && result.quote.available) return Promise.resolve(result);
        return next(i + 1);
      }
      return result.catch(function () { return next(i + 1); });
    }

    return next(0);
  }

  function fetchGoldQuote() {
    return resolveQuoteChain(false);
  }

  function refreshGoldQuote() {
    return resolveQuoteChain(true);
  }

  function probeLiveEndpoint() {
    if (!canFetchHttp()) return Promise.resolve(false);

    function probeJson(url, isPhp) {
      return fetch(url, { cache: 'no-store' })
        .then(function (res) {
          if (!res.ok) return false;
          return res.json().then(function (d) {
            if (isPhp) return !!(d.html && d.html.length > 10000 && !d.error);
            return !!(d.quote && d.quote.available && !d.error);
          }).catch(function () { return false; });
        })
        .catch(function () { return false; });
    }

    return probeJson(BOT_JSON, false).then(function (ok) {
      if (ok) return true;
      return probeJson(BOT_PHP, true);
    });
  }

  function updateLiveHint(ok) {
    liveReady = ok;
    var el = document.getElementById('gold-live-hint');
    if (!el) return;
    if (ok) {
      el.classList.add('hidden');
      el.textContent = '';
      return;
    }
    el.classList.remove('hidden');
    el.innerHTML = '目前無即時抓取。若網站部署在 Render（Node Web Service），請確認 Build：<code>npm install && npm install --prefix backend</code>、Start：<code>npm start</code>。本機開發：<code>npm run dev</code>。';
  }

  function refreshMessage(data) {
    if (data.refreshed) return { text: '牌價已更新', ok: true };
    if (data.fromCache) return { text: '顯示瀏覽器快取牌價', ok: false };
    if (data.fromStatic || data.fromBootstrap) {
      if (liveReady) return { text: '已載入備援牌價', ok: true };
      return { text: '仍為備援牌價。Render 部署請使用 Node Web Service（npm start）', ok: false };
    }
    if (data.fromFallback) return { text: '顯示預設備援牌價', ok: false };
    return { text: '牌價已更新', ok: true };
  }

  function currentUnit() {
    var stored = localStorage.getItem('goldPriceUnit');
    return GOLD_UNITS.indexOf(stored) >= 0 ? stored : 'g';
  }

  function unitFactor() {
    var unit = currentUnit();
    if (unit === 'chin') return CHIN_TO_GRAMS;
    if (unit === 'tael') return CHIN_TO_GRAMS * 10;
    return 1;
  }

  function unitSuffix() {
    return { g: '/ 公克', chin: '/ 錢', tael: '/ 兩' }[currentUnit()];
  }

  function renderSourcePill(source) {
    var badge = document.getElementById('gold-source-badge');
    if (!badge) return;
    var meta = SOURCE_PILL[source] || SOURCE_PILL.fallback;
    badge.innerHTML = '<span class="source-pill ' + meta.cls + '">' + meta.label + '</span>';
  }

  function setVisible(id, show) {
    var el = document.getElementById(id);
    if (el) el.classList.toggle('hidden', !show);
  }

  function applyQuote(data) {
    var q = data.quote || {};
    var loading = document.getElementById('gold-price-loading');
    if (loading) loading.classList.add('hidden');

    if (!q.available) {
      setVisible('gold-price-live', false);
      setVisible('gold-price-empty', true);
      return false;
    }

    setVisible('gold-price-empty', false);
    setVisible('gold-price-live', true);
    renderSourcePill(q.source || 'fallback');

    var sellEl = document.getElementById('gold-sell-val');
    if (sellEl && q.sell != null) {
      sellEl.dataset.perGram = String(q.sell);
      sellEl.textContent = formatTwd(q.sell * unitFactor());
    }

    var link = document.getElementById('gold-source-link');
    if (link && q.source_url) link.href = q.source_url;

    var updatedEl = document.getElementById('gold-updated-line');
    if (updatedEl) {
      if (q.bot_posted_at) {
        updatedEl.textContent = '掛牌時間：' + q.bot_posted_at;
        updatedEl.classList.remove('hidden');
      } else updatedEl.classList.add('hidden');
    }

    var fetchedEl = document.getElementById('gold-fetched-line');
    if (fetchedEl) {
      if (q.fetched_at_display) {
        fetchedEl.textContent = '資料擷取時間：' + q.fetched_at_display;
        fetchedEl.classList.remove('hidden');
      } else fetchedEl.classList.add('hidden');
    }

    var staleEl = document.getElementById('gold-stale-warning');
    if (staleEl) staleEl.classList.toggle('hidden', !q.is_stale);

    var tbody = document.querySelector('#gold-alloy-table tbody');
    if (tbody && data.alloyRates) {
      tbody.innerHTML = Object.keys(PURITY_LABELS).map(function (gold) {
        var rate = data.alloyRates[gold];
        if (rate == null) return '';
        return '<tr><td>' + PURITY_LABELS[gold] + '</td><td class="gold-alloy-rate" data-per-gram="' + rate + '">' +
          Math.round(rate * unitFactor()).toLocaleString('en-US') + '</td></tr>';
      }).join('');
    }

    renderUnitUi();
    return true;
  }

  function renderUnitUi() {
    var unit = currentUnit();
    document.querySelectorAll('.gold-unit-btn').forEach(function (b) {
      b.classList.toggle('active', b.dataset.unit === unit);
    });

    var sellEl = document.getElementById('gold-sell-val');
    if (sellEl) {
      var perGram = parseFloat(sellEl.dataset.perGram);
      if (!isNaN(perGram)) sellEl.textContent = formatTwd(perGram * unitFactor());
    }

    var unitEl = document.getElementById('gold-sell-unit');
    if (unitEl) unitEl.textContent = unitSuffix();

    document.querySelectorAll('.gold-alloy-rate').forEach(function (td) {
      var perGram = parseFloat(td.dataset.perGram);
      if (!isNaN(perGram)) td.textContent = Math.round(perGram * unitFactor()).toLocaleString('en-US');
    });

    var heading = document.getElementById('gold-alloy-heading');
    if (heading) {
      var suffix = { g: '/ 公克', chin: '/ 錢', tael: '/ 兩' }[unit];
      heading.textContent = '試算用成色金價（NT$ ' + suffix.trim() + '）';
    }
  }

  function showMsg(text, ok) {
    var el = document.getElementById('gold-refresh-msg');
    if (!el) return;
    el.textContent = text;
    el.classList.remove('hidden', 'gold-refresh-msg--ok', 'gold-refresh-msg--err');
    el.classList.add(ok ? 'gold-refresh-msg--ok' : 'gold-refresh-msg--err');
  }

  function init() {
    document.querySelectorAll('.gold-unit-btn').forEach(function (b) {
      b.addEventListener('click', function () {
        localStorage.setItem('goldPriceUnit', b.dataset.unit);
        renderUnitUi();
      });
    });

    var refreshBtn = document.getElementById('gold-refresh-btn');
    if (refreshBtn) {
      refreshBtn.addEventListener('click', function () {
        refreshBtn.disabled = true;
        refreshBtn.classList.add('is-loading');
        showMsg('抓取中…', true);
        refreshGoldQuote()
          .then(function (data) {
            applyQuote(data);
            return probeLiveEndpoint().then(function (ok) {
              updateLiveHint(ok);
              return data;
            });
          })
          .then(function (data) {
            var msg = refreshMessage(data);
            showMsg(msg.text, msg.ok);
          })
          .catch(function () {
            applyQuote(fallbackPayload());
            showMsg('顯示預設備援牌價', false);
          })
          .finally(function () {
            refreshBtn.disabled = false;
            refreshBtn.classList.remove('is-loading');
          });
      });
    }

    probeLiveEndpoint().then(function (ok) {
      updateLiveHint(ok);
      fetchGoldQuote().then(applyQuote);
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})(window);
