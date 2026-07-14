/* Renders DNA diamond price reference tables from ImprintPricing (pricing-config.js). */
(function () {
  'use strict';

  var SNAPSHOT_CARATS = ['0.10', '0.50', '1.00', '3.00'];
  var SNAPSHOT_LABELS = {
    '0.10': '低調的日常陪伴',
    '0.50': '最受歡迎・可送鑑定',
    '1.00': '傳家的份量',
    '3.00': '頂級珍藏'
  };
  var CARAT_RANGES = {
    '0.10': '0.10–0.15ct',
    '0.20': '0.20–0.25ct',
    '0.30': '0.30–0.35ct',
    '0.50': '0.50–0.55ct',
    '0.60': '0.60–0.65ct',
    '0.70': '0.70–0.75ct',
    '0.80': '0.80–0.85ct',
    '0.90': '0.90–0.95ct',
    '1.00': '1.00–1.25ct',
    '1.50': '1.50–1.75ct',
    '2.00': '2.00–2.50ct',
    '3.00': '3.00–3.50ct'
  };

  function fmt(n) {
    if (n == null) return '—';
    return 'NT$ ' + Number(n).toLocaleString('zh-TW');
  }

  function renderSnapshot(pricing) {
    var el = document.getElementById('price-ref-snapshot');
    if (!el || !pricing) return;
    var white = pricing.diamond.white || {};
    var rows = SNAPSHOT_CARATS.map(function (c) {
      var hl = c === '0.50' ? ' price-ref-row--hl' : '';
      return (
        '<div class="price-ref-row' + hl + '">' +
          '<span class="price-ref-row__ct">' + c + ' 克拉<small>' + (SNAPSHOT_LABELS[c] || '') + '</small></span>' +
          '<span class="price-ref-row__amt">' + fmt(white[c]) + '</span>' +
        '</div>'
      );
    }).join('');
    el.innerHTML = rows;
  }

  function buildTable(headers, bodyRows) {
    var thead = '<thead><tr>' + headers.map(function (h) { return '<th>' + h + '</th>'; }).join('') + '</tr></thead>';
    var tbody = '<tbody>' + bodyRows.join('') + '</tbody>';
    return '<div class="price-ref-scroll"><table class="price-full-table">' + thead + tbody + '</table></div>';
  }

  function singleRows(table, isFancy) {
    var keys = Object.keys(table).sort(function (a, b) { return parseFloat(a) - parseFloat(b); });
    var rows = keys.map(function (c) {
      var val = table[c];
      var amt = val != null
        ? '<td class="amt">' + fmt(val) + '</td>'
        : '<td class="na">無法製作</td>';
      return '<tr><td>' + c + ' 克拉</td><td>' + (CARAT_RANGES[c] || '—') + '</td>' + amt + '</tr>';
    });
    rows.push(
      '<tr class="is-note"><td colspan="3">' +
        (isFancy ? '彩鑽最低 0.30 克拉；' : '') +
        '3.00 克拉以上請洽官方 LINE 專屬報價</td></tr>'
    );
    return rows;
  }

  function renderSingleTabs(pricing) {
    var mount = document.getElementById('price-ref-single-tabs');
    if (!mount || !pricing) return;
    var whiteHtml = buildTable(['克拉', '實際區間', '價格'], singleRows(pricing.diamond.white || {}, false));
    var fancyHtml = buildTable(['克拉', '實際區間', '價格'], singleRows(pricing.diamond.fancy || {}, true));
    mount.innerHTML =
      '<div class="price-ref-tabset">' +
        '<input type="radio" name="prSingle" id="prSingleWhite" class="price-tab-radio" checked>' +
        '<input type="radio" name="prSingle" id="prSingleFancy" class="price-tab-radio">' +
        '<div class="price-tab-labels">' +
          '<label for="prSingleWhite" class="price-tab">白鑽</label>' +
          '<label for="prSingleFancy" class="price-tab">彩鑽</label>' +
        '</div>' +
        '<div class="price-panel panel-white">' + whiteHtml + '</div>' +
        '<div class="price-panel panel-fancy">' + fancyHtml + '</div>' +
      '</div>';
  }

  function multiRows(table, caratKeys) {
    return caratKeys.map(function (c) {
      var row = table[c] || {};
      return (
        '<tr><td>' + c + ' 克拉<br><small style="color:var(--ink-faint);">' + (CARAT_RANGES[c] || '') + '</small></td>' +
        '<td class="amt">' + fmt(row['2']) + '</td>' +
        '<td class="amt">' + fmt(row['3']) + '</td>' +
        '<td class="amt">' + fmt(row['4']) + '</td></tr>'
      );
    });
  }

  function renderMultiTabs(pricing) {
    var mount = document.getElementById('price-ref-multi-tabs');
    if (!mount || !pricing) return;
    var white = pricing.whiteMultiDiamondPrice || {};
    var fancy = pricing.coloredMultiDiamondPrice || {};
    var whiteKeys = Object.keys(white).sort(function (a, b) { return parseFloat(a) - parseFloat(b); });
    var fancyKeys = Object.keys(fancy).sort(function (a, b) { return parseFloat(a) - parseFloat(b); });
    var noteRow =
      '<tr class="is-note"><td>0.30 克拉以上</td>' +
      '<td>沿用 0.30 整組價・85 折</td><td>8 折</td><td>75 折</td></tr>';
    var whiteHtml = buildTable(['克拉', '2 顆', '3 顆', '4 顆'], multiRows(white, whiteKeys).concat([noteRow]));
    var fancyHtml = buildTable(['克拉', '2 顆', '3 顆', '4 顆'], multiRows(fancy, fancyKeys).concat([noteRow]));
    mount.innerHTML =
      '<div class="price-ref-tabset">' +
        '<input type="radio" name="prMulti" id="prMultiWhite" class="price-tab-radio" checked>' +
        '<input type="radio" name="prMulti" id="prMultiFancy" class="price-tab-radio">' +
        '<div class="price-tab-labels">' +
          '<label for="prMultiWhite" class="price-tab">白鑽</label>' +
          '<label for="prMultiFancy" class="price-tab">彩鑽</label>' +
        '</div>' +
        '<div class="price-panel panel-white">' + whiteHtml + '</div>' +
        '<div class="price-panel panel-fancy">' + fancyHtml + '</div>' +
      '</div>';
  }

  function renderRules(pricing) {
    var el = document.getElementById('price-ref-rules-list');
    if (!el || !pricing) return;
    var pct = pricing.shapeSurchargePct || 10;
    el.innerHTML =
      '<li>圓形明亮式切工／白鑽為基準價；其餘切工加價 <strong>' + pct + '%</strong>，且需 <strong>0.30 克拉以上</strong>才能製作。</li>' +
      '<li>DNA 鑽石價格<strong>不含飾品戒台</strong>；戒台依款式與材質另計（9K 經典項鍊 NT$10,000 起，不含鑽）。</li>' +
      '<li>因鑽石價格浮動，以上僅供參考，銘印鑽石保有更改之權利。</li>';
  }

  function renderAll() {
    var pricing = window.ImprintPricing ? window.ImprintPricing.getAll() : null;
    if (!pricing) return;
    renderSnapshot(pricing);
    renderSingleTabs(pricing);
    renderMultiTabs(pricing);
    renderRules(pricing);
  }

  function expandPriceReference() {
    ['price-ref-details-single', 'price-ref-details-multi'].forEach(function (id) {
      var d = document.getElementById(id);
      if (d) d.open = true;
    });
  }

  function init() {
    var root = document.getElementById('price-reference');
    if (!root) return;

    if (window.ImprintPricing && window.ImprintPricing.ready) {
      window.ImprintPricing.ready.then(renderAll);
    } else {
      renderAll();
    }
  }

  window.PriceReference = {
    init: init,
    refresh: renderAll,
    expand: expandPriceReference
  };

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
