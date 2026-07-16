/* 銘印鑽石｜共用價格設定
   說明給工程師/接手的人：
   - 這是全站唯一的「價格資料來源」。五大系列頁的客製選單(configurator.js)
     跟後台的「價格設定」頁(admin.html)都讀寫同一份資料，靠這支檔案串起來。
   - 價格真正存在 Postgres 的 pricing_settings 資料表
     (一筆固定 id=1 的 JSON)，透過 js/api-client.js 呼叫 FastAPI /api 讀寫，
     後台改一次，全站所有裝置都會同步看到新價格。
   - 為了讓頁面「立刻有數字可以顯示」不用整頁空白等網路，這裡同時把最後一次
     讀到的價格快取一份在瀏覽器的 localStorage：頁面一開場先用快取畫面，
     API 回應後如果有變動再重新整理畫面。真正的資料來源永遠是後端資料庫，
     localStorage 只是「上次看到的樣子」，不是可信來源。
   - DEFAULTS 裡標了「★官方資料」的數字，是官方報價單上的真實金額；
     其餘（尤其是飾品戒台費用矩陣）除了 9K 項鍊之外，都是先抓一個合理估算值
     佔位，正式報價請盡快在後台「價格設定」頁裡逐一修正。
   - 這支檔案必須在 api-client.js 之後載入(才吃得到 window.imprintAPI)，
     但要在 configurator.js 之前載入。

   多顆珍藏方案 / 稅金規則移植自 diamond calculator 專案(imprint-calculator，
   Flask 正式報價系統)的 diamond_options.py / pricing.py / order_pricing.py，
   取其「公式與資料」。該專案的資料庫金重查表(每個商品的實際克重)沒有搬過來，
   因為 V3 的商品線是全新設計，沒有對應的克重資料，mounting 目前仍是估算表。

   即時金價：排程腳本 scripts/fetch_gold_quote.py（GitHub Actions）更新
   data/gold-quote.json；線上則由 FastAPI GET /api/bot-gold 提供。
   getLiveGoldPrice() 透過 API 讀快取，目前 mounting 仍用估算表，金價僅供顯示參考。
*/
(function (global) {
  'use strict';

  var DEFAULTS = {
    /* ★官方資料：單顆鑽石價格,依顏色×克拉。找不到的組合(例如彩鑽 0.10/0.20)
       代表目前無法製作。 */
    diamond: {
      white: {
        '0.10': 24000, '0.20': 48000, '0.30': 79000, '0.50': 98000,
        '0.60': 113000, '0.70': 133000, '0.80': 159000, '0.90': 200000,
        '1.00': 250000, '1.50': 380000, '2.00': 700000, '3.00': 990000
      },
      fancy: {
        '0.30': 102000, '0.50': 127000, '0.60': 147000, '0.70': 172000,
        '0.80': 206000, '0.90': 260000, '1.00': 325000, '1.50': 494000,
        '2.00': 910000, '3.00': 1287000
      }
    },
    /* ★官方資料：非圓形切工一律加價 10%，且需 0.30 克拉以上才允許選取。 */
    shapeSurchargePct: 10,

    /* ★官方資料(價格頁「多顆珍藏方案」)：整組總價查表(非單顆×折扣估算)。
       只支援 2/3/4 顆(官網未公開 5 顆以上的整組報價，故不再猜測估算)。
       0.30 克拉以上：沿用 0.30 那一列 × multiStoneAbove03Multiplier 換算。 */
    whiteMultiDiamondPrice: {
      '0.10': { '2': 45600, '3': 61200, '4': 81000 },
      '0.20': { '2': 86400, '3': 122400, '4': 162000 },
      '0.30': { '2': 142200, '3': 189600, '4': 250000 }
    },
    coloredMultiDiamondPrice: {
      '0.30': { '2': 173400, '3': 244800, '4': 322300 }
    },
    multiStoneAbove03Multiplier: { '2': 0.85, '3': 0.80, '4': 0.75 },

    /* ★官方資料：鑽石牌價已含稅；飾品戒台費用(mounting)為未稅金額，
       顯示/加總時另外加稅(見 configurator.js 的 render())。 */
    taxRate: 0.05,

    /* 估算值：飾品戒台費用（依飾品款式 × 金屬材質，未稅）。
       只有「9K 經典款項鍊 NT$10,000 起」是官方公開的真實數字，
       其餘皆用倍率推算佔位，請儘快替換成正式報價。
       純銀(silver)為基本金屬，估算價低於 9K，且僅提供白色成色(見 configurator.js 的成色限制邏輯)。
       戒指戒圍加價與 diamond-calculator 同步，見 js/jewelry-mounting.js。 */
    mounting: {
      loose:    { '18k': 0,     '14k': 0,     '9k': 0,     'pt950': 0,     'silver': 0    },
      necklace: { '18k': 15000, '14k': 12500, '9k': 10000, 'pt950': 18000, 'silver': 7000 },
      ring:     { '18k': 18000, '14k': 15000, '9k': 12000, 'pt950': 21500, 'silver': 8000 },
      earring:  { '18k': 21000, '14k': 17500, '9k': 14000, 'pt950': 25000, 'silver': 9500 },
      bracelet: { '18k': 24000, '14k': 20000, '9k': 16000, 'pt950': 29000, 'silver': 11000 }
    },

    /* 估算值：腰圍刻字費用，預設 0（比照多數品牌基本刻字不加價）。 */
    engraveFee: 0
  };

  var STORAGE_KEY = 'imprintPricingOverridesV1';

  function isPlainObject(v) {
    return v && typeof v === 'object' && !Array.isArray(v);
  }

  function deepMerge(base, override) {
    if (!isPlainObject(override)) return base;
    var out = {};
    for (var k in base) { out[k] = base[k]; }
    for (var k2 in override) {
      if (isPlainObject(override[k2]) && isPlainObject(base[k2])) {
        out[k2] = deepMerge(base[k2], override[k2]);
      } else {
        out[k2] = override[k2];
      }
    }
    return out;
  }

  function loadLocalCache() {
    try {
      var raw = localStorage.getItem(STORAGE_KEY);
      return raw ? JSON.parse(raw) : null;
    } catch (e) {
      return null;
    }
  }

  function saveLocalCache(overrides) {
    try { localStorage.setItem(STORAGE_KEY, JSON.stringify(overrides)); } catch (e) { /* 忽略無痕模式等寫入失敗 */ }
  }

  var currentOverrides = loadLocalCache() || {};

  function getAll() {
    return deepMerge(DEFAULTS, currentOverrides);
  }

  function hasOverrides() {
    return !!(currentOverrides && Object.keys(currentOverrides).length);
  }

  /* 頁面一載入就去後端 API 拿最新價格；ready 讓呼叫端知道「這是不是已經是最新資料」。
     連線失敗時也會 resolve，讓頁面至少能用預設值/舊快取運作。 */
  var ready = new Promise(function (resolve) {
    if (!global.imprintAPI) { resolve(); return; }
    global.imprintAPI.getPricingOverrides().then(function (res) {
      if (res && !res.error && isPlainObject(res.overrides)) {
        currentOverrides = res.overrides;
        saveLocalCache(currentOverrides);
      }
      resolve();
    }, function () {
      resolve(); // 連線失敗就沿用本機快取/預設值，不擋頁面
    });
  });

  function saveOverrides(overrides) {
    currentOverrides = overrides;
    saveLocalCache(overrides);
    if (!global.imprintAPI) return Promise.resolve({ error: '尚未連上後端 API' });
    return global.imprintAPI.savePricingOverrides(overrides);
  }

  function resetOverrides() {
    return saveOverrides({});
  }

  /* 鑽石總價試算(移植自 imprint-calculator 的 compute_diamond_list_price)。
     qty=1 走單顆價格表；qty=2/3/4 走「多顆珍藏方案」整組查表(非單顆×折扣)；
     0.30 克拉以上且不在表中的克拉數，沿用 0.30 那一列 × 倍率換算。
     非圓形切工的加價，統一在最後對「整組總價」加一次，不是對單顆加價後再乘倍數。
     找不到對應組合(例如彩鑽 0.10/0.20、5 顆以上)一律回傳 null。 */
  function computeDiamondPrice(pricing, colorVal, caratVal, shapeVal, qty) {
    if (!caratVal) return null;
    var caratNum = parseFloat(caratVal);
    if (isNaN(caratNum)) return null; // 例如 'custom'（客製克拉另洽顧問，不試算）

    var isRound = !shapeVal || shapeVal === 'round';
    if (!isRound && caratNum < 0.30) return null; // 非圓形切工需 0.30 克拉以上

    var base = null;
    var q = qty && qty > 1 ? String(qty) : null;

    if (q) {
      var table = colorVal === 'fancy' ? pricing.coloredMultiDiamondPrice : pricing.whiteMultiDiamondPrice;
      table = table || {};
      if (table[caratVal] && table[caratVal][q] != null) {
        base = table[caratVal][q];
      } else if (caratNum > 0.30) {
        var row = table['0.30'];
        var mult = pricing.multiStoneAbove03Multiplier ? pricing.multiStoneAbove03Multiplier[q] : null;
        if (row && row[q] != null && mult) {
          base = Math.round(row[q] * mult);
        }
      }
    } else {
      var singleTable = pricing.diamond[colorVal] || {};
      base = singleTable[caratVal] != null ? singleTable[caratVal] : null;
    }

    if (base == null) return null;
    if (!isRound) {
      base = Math.round(base * (1 + (pricing.shapeSurchargePct || 0) / 100));
    }
    return base;
  }

  /* 讀取 gold_price_cache 的即時金價(僅供顯示參考，
     目前站上任何試算都不吃這個值)。回傳 { xauPerGram, xptPerGram, xagPerGram,
     botPostedAt, fetchedAt } 或 null(尚未部署爬蟲 / 查無資料 / 連線失敗)。 */
  function getLiveGoldPrice() {
    if (!global.imprintAPI) return Promise.resolve(null);
    return global.imprintAPI.getLiveGoldPrice().then(function (res) {
      if (!res || res.error || !res.price) return null;
      var d = res.price;
      return {
        xauPerGram: d.xau_per_gram,
        xptPerGram: d.xpt_per_gram,
        xagPerGram: d.xag_per_gram,
        botPostedAt: d.bot_posted_at,
        fetchedAt: d.fetched_at
      };
    }, function () {
      return null; // 讀取失敗就當作沒有即時金價，不擋頁面
    });
  }

  global.ImprintPricing = {
    DEFAULTS: DEFAULTS,
    ready: ready,
    getAll: getAll,
    saveOverrides: saveOverrides,
    resetOverrides: resetOverrides,
    hasOverrides: hasOverrides,
    computeDiamondPrice: computeDiamondPrice,
    getLiveGoldPrice: getLiveGoldPrice
  };
})(window);
