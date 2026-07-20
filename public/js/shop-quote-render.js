/* Shared quote / share summary renderer — client-side, no /api/quote needed. */
(function (global) {
  'use strict';

  var CAT_ZH = { pendant: '項墜', ring: '戒指', earring: '耳飾', bracelet: '手鍊', chain: '鍊條' };
  var GOLD_ZH = { '9k': '9K', '14k': '14K', '18k': '18K', pt950: 'PT950', s925: '925銀' };
  var COLOR_ZH = { white: '白金', yellow: '黃金', rose: '玫瑰金' };
  var DIAMOND_COLOR_ZH = { white: '白鑽', yellow: '黃鑽', blue: '藍鑽', pink: '粉鑽' };
  var STYLE_ID = /^([a-z]+)-([A-C])$/i;
  var UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

  function esc(text) {
    var el = document.createElement('span');
    el.textContent = text == null ? '' : String(text);
    return el.innerHTML;
  }

  function fmt(n) {
    if (n == null || Number.isNaN(Number(n))) return '—';
    return Number(n).toLocaleString('zh-TW', { maximumFractionDigits: 0 });
  }

  function materialLabel(gold, color) {
    if (!gold) return '—';
    var g = GOLD_ZH[gold] || gold;
    if (gold === 'pt950' || gold === 's925') return g;
    var c = COLOR_ZH[color] || COLOR_ZH.white;
    return g + c;
  }

  function caratLabel(carat) {
    if (!carat) return '—';
    if (carat === '3fen') return '3分';
    if (carat === '4fen') return '4分';
    return carat + 'ct';
  }

  function formatDate(d) {
    var p = function (n) { return String(n).padStart(2, '0'); };
    return d.getFullYear() + '/' + p(d.getMonth() + 1) + '/' + p(d.getDate())
      + ' ' + p(d.getHours()) + ':' + p(d.getMinutes());
  }

  function urlAttr(url) {
    return String(url || '').replace(/"/g, '%22');
  }

  function diamondColorId(config) {
    if (!config || config.category === 'chain') return '';
    if (config.diamondColor) return config.diamondColor;
    if (config.diamondKind === 'white') return 'white';
    return config.fancyColor || '';
  }

  function diamondColorLabel(config) {
    var id = diamondColorId(config);
    if (!id) return '';
    return DIAMOND_COLOR_ZH[id] || id;
  }

  function resolveStyleKey(config) {
    if (!config) return '';
    if (config.styleKey && STYLE_ID.test(String(config.styleKey))) return String(config.styleKey);
    var type = String(config.type || '').trim();
    if (STYLE_ID.test(type)) return type;
    var cat = String(config.category || '').toLowerCase();
    if (cat && type.length === 1 && 'ABC'.indexOf(type) >= 0) return cat + '-' + type;
    if (cat && UUID.test(type)) return config.styleKey || '';
    return '';
  }

  function colorLabel(color) {
    if (!color) return '';
    return COLOR_ZH[color] || color;
  }

  function isGenericThumb(url) {
    return /\/thumbs\//i.test(String(url || ''));
  }

  function productImage(config) {
    var previewPrimary = config.previewImage || '';
    var previewChain = config.previewChainImage || '';

    /* Calculator captures the live preview — trust it over static thumb fallbacks */
    if (previewPrimary && previewChain) {
      return { composite: true, pendant: previewPrimary, chain: previewChain };
    }
    if (previewPrimary && !isGenericThumb(previewPrimary)) {
      return { primary: previewPrimary, fallback: '' };
    }

    var styleKey = resolveStyleKey(config);
    if (!global.ShopAssets || !styleKey) {
      if (previewPrimary) return { primary: previewPrimary, fallback: '' };
      var catOnly = global.ShopAssets ? (global.ShopAssets.categoryThumb(config.category) || '') : '';
      return { primary: catOnly, fallback: '' };
    }
    var pendantOnly = config.category === 'pendant' && !config.includeChain;
    var withChain = config.category === 'pendant' && config.includeChain;
    var pendantMetal = config.color || config.defaultColor || 'white';
    var chainMetal = (withChain && config.chainColor) ? config.chainColor : pendantMetal;
    var defaultColor = config.defaultColor || pendantMetal;
    var diamond = diamondColorId(config) || 'white';
    if (withChain) {
      var fullCombo = global.ShopAssets.productImage(styleKey, pendantMetal, defaultColor, diamond, { chainColor: chainMetal });
      if (fullCombo && !isGenericThumb(fullCombo) && !/_(?:only|chain)\.[a-z0-9]+$/i.test(fullCombo)) {
        return { primary: fullCombo, fallback: '' };
      }
      var pendantLayer = global.ShopAssets.productImage(styleKey, pendantMetal, defaultColor, diamond, { pendantOnly: true });
      var chainLayer = global.ShopAssets.productImage(styleKey, chainMetal, defaultColor, 'white', { chainOnly: true });
      if (pendantLayer && chainLayer && !isGenericThumb(pendantLayer) && !isGenericThumb(chainLayer)) {
        return { composite: true, pendant: pendantLayer, chain: chainLayer };
      }
    }
    var fullOpts = { pendantOnly: withChain ? false : pendantOnly };
    if (withChain) fullOpts.chainColor = chainMetal;
    var resolved = global.ShopAssets.productImageWithFallback
      ? global.ShopAssets.productImageWithFallback(styleKey, pendantMetal, defaultColor, diamond, fullOpts)
      : global.ShopAssets.productImage(styleKey, pendantMetal, defaultColor, diamond, fullOpts);
    if (typeof resolved === 'object' && resolved && resolved.primary && !isGenericThumb(resolved.primary)) {
      if (diamond !== 'white') resolved.fallback = '';
      return resolved;
    }
    if (resolved && !isGenericThumb(resolved)) return { primary: resolved, fallback: '' };
    if (previewPrimary) return { primary: previewPrimary, fallback: '' };
    var thumb = global.ShopAssets.styleThumb(styleKey);
    if (thumb) return { primary: thumb, fallback: '' };
    var cat = global.ShopAssets.categoryThumb(config.category);
    return cat ? { primary: cat, fallback: '' } : { primary: '', fallback: '' };
  }

  function specRows(config) {
    var rows = [
      { label: '品項', value: CAT_ZH[config.category] || config.category || '—' },
      { label: '款式', value: config.summaryZh || '訂製品項' },
      { label: '金屬材質', value: materialLabel(config.gold, config.color) },
      { label: '克拉', value: caratLabel(config.carat) },
    ];
    var diamondLabel = diamondColorLabel(config);
    if (diamondLabel) rows.push({ label: '鑽石顏色', value: diamondLabel });
    if (config.ringSize) rows.push({ label: '戒圍', value: String(config.ringSize) });
    if (config.lengthCm) rows.push({ label: '長度', value: config.lengthCm + ' cm' });
    if (config.category === 'pendant' && config.includeChain) {
      var pendantColorVal = colorLabel(config.color || config.defaultColor)
        || (config.gold === 'pt950' || config.gold === 's925' ? materialLabel(config.gold, config.color) : '');
      var chainColorVal = materialLabel(config.chainGold, config.chainColor);
      if (pendantColorVal) rows.push({ label: '項墜顏色', value: pendantColorVal });
      if (chainColorVal) rows.push({ label: '鍊條顏色', value: chainColorVal });
      if (config.chainLength) rows.push({ label: '鍊條長度', value: config.chainLength + ' cm' });
    } else if (config.includeChain) {
      rows.push({ label: '搭配鍊條', value: materialLabel(config.chainGold, config.chainColor) || '是' });
    }
    return rows;
  }

  function breakdownRows(pricing) {
    if (!pricing || pricing.manualOverride) return [];
    var rows = [];
    if (pricing.diamondPrice != null && pricing.diamondPrice > 0) {
      rows.push({ label: '鑽石價格', value: 'NT$ ' + fmt(pricing.diamondPrice) });
    }
    var metalwork = pricing.metalworkPrice != null
      ? pricing.metalworkPrice
      : (pricing.taijinPrice != null && pricing.laborPrice != null ? pricing.taijinPrice + pricing.laborPrice : null);
    if (metalwork != null) rows.push({ label: '金工價格', value: 'NT$ ' + fmt(metalwork) });
    if (pricing.chainPrice != null) rows.push({ label: '搭配鏈條', value: 'NT$ ' + fmt(pricing.chainPrice) });
    return rows;
  }

  function renderCard(config, opts) {
    opts = opts || {};
    var mode = opts.mode || 'quote';
    var pricing = config.clientPricing || {};
    var total = pricing.total;
    var imgInfo = productImage(config);
    var imgComposite = imgInfo.composite && imgInfo.pendant && imgInfo.chain;
    var imgSrc = imgInfo.primary || imgInfo.pendant || '';
    var imgChain = imgInfo.chain || '';
    var imgFallback = imgInfo.fallback || '';
    var now = formatDate(new Date());
    var title = mode === 'share' ? '試算分享' : '珠寶訂製報價單';
    var subtitle = mode === 'share'
      ? '以下為當下規格之參考試算，可分享給親友或業務確認。'
      : '本報價單依目前金價與牌價試算，供存檔或列印使用。';

    var specs = specRows(config).map(function (row) {
      return '<div class="share-spec-row"><dt>' + esc(row.label) + '</dt><dd>' + esc(row.value) + '</dd></div>';
    }).join('');

    var breakdown = breakdownRows(pricing).map(function (row) {
      return '<div class="share-spec-row share-spec-row--price"><dt>' + esc(row.label) + '</dt><dd>' + esc(row.value) + '</dd></div>';
    }).join('');

    var actions = mode === 'share'
      ? '<div class="share-actions">'
        + '<button type="button" class="share-btn share-btn--primary" id="share-copy-link">複製連結</button>'
        + '<a class="share-btn share-btn--ghost" href="/shop/calculator/">重新試算</a>'
        + '</div>'
      : '<footer class="share-actions share-actions--end">'
        + '<button type="button" class="share-btn share-btn--primary" id="quote-print-btn">列印 / 儲存 PDF</button>'
        + '<a class="share-btn share-btn--ghost" href="/shop/calculator/">返回試算</a>'
        + '</footer>';

    return ''
      + '<article class="share-card share-card--' + mode + '">'
      + '<p class="share-brand">IMPRINT DIAMOND · 銘印鑽石</p>'
      + '<header class="share-card-header">'
      + '<div><h1>' + esc(title) + '</h1><p class="share-card-sub">' + esc(subtitle) + '</p></div>'
      + '<time class="share-card-time" datetime="' + esc(new Date().toISOString()) + '">' + esc(now) + '</time>'
      + '</header>'
      + '<section class="share-hero">'
      + (imgComposite
        ? '<div class="share-image-composite">'
          + '<img class="share-image share-image--chain" src="' + urlAttr(imgChain) + '" alt="">'
          + '<img class="share-image share-image--pendant" src="' + urlAttr(imgSrc) + '" alt="">'
          + '</div>'
        : (imgSrc
          ? '<img class="share-image" src="' + urlAttr(imgSrc) + '" alt=""'
            + (imgFallback ? ' data-fallback="' + urlAttr(imgFallback) + '"' : '') + '>'
          : ''))
      + '<div class="share-hero-copy">'
      + '<p class="share-category">' + esc(CAT_ZH[config.category] || config.category || '') + '</p>'
      + '<h2>' + esc(config.summaryZh || '訂製品項') + '</h2>'
      + '</div>'
      + '</section>'
      + '<dl class="share-specs">' + specs + '</dl>'
      + (breakdown ? '<section class="share-breakdown"><h3 class="share-section-title">價格明細</h3><dl class="share-specs share-specs--breakdown">' + breakdown + '</dl></section>' : '')
      + '<div class="share-total"><span>含稅預估總價</span><strong>NT$ ' + esc(fmt(total)) + '</strong></div>'
      + '<p class="share-note">本報價為當下金價之預估結果；實際金額可能因市場價格與最終規格調整 ±10%。</p>'
      + actions
      + '<p class="quote-sheet-footnote">銘印鑽石 · imprint-diamond.com</p>'
      + '</article>';
  }

  function bindActions(root, mode) {
    if (mode === 'share') {
      root.querySelector('#share-copy-link')?.addEventListener('click', function () {
        navigator.clipboard.writeText(global.location.href).then(function () {
          var btn = root.querySelector('#share-copy-link');
          if (btn) { btn.textContent = '已複製'; setTimeout(function () { btn.textContent = '複製連結'; }, 2000); }
        });
      });
    } else {
      root.querySelector('#quote-print-btn')?.addEventListener('click', function () { global.print(); });
    }
  }

  function mount(root, config, mode) {
    if (!config) {
      root.innerHTML = '<div class="share-page"><p class="share-error">無法讀取試算資料，請回到計算機重新產生。</p></div>';
      return;
    }
    if (!config.clientPricing || config.clientPricing.total == null) {
      root.innerHTML = '<div class="share-page"><p class="share-error">試算資料不完整，請先完成規格選擇並確認總價後再試。</p>'
        + '<p class="share-error-actions"><a class="share-btn share-btn--primary" href="/shop/calculator/">返回試算</a></p></div>';
      return;
    }
    root.innerHTML = '<div class="share-page">' + renderCard(config, { mode: mode }) + '</div>';
    root.querySelectorAll('.share-image[data-fallback]').forEach(function (img) {
      var fb = img.getAttribute('data-fallback');
      if (fb && global.ShopAssets) global.ShopAssets.attachImageFallback(img, fb);
    });
    bindActions(root, mode);
  }

  global.ShopQuoteRender = { mount: mount, renderCard: renderCard };
})(window);
