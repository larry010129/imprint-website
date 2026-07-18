/**
 * Member-facing order row + detail panel (history, account).
 */
(function (global) {
  'use strict';

  var CATEGORY_LABELS = {
    pendant: '項墜',
    ring: '戒指',
    earring: '耳環',
    bracelet: '手鍊',
    chain: '鏈條',
  };
  var GOLD_LABELS = { '9k': '9K', '14k': '14K', '18k': '18K', pt950: 'PT950', s925: 'S925' };
  var COLOR_LABELS = { white: 'K白', yellow: 'K黃', rose: '玫瑰金' };
  var FULFILLMENT_LABELS = { pickup: '門市自取', delivery: '宅配到府' };
  var STATUS_FLOW = [
    'received', 'dna_lab', 'deposit_confirmed', 'in_production',
    'quality_check', 'shipped', 'completed',
  ];
  var STATUS_COLORS = {
    received: '#e0a458',
    dna_lab: '#6c9bd1',
    deposit_confirmed: '#5bc0de',
    in_production: '#9cefef',
    quality_check: '#5ecfcf',
    shipped: '#9b7fd4',
    completed: '#4caf7d',
    cancelled: '#8a817b',
  };

  function esc(s) {
    var el = document.createElement('span');
    el.textContent = s == null ? '' : String(s);
    return el.innerHTML;
  }

  function formatMoney(n) {
    if (n == null || n === '') return '—';
    return Number(n).toLocaleString('zh-TW', { maximumFractionDigits: 0 });
  }

  function styleLabel(o) {
    return o.product_name || o.summary || o.product_type || CATEGORY_LABELS[o.category] || '訂製品項';
  }

  function diamondLabel(o) {
    if (o.diamond_kind === 'fancy') {
      return '彩鑽' + (o.fancy_color ? '（' + o.fancy_color + '）' : '');
    }
    return '白鑽';
  }

  function imageUrl(o) {
    if (o.image_url) return o.image_url;
    if (global.ShopAssets && o.category) {
      var thumb = global.ShopAssets.categoryThumb(o.category);
      if (thumb) return thumb;
    }
    if (o.category) return '/static/images/shop/categories/' + o.category + '.svg';
    return '';
  }

  function isCancelled(o) {
    var s = (o.status || '').toLowerCase();
    return s === 'cancelled' || s === 'canceled';
  }

  function statusIndex(status) {
    var i = STATUS_FLOW.indexOf(status);
    return i < 0 ? 0 : i;
  }

  function priceBreakdownLines(o) {
    var lines = '';
    if (o.diamond_price_twd != null && Number(o.diamond_price_twd) > 0) {
      lines += specItem('鑽石價格 (NT$)', formatMoney(o.diamond_price_twd));
    }
    var metalwork = Number(o.taijin_price_twd || 0) + Number(o.labor_price_twd || 0);
    if (metalwork > 0) {
      lines += specItem('金工價格 (NT$)', formatMoney(metalwork));
    }
    if (o.chain_total_twd != null && Number(o.chain_total_twd) > 0) {
      lines += specItem('搭配鏈條 (NT$)', formatMoney(o.chain_total_twd));
    }
    lines += specItem('總計 (NT$)', formatMoney(o.total_price));
    return lines;
  }

  function canEditOrder(o) {
    return (o.status || '').toLowerCase() === 'received';
  }

  function orderToShopConfig(o) {
    var type = o.product_id || o.product_type;
    var cfg = {
      orderId: o.id,
      orderNumber: o.order_number,
      category: o.category,
      type: type,
      gold: o.gold_purity,
      color: o.color,
      carat: o.carat,
      ringSize: o.ring_size,
      engravingBand: o.engraving_band || '',
      engravingGirdle: o.engraving_girdle || '',
      diamondKind: o.diamond_kind || 'white',
      fancyColor: o.fancy_color,
      stoneCount: o.stone_count,
      diamondShape: o.diamond_shape || 'round',
      includeChain: !!o.include_chain,
      chainGold: o.chain_gold,
      chainColor: o.chain_color,
    };
    if (o.category === 'chain') {
      cfg.lengthCm = o.chain_length_cm;
    } else {
      cfg.chainLength = o.chain_length_cm;
    }
    if (o.product_name) cfg.summaryZh = o.product_name;
    return cfg;
  }

  function detailId(o) {
    var key = o.id || o.order_number || 'order';
    return 'history-detail-' + String(key).replace(/[^a-zA-Z0-9_-]/g, '-');
  }

  function thumbHtml(url, alt) {
    if (!url) return '<span class="order-style-thumb order-style-thumb--empty">—</span>';
    return '<img class="order-style-thumb" src="' + esc(url) + '" alt="' + esc(alt || '') + '" loading="lazy">';
  }

  function specItem(label, value) {
    return (
      '<div class="order-detail-item">' +
        '<span class="order-detail-label">' + esc(label) + '</span>' +
        '<span class="order-detail-value">' + esc(String(value)) + '</span>' +
      '</div>'
    );
  }

  function progressHtml(status, statusLabel) {
    if (isCancelled({ status: status })) {
      return '<div class="order-detail-status"><p class="order-detail-cancelled">此訂單已取消</p></div>';
    }
    var idx = statusIndex(status);
    var steps = STATUS_FLOW.map(function (s, i) {
      var state = i < idx ? 'complete' : (i === idx ? 'current' : 'incomplete');
      var color = STATUS_COLORS[s] || '#9cefef';
      var barStyle = state === 'incomplete' ? '' : ' style="--step-color:' + color + '"';
      return (
        '<div class="order-steps-item">' +
          '<div class="order-steps-bar order-steps-bar--' + state + '" data-step="' + s + '"' + barStyle + '></div>' +
          '<div class="order-steps-label order-steps-label--' + state + '">' + esc(statusLabel(s)) + '</div>' +
        '</div>'
      );
    }).join('');
    return '<div class="order-detail-status"><div class="order-steps" role="list">' + steps + '</div></div>';
  }

  function detailPanel(o, statusLabel) {
    statusLabel = statusLabel || function (s) { return s; };
    var cat = CATEGORY_LABELS[o.category] || o.category || '—';
    var gold = GOLD_LABELS[o.gold_purity] || o.gold_purity || '—';
    var color = COLOR_LABELS[o.color] || o.color || '—';
    var name = styleLabel(o);
    var img = imageUrl(o);
    var fulfillment = FULFILLMENT_LABELS[o.fulfillment_method] || o.fulfillment_method || '—';
    var shipping = o.fulfillment_method === 'delivery'
      ? [o.shipping_city, o.shipping_postal, o.shipping_address].filter(Boolean).join(' ')
      : '';
    var cancelNote = isCancelled(o) && o.cancel_reason
      ? '<p class="order-detail-cancel-reason">取消原因：' + esc(o.cancel_reason) + '</p>'
      : '';
    var noteBlock = o.order_note
      ? specItem('備註', o.order_note)
      : '';
    var statusNote = o.status_note
      ? specItem('狀態說明', o.status_note)
      : '';
    var editBtn = canEditOrder(o)
      ? '<div class="order-detail-actions">' +
          '<a href="/shop/calculator/?editOrder=' + encodeURIComponent(o.order_number || '') + '" ' +
          'class="btn btn-mint member-order-edit-btn" data-order-number="' + esc(o.order_number || '') + '">修改訂單</a>' +
          '<p class="order-detail-edit-hint">僅「已收到申請」狀態可修改規格並重新試算</p>' +
        '</div>'
      : '';

    return (
      '<div class="order-detail-panel">' +
        '<div class="order-detail-layout">' +
          '<div class="order-detail-gallery">' +
            '<div class="order-detail-preview">' + thumbHtml(img, name) + '</div>' +
            '<p class="order-detail-product-name">' + esc(name) + '</p>' +
            '<p class="order-detail-product-meta">' + esc(cat) + ' · ' + esc(gold) + ' · ' + esc(color) + ' · ' + esc(diamondLabel(o)) + '</p>' +
            cancelNote +
          '</div>' +
          '<div class="order-detail-specs">' +
            '<div class="order-detail-grid">' +
              specItem('訂單編號', o.order_number || '—') +
              specItem('品項', name) +
              specItem('成色', gold) +
              specItem('顏色', color) +
              specItem('克拉', o.carat || '—') +
              specItem('鑽石', diamondLabel(o)) +
              (o.diamond_shape ? specItem('形狀', o.diamond_shape) : '') +
              specItem('戒圍', o.ring_size != null ? o.ring_size : '—') +
              (o.engraving_band ? specItem('戒圈刻字', o.engraving_band) : '') +
              (o.engraving_girdle ? specItem('腰圍刻字', o.engraving_girdle) : '') +
              specItem('取貨方式', fulfillment) +
              (shipping ? specItem('收件地址', shipping) : '') +
              priceBreakdownLines(o) +
              noteBlock +
              statusNote +
            '</div>' +
            progressHtml(o.status, statusLabel) +
            editBtn +
          '</div>' +
        '</div>' +
      '</div>'
    );
  }

  function rowHtml(o, statusLabel, escapeHtml) {
    escapeHtml = escapeHtml || esc;
    statusLabel = statusLabel || function (s) { return s; };
    var orderNo = o.order_number || o.id || '—';
    var price = o.total_price != null ? o.total_price : o.totalPrice;
    var label = styleLabel(o);
    var target = detailId(o);
    var searchBlob = [orderNo, label, o.category, o.status, o.customer_name].filter(Boolean).join(' ');

    return (
      '<tr class="order-row-main member-order-row" data-search="' + escapeHtml(searchBlob.toLowerCase()) + '" tabindex="0" role="button" aria-label="查看訂單 ' + escapeHtml(orderNo) + ' 詳情">' +
        '<td>' + escapeHtml(String(orderNo)) + '</td>' +
        '<td>' + escapeHtml(o.created_at_display || o.created_at || '—') + '</td>' +
        '<td class="member-order-item">' + escapeHtml(label) + '</td>' +
        '<td>' + (price != null ? formatMoney(price) : '—') + '</td>' +
        '<td><span class="member-order-status">' + escapeHtml(statusLabel(o.status) || '—') + '</span></td>' +
        '<td class="member-order-expand">' +
          '<span class="member-order-chevron" aria-hidden="true">›</span>' +
          '<button type="button" class="order-detail-btn visually-hidden" data-target="' + esc(target) + '" aria-expanded="false">查看詳情</button>' +
        '</td>' +
      '</tr>' +
      '<tr class="order-detail-row" id="' + esc(target) + '" hidden>' +
        '<td colspan="6">' + detailPanel(o, statusLabel) + '</td>' +
      '</tr>'
    );
  }

  global.ImprintOrderDisplay = {
    styleLabel: styleLabel,
    detailPanel: detailPanel,
    rowHtml: rowHtml,
    detailId: detailId,
    canEditOrder: canEditOrder,
    orderToShopConfig: orderToShopConfig,
  };
})(window);
