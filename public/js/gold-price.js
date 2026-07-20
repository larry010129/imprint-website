/* Gold price page — live quote via GET /api/bot-gold (FastAPI / gunicorn on Render). */
(function (global) {
  'use strict';

  var API_URL = '/api/bot-gold';
  var BOT_PUBLIC_RECENT = 'https://rate.bot.com.tw/gold/quote/recent';
  var CACHE_KEY = 'imprintGoldQuoteCache';
  var CHIN_TO_GRAMS = 3.75;
  var GOLD_UNITS = ['g', 'chin', 'tael'];

  var PURITY_LABELS = {
    '9k': '9K 金',
    '14k': '14K 金',
    '18k': '18K 金',
    pt950: 'Pt950',
    s925: 'S925 銀',
  };

  var SOURCE_PILL = {
    bot: { cls: 'source-pill--bot', label: '台銀牌價' },
    cached: { cls: 'source-pill--cached', label: '沿用上次牌價' },
    fallback: { cls: 'source-pill--fallback', label: '備援牌價' },
  };

  var FALLBACK_XAU = 4300;
  var liveReady = false;

  function formatTwd(value) {
    return 'NT$ ' + Math.round(value).toLocaleString('en-US');
  }

  function readBootstrap() {
    var data = global.__GOLD_QUOTE_BOOTSTRAP__;
    if (!data || !data.quote || !data.quote.available) return null;
    return {
      refreshed: false,
      fromBootstrap: true,
      quote: Object.assign({}, data.quote, { source: 'cached', is_stale: true }),
      alloyRates: data.alloyRates,
    };
  }

  function readCache() {
    try {
      var raw = localStorage.getItem(CACHE_KEY);
      if (!raw) return null;
      var data = JSON.parse(raw);
      if (!data || !data.quote || !data.quote.available) return null;
      return {
        refreshed: false,
        fromCache: true,
        quote: data.quote,
        alloyRates: data.alloyRates,
      };
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

  function fallbackPayload() {
    var sell = FALLBACK_XAU;
    return {
      refreshed: false,
      fromFallback: true,
      quote: {
        available: true,
        sell: sell,
        source: 'fallback',
        bot_posted_at: null,
        fetched_at_display: null,
        is_stale: true,
        source_url: BOT_PUBLIC_RECENT,
      },
      alloyRates: {
        '9k': sell * 0.5,
        '14k': sell * 0.75,
        '18k': sell * 0.85,
        pt950: 1050 * 1.1,
        s925: 30 * 0.925,
      },
    };
  }

  /** Live BOT quote from FastAPI server (Render / dev.bat). */
  function fetchLiveQuote() {
    return fetch(API_URL, { cache: 'no-store' })
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

  function fetchGoldQuote() {
    return fetchLiveQuote()
      .catch(function () { return readCache(); })
      .catch(function () { return readBootstrap(); })
      .catch(function () { return fallbackPayload(); });
  }

  function refreshGoldQuote() {
    return fetchLiveQuote().catch(function () {
      var cached = readCache() || readBootstrap();
      if (cached) return Object.assign({}, cached, { refreshed: false });
      return fallbackPayload();
    });
  }

  function probeLiveEndpoint() {
    return fetch(API_URL, { cache: 'no-store' })
      .then(function (res) {
        if (!res.ok) return false;
        return res.json().then(function (d) {
          return !!(d.quote && d.quote.available && !d.error);
        }).catch(function () { return false; });
      })
      .catch(function () { return false; });
  }

  function updateLiveHint(ok) {
    liveReady = ok;
    var el = document.getElementById('gold-live-hint');
    if (!el) return;
    if (ok) {
      el.classList.add('hidden');
      return;
    }
    el.classList.remove('hidden');
    el.textContent = '無法連線即時 API。Render 請使用 Python Web Service，Start：gunicorn main:app -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:$PORT。本機：dev.bat。';
  }

  function refreshMessage(data) {
    if (data.refreshed) return { text: '牌價已更新', ok: true };
    if (data.fromCache || data.fromBootstrap) {
      return { text: liveReady ? '台銀暫時無回應，顯示備援牌價' : '顯示備援牌價（需 FastAPI 伺服器才能即時抓取）', ok: false };
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
      heading.textContent = '試算用成色金價（約 NT$ ' + suffix.trim() + '）';
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
            showMsg('無法更新牌價', false);
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
