(function (global) {
  'use strict';
  var M = global.ImprintMVC;
  var CAT_ZH = {
    pendant: '項墜',
    ring: '戒指',
    earring: '耳飾',
    bracelet: '手鍊',
    chain: '鍊條',
  };
  var GOLD_ZH = {
    '9k': '9K',
    '14k': '14K',
    '18k': '18K',
    pt950: 'PT950',
    s925: '925銀',
  };
  var COLOR_ZH = {
    white: '白金',
    yellow: '黃金',
    rose: '玫瑰金',
  };
  var FANCY_COLOR_ZH = {
    yellow: '黃鑽',
    pink: '粉鑽',
    blue: '藍鑽',
  };
  var SHAPE_ZH = {
    round: '圓形',
    marquise: '馬眼型',
    oval: '橢圓形',
    princess: '公主方',
    trilliant: '三角形',
    emerald: '祖母綠形',
    heart: '心形',
    radiant: '雷地恩形',
    pear: '梨形',
    cushion: '枕形',
    asscher: '阿斯切',
  };

  function escapeAttr(value) {
    return M.escapeHtml(value).replace(/"/g, '&quot;').replace(/'/g, '&#39;');
  }

  function configFor(item) {
    return item && item.config_json && typeof item.config_json === 'object'
      ? item.config_json
      : {};
  }

  function titleFor(item) {
    var config = configFor(item);
    return item.summary_zh || item.summary || config.summaryZh || '訂製品項';
  }

  function materialLabel(gold, color) {
    if (!gold) return '';
    var goldLabel = GOLD_ZH[gold] || gold;
    if (gold === 'pt950' || gold === 's925') return goldLabel;
    return goldLabel + (COLOR_ZH[color] || COLOR_ZH.white);
  }

  function caratLabel(carat, stoneCount, quantity) {
    if (!carat) return '';
    var label = /mm$/.test(carat) ? carat : carat + 'ct';
    if (Number(quantity) > 1) return label + ' × ' + quantity;
    return Number(stoneCount) > 1 ? label + ' × ' + stoneCount : label;
  }

  function diamondLabel(config) {
    if (config.category === 'chain') return '';
    if (config.diamondKind === 'fancy') {
      return FANCY_COLOR_ZH[config.fancyColor] || '彩鑽';
    }
    return '白鑽';
  }

  function itemMeta(item) {
    var config = configFor(item);
    return [
      materialLabel(config.gold, config.color),
      caratLabel(config.carat, config.stoneCount, config.quantity),
      CAT_ZH[config.category || item.category] || config.category || item.category || '',
    ].filter(Boolean).join(' · ');
  }

  function specRows(item) {
    var config = configFor(item);
    var category = config.category || item.category || '';
    var title = titleFor(item);
    var rows = [
      { label: '品項', value: CAT_ZH[category] || category },
      { label: '款式', value: title },
      { label: '金屬材質', value: materialLabel(config.gold, config.color) },
      { label: category === 'chain' ? '厚度' : '克拉', value: caratLabel(config.carat) },
    ];
    var diamond = diamondLabel(config);
    if (diamond) rows.push({ label: '鑽石', value: diamond });
    if (config.diamondShape && config.diamondShape !== 'round') {
      rows.push({ label: '形狀', value: SHAPE_ZH[config.diamondShape] || config.diamondShape });
    }
    if (Number(config.stoneCount) > 1) {
      rows.push({ label: '鑽石顆數', value: String(config.stoneCount) });
    }
    if (category === 'earring' && Number(config.quantity) >= 1) {
      rows.push({ label: '數量', value: String(config.quantity) });
    }
    if (config.ringSize) rows.push({ label: '戒圍', value: String(config.ringSize) });
    if (config.lengthCm) rows.push({ label: '長度', value: config.lengthCm + ' cm' });
    if (config.chainThickness && category !== 'chain') {
      rows.push({ label: '鍊條厚度', value: config.chainThickness });
    }
    if (config.chainLength && category !== 'chain') {
      rows.push({ label: '鍊長', value: config.chainLength + ' cm' });
    }
    if (config.includeChain) {
      rows.push({
        label: '搭配鍊條',
        value: materialLabel(config.chainGold, config.chainColor) || '是',
      });
    }
    if (config.engravingBand) rows.push({ label: '戒圈刻字', value: config.engravingBand });
    if (config.engravingRemark) rows.push({ label: '金屬刻字', value: config.engravingRemark });
    if (config.engravingGirdle) rows.push({ label: '腰圍刻字', value: config.engravingGirdle });
    if (config.series) rows.push({ label: '系列', value: config.series });
    return rows.filter(function (row) { return row.value != null && row.value !== ''; });
  }

  function priceRows(breakdown) {
    breakdown = breakdown || {};
    var rows = [];
    if (Number(breakdown.diamondPrice) > 0) {
      rows.push({ label: '鑽石價格', value: M.formatPrice(breakdown.diamondPrice) });
    }
    var metalwork = breakdown.metalworkPrice;
    if (metalwork == null && breakdown.taijinPrice != null && breakdown.laborPrice != null) {
      metalwork = Number(breakdown.taijinPrice) + Number(breakdown.laborPrice);
    }
    if (Number(metalwork) > 0) {
      rows.push({ label: '金工價格', value: M.formatPrice(metalwork) });
    }
    if (Number(breakdown.chainPrice) > 0) {
      rows.push({ label: '搭配鍊條', value: M.formatPrice(breakdown.chainPrice) });
    }
    return rows;
  }

  function renderDetailRows(rows, modifier) {
    var className = 'member-cart-detail__rows' + (modifier ? ' ' + modifier : '');
    return '<dl class="' + className + '">' + rows.map(function (row) {
      return '<div class="member-cart-detail__row"><dt>' + M.escapeHtml(row.label) +
        '</dt><dd>' + M.escapeHtml(row.value) + '</dd></div>';
    }).join('') + '</dl>';
  }

  global.ImprintViews = global.ImprintViews || {};
  global.ImprintViews.Cart = {
    els: function () {
      return {
        loading: document.getElementById('cart-loading'),
        empty: document.getElementById('cart-empty'),
        wrap: document.getElementById('cart-list-wrap'),
        list: document.getElementById('cart-list'),
        selectedLabel: document.getElementById('cart-selected-label'),
        selectedTotal: document.getElementById('cart-selected-total'),
        checkoutBtn: document.getElementById('cart-checkout-btn'),
        selectAll: document.getElementById('cart-select-all'),
        dialog: document.getElementById('cart-detail-dialog'),
        dialogBody: document.getElementById('cart-detail-body'),
        dialogClose: document.getElementById('cart-detail-close'),
      };
    },
    setState: function (state) {
      var e = this.els();
      M.show(e.loading, state === 'loading');
      M.show(e.empty, state === 'empty');
      M.show(e.wrap, state === 'list');
    },
    renderRows: function (rows) {
      var e = this.els();
      if (!e.list) return;
      e.list.innerHTML = rows.map(function (row) {
        var item = row.item || row;
        var specs = row.specs || item.specs || {};
        var id = item.id;
        var price = item.total_price != null ? item.total_price : item.totalPrice;
        var compareAt = item.compare_at_total != null ? item.compare_at_total : item.compareAtTotal;
        var showCompare = Number(compareAt) > Number(price || 0);
        var img = row.image_url || item.image_url || '';
        var summary = titleFor(item) || ('#' + id);
        var meta = itemMeta(item) || [
          specs.category,
          specs.carat ? specs.carat + ' ct' : '',
          specs.gold,
          specs.color,
        ].filter(Boolean).join(' · ');
        var cfg = configFor(item);
        var cat = cfg.category || item.category || '';
        var qtyMax = cat === 'earring' ? 2 : 99;
        var qty = Math.max(1, Math.min(qtyMax, Number(cfg.quantity != null ? cfg.quantity : 1) || 1));
        var compareAttr = showCompare ? Number(compareAt) : Number(price || 0);
        return (
          '<li class="member-cart-item" id="cart-item-' + id + '" data-id="' + id + '" data-price="' + (price || 0) +
            '" data-compare-price="' + compareAttr + '" data-qty-max="' + qtyMax + '">' +
            '<label class="member-cart-item__check"><input type="checkbox" class="cart-item-checkbox" value="' +
              escapeAttr(id) + '" aria-label="選取 ' + escapeAttr(summary) + '" checked></label>' +
            (img ? '<img class="member-cart-item__thumb" src="' + escapeAttr(img) + '" alt="" loading="lazy">' :
              '<span class="member-cart-item__thumb member-cart-item__thumb--empty" aria-hidden="true"></span>') +
            '<div class="member-cart-item__body">' +
              '<a class="member-cart-item__title" href="/shop/calculator/?cart_edit=' + encodeURIComponent(id) + '">' +
                M.escapeHtml(summary) + '</a>' +
              '<span class="member-cart-item__price-wrap">' +
                '<strong class="member-cart-item__price">' + M.formatPrice(price) + '</strong>' +
                (showCompare
                  ? '<s class="member-cart-item__price-compare">' + M.formatPrice(compareAt) + '</s>'
                  : '') +
              '</span>' +
              (meta ? '<p class="member-cart-item__meta"><span class="member-cart-item__tag">' +
                M.escapeHtml(meta).replace(/ · /g, '</span><span class="member-cart-item__tag">') +
                '</span></p>' : '') +
            '</div>' +
            '<div class="member-cart-item__side">' +
              '<div class="member-cart-qty" role="group" aria-label="數量">' +
                '<button type="button" class="member-cart-qty__btn member-cart-qty__btn--dec cart-qty-dec" data-id="' +
                  escapeAttr(id) + '" aria-label="減少數量">−</button>' +
                '<input type="number" class="member-cart-qty__input cart-qty-input" data-id="' + escapeAttr(id) +
                  '" value="' + qty + '" min="1" max="' + qtyMax + '" step="1" inputmode="numeric" aria-label="數量">' +
                '<button type="button" class="member-cart-qty__btn member-cart-qty__btn--inc cart-qty-inc" data-id="' +
                  escapeAttr(id) + '" aria-label="增加數量"' + (qty >= qtyMax ? ' disabled' : '') + '>+</button>' +
              '</div>' +
              '<div class="member-cart-item__utils">' +
                '<a class="member-cart-item__util" href="/shop/calculator/?cart_edit=' + encodeURIComponent(id) +
                  '" aria-label="編輯' + escapeAttr(summary) + '">追蹤</a>' +
                '<button type="button" class="member-cart-item__util member-cart-item__util--danger cart-item-remove" data-id="' +
                  escapeAttr(id) + '" aria-label="刪除' + escapeAttr(summary) + '">刪除</button>' +
              '</div>' +
            '</div>' +
          '</li>'
        );
      }).join('');
    },
    updateSelection: function () {
      var e = this.els();
      if (!e.list) return;
      var boxes = [].slice.call(e.list.querySelectorAll('.cart-item-checkbox'));
      var selected = boxes.filter(function (cb) { return cb.checked; });
      var total = 0;
      var compare = 0;
      selected.forEach(function (cb) {
        var row = cb.closest('.member-cart-item');
        var p = Number(row && row.dataset.price || 0);
        var c = Number(row && row.dataset.comparePrice);
        total += p;
        compare += (Number.isFinite(c) && c > p) ? c : p;
      });
      if (e.selectedLabel) e.selectedLabel.textContent = '已選 ' + selected.length + ' 件';
      if (e.selectedTotal) {
        e.selectedTotal.textContent = M.formatPrice(total);
        e.selectedTotal.classList.toggle('member-cart-summary__sale', compare > total);
      }
      var sub = document.getElementById('cart-selected-subtotal');
      if (sub) {
        sub.textContent = M.formatPrice(compare);
        sub.classList.toggle('member-cart-summary__compare', compare > total);
      }
      var countEl = document.getElementById('cart-checkout-count');
      if (countEl) countEl.textContent = String(selected.length);
      if (e.checkoutBtn) e.checkoutBtn.disabled = selected.length === 0;
      if (e.selectAll) {
        e.selectAll.checked = boxes.length > 0 && selected.length === boxes.length;
        e.selectAll.indeterminate = selected.length > 0 && selected.length < boxes.length;
      }
      return selected.map(function (cb) { return String(cb.value); });
    },
    renderDetail: function (item, breakdown) {
      var e = this.els();
      if (!e.dialogBody) return;
      var config = configFor(item);
      var title = titleFor(item);
      var category = config.category || item.category || '';
      var img = item.image_url || config.previewImage || '';
      var specs = specRows(item);
      var prices = priceRows(breakdown);
      var total = breakdown && breakdown.total != null
        ? breakdown.total
        : (item.total_price != null ? item.total_price : item.totalPrice);
      e.dialogBody.innerHTML =
        '<article class="member-cart-detail">' +
          '<div class="member-cart-detail__hero">' +
            '<div class="member-cart-detail__media">' +
              (img
                ? '<img src="' + escapeAttr(img) + '" alt="" loading="lazy">'
                : '<span aria-hidden="true">💎</span>') +
            '</div>' +
            '<div class="member-cart-detail__intro">' +
              (category ? '<p>' + M.escapeHtml(CAT_ZH[category] || category) + '</p>' : '') +
              '<h3>' + M.escapeHtml(title) + '</h3>' +
              '<a class="member-cart-detail__edit" href="/shop/calculator/?cart_edit=' +
                encodeURIComponent(item.id) + '">編輯規格</a>' +
            '</div>' +
          '</div>' +
          '<section class="member-cart-detail__section">' +
            '<h3>訂製規格</h3>' +
            renderDetailRows(specs) +
          '</section>' +
          '<section class="member-cart-detail__section member-cart-detail__section--price">' +
            '<h3>價格明細</h3>' +
            (prices.length ? renderDetailRows(prices, 'member-cart-detail__rows--price') : '') +
            '<div class="member-cart-detail__total"><span>總計</span><strong>' +
              M.formatPrice(total) + '</strong></div>' +
          '</section>' +
        '</article>';
    },
  };
})(window);
