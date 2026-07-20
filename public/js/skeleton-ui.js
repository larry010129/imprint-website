/* Shared skeleton HTML helpers — admin + member pages */
(function (global) {
  'use strict';

  function line(mod) {
    return '<span class="skel-line' + (mod ? ' skel-line--' + mod : '') + '"></span>';
  }

  function block(mod) {
    return '<span class="skel-block skel-block--' + mod + '"></span>';
  }

  function tableRowCells(cells) {
    return '<tr class="skel-row">' + cells.map(function (c) {
      return '<td>' + c + '</td>';
    }).join('') + '</tr>';
  }

  function productTableRow() {
    return tableRowCells([
      block('xs'),
      block('thumb'),
      line(),
      line('long'),
      block('badge'),
      '<span class="skel-actions"></span>',
    ]);
  }

  function orderTableRow() {
    return tableRowCells([
      block('xs'),
      block('thumb'),
      line('long'),
      line(),
      line(),
      block('badge'),
      '<span class="skel-actions"></span>',
    ]);
  }

  function leadsTableRow() {
    return tableRowCells([
      line('long'),
      line(),
      line('full'),
      line(),
      block('badge'),
      block('btn'),
    ]);
  }

  function memberOrderTableRow() {
    return tableRowCells([
      line('long'),
      line(),
      line(),
      line(),
      block('badge'),
      block('xs'),
    ]);
  }

  function tableBodyRows(count, rowFn) {
    var body = '';
    for (var i = 0; i < (count || 5); i++) body += (rowFn || productTableRow)();
    return body;
  }

  function table(opts) {
    opts = opts || {};
    var headers = opts.headers || [];
    var rows = opts.rows || 5;
    var rowFn = opts.rowFn || productTableRow;
    var thead = headers.length
      ? '<thead><tr>' + headers.map(function (h) { return '<th>' + h + '</th>'; }).join('') + '</tr></thead>'
      : '';
    var body = '';
    for (var i = 0; i < rows; i++) body += rowFn();
    var busy = opts.busy !== false ? ' aria-busy="true"' : '';
    var label = opts.label ? ' aria-label="' + opts.label + '"' : '';
    return (
      '<div class="skel-table-wrap skel-panel"' + busy + label + '>' +
        '<table class="skel-table">' + thead + '<tbody>' + body + '</tbody></table>' +
      '</div>'
    );
  }

  function rankList(count) {
    var items = '';
    for (var i = 0; i < (count || 4); i++) {
      items +=
        '<div class="skel-rank-item">' +
          '<div class="skel-rank-left">' + block('avatar') +
            '<div class="skel-rank-text">' + line('long') + line('medium') + '</div>' +
          '</div>' +
          line('medium') +
        '</div>';
    }
    return '<div class="skel-rank-list skel-panel" aria-busy="true">' + items + '</div>';
  }

  function recentList(count) {
    var items = '';
    for (var i = 0; i < (count || 5); i++) {
      items +=
        '<div class="skel-recent-item">' +
          '<div>' + line('medium') + line('long') + '</div>' +
          line() +
        '</div>';
    }
    return '<div class="skel-recent-list skel-panel" aria-busy="true">' + items + '</div>';
  }

  function statusCards(count) {
    var items = '';
    for (var i = 0; i < (count || 4); i++) {
      items += '<div class="skel-status-card">' + line() + line('medium') + '</div>';
    }
    return '<div class="skel-status-cards skel-panel" aria-busy="true">' + items + '</div>';
  }

  function memberList(count) {
    var rows = '';
    for (var i = 0; i < (count || 5); i++) {
      rows +=
        '<div class="skel-member-row">' +
          '<div class="skel-member-identity">' + block('avatar') +
            '<div style="flex:1">' + line('long') + line('medium') + '</div>' +
          '</div>' +
          block('pill') + block('badge') + line() + line() + line() +
          '<span class="skel-actions"></span>' +
        '</div>';
    }
    return '<div class="skel-panel" aria-busy="true" aria-label="載入中">' + rows + '</div>';
  }

  function cartList(count) {
    var items = '';
    for (var i = 0; i < (count || 3); i++) {
      items +=
        '<li class="skel-cart-item">' +
          block('xs') + block('thumb') +
          '<div>' + line('long') + line('medium') + '</div>' +
          line('medium') +
        '</li>';
    }
    return '<ul class="skel-cart-list skel-panel" aria-busy="true">' + items + '</ul>';
  }

  function favoriteGrid(count) {
    var items = '';
    for (var i = 0; i < (count || 4); i++) {
      items +=
        '<div class="skel-fav-card">' +
          '<div class="skel-fav-card__img"></div>' +
          '<div class="skel-fav-card__body">' + line('long') + line('medium') + '</div>' +
        '</div>';
    }
    return '<div class="skel-fav-grid skel-panel" aria-busy="true">' + items + '</div>';
  }

  function notifyList(count) {
    var items = '';
    for (var i = 0; i < (count || 4); i++) {
      items +=
        '<div class="skel-notify-item">' +
          block('xs') +
          '<div>' + line('long') + line('full') + line('medium') + '</div>' +
          line() +
        '</div>';
    }
    return '<div class="skel-notify-list skel-panel" aria-busy="true">' + items + '</div>';
  }

  function orderCards(count) {
    var items = '';
    for (var i = 0; i < (count || 3); i++) {
      items += '<div class="skel-order-card">' + line('long') + line('medium') + line('full') + '</div>';
    }
    return '<div class="skel-order-cards skel-panel" aria-busy="true">' + items + '</div>';
  }

  function tabs(count) {
    var items = '';
    for (var i = 0; i < (count || 5); i++) items += block('tab') + ' ';
    return '<div class="skel-tabs">' + items + '</div>';
  }

  function productsShell() {
    return (
      '<p class="note ap-skeleton-note">' + line('short') + '</p>' +
      '<div class="ap-toolbar" style="display:flex;justify-content:flex-end;margin:14px 0">' + block('btn') + '</div>' +
      tabs(5) +
      table({ headers: ['', '縮圖', '品項', '名稱', '狀態', '操作'], rows: 5, label: '載入商品中' })
    );
  }

  function invitesShell() {
    return (
      line('short') +
      '<div style="margin:14px 0">' + block('btn') + '</div>' +
      table({
        headers: ['邀請碼', '合作廠商', '已使用 / 上限', '權限', '狀態', '到期日', '建立時間', '操作'],
        rows: 4,
        rowFn: function () {
          return tableRowCells([line(), line(), line(), block('badge'), block('badge'), line(), line(), '<span class="skel-actions"></span>']);
        },
        label: '載入邀請碼中',
      })
    );
  }

  function accountsShell() {
    return line('short') + memberList(5);
  }

  global.SkeletonUI = {
    line: line,
    block: block,
    table: table,
    tableBodyRows: tableBodyRows,
    rankList: rankList,
    recentList: recentList,
    statusCards: statusCards,
    memberList: memberList,
    cartList: cartList,
    favoriteGrid: favoriteGrid,
    notifyList: notifyList,
    orderCards: orderCards,
    tabs: tabs,
    productsShell: productsShell,
    invitesShell: invitesShell,
    accountsShell: accountsShell,
    orderTableRow: orderTableRow,
    leadsTableRow: leadsTableRow,
    memberOrderTableRow: memberOrderTableRow,
  };
})(window);
