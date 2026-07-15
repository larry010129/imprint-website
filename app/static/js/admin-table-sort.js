/* 銘印鑽石｜後台表格欄位排序（共用） */
(function (window) {
  'use strict';

  function parseValue(text, type) {
    var raw = String(text == null ? '' : text).trim();
    if (type === 'number') {
      var n = parseFloat(raw.replace(/,/g, '').replace(/[^\d.-]/g, ''));
      return isNaN(n) ? -Infinity : n;
    }
    if (type === 'date') {
      var d = Date.parse(raw.replace(' ', 'T'));
      return isNaN(d) ? 0 : d;
    }
    return raw.toLowerCase();
  }

  function compareValues(a, b, dir) {
    if (a < b) return dir === 'asc' ? -1 : 1;
    if (a > b) return dir === 'asc' ? 1 : -1;
    return 0;
  }

  function sortIcon(dir) {
    if (dir === 'asc') return '↑';
    if (dir === 'desc') return '↓';
    return '↕';
  }

  function enhanceHeader(th, onSort) {
    if (th.dataset.sortBound) return;
    th.dataset.sortBound = '1';
    var label = th.textContent.trim();
    th.classList.add('adx-sort-th');
    th.setAttribute('aria-sort', 'none');
    th.innerHTML =
      '<button type="button" class="adx-sort-btn">' +
        '<span class="adx-sort-label">' + label + '</span>' +
        '<span class="adx-sort-icon" aria-hidden="true">↕</span>' +
      '</button>';
    var btn = th.querySelector('.adx-sort-btn');
    btn.addEventListener('click', function () { onSort(th, btn); });
  }

  function collectRowGroups(tbody) {
    var groups = [];
    var rows = Array.from(tbody.querySelectorAll('tr'));
    for (var i = 0; i < rows.length; i++) {
      var row = rows[i];
      if (row.classList.contains('order-detail-row')) continue;
      var group = [row];
      var next = rows[i + 1];
      if (next && next.classList.contains('order-detail-row')) {
        group.push(next);
        i++;
      }
      groups.push(group);
    }
    return groups;
  }

  function datasetSort(row, key) {
    if (!key || !row || !row.dataset) return null;
    var prop = 'sort' + key.charAt(0).toUpperCase() + key.slice(1);
    return row.dataset[prop];
  }

  function bindTable(table) {
    if (!table || table.dataset.sortTableBound) return;
    var thead = table.tHead;
    var tbody = table.tBodies[0];
    if (!thead || !tbody || !thead.rows.length) return;
    table.dataset.sortTableBound = '1';

    var headers = Array.from(thead.rows[0].cells);
    var sortState = { col: -1, dir: 'asc' };

    function getCellText(row, index) {
      var cell = row.cells && row.cells[index];
      return cell ? cell.textContent : '';
    }

    function getValue(group, colIndex, type) {
      var row = group[0];
      var key = headers[colIndex] && headers[colIndex].dataset.sortKey;
      var fromData = datasetSort(row, key);
      if (fromData != null && fromData !== '') return parseValue(fromData, type);
      return parseValue(getCellText(row, colIndex), type);
    }

    function applySort(colIndex) {
      var th = headers[colIndex];
      var type = th.dataset.sortable || 'text';
      if (sortState.col === colIndex) {
        sortState.dir = sortState.dir === 'asc' ? 'desc' : 'asc';
      } else {
        sortState.col = colIndex;
        sortState.dir = 'asc';
      }

      headers.forEach(function (h, i) {
        var icon = h.querySelector('.adx-sort-icon');
        if (!icon) return;
        if (i === colIndex) {
          h.setAttribute('aria-sort', sortState.dir === 'asc' ? 'ascending' : 'descending');
          icon.textContent = sortIcon(sortState.dir);
          h.classList.add('adx-sort-th--active');
        } else {
          h.setAttribute('aria-sort', 'none');
          icon.textContent = '↕';
          h.classList.remove('adx-sort-th--active');
        }
      });

      var groups = collectRowGroups(tbody);
      if (groups.length < 2) return;
      var dir = sortState.dir;
      groups.sort(function (ga, gb) {
        return compareValues(getValue(ga, colIndex, type), getValue(gb, colIndex, type), dir);
      });
      groups.forEach(function (group) {
        group.forEach(function (row) { tbody.appendChild(row); });
      });
    }

    headers.forEach(function (th, colIndex) {
      if (th.dataset.sortable === 'false') return;
      if (th.getAttribute('aria-label') && !th.textContent.trim()) return;
      enhanceHeader(th, function () { applySort(colIndex); });
    });
  }

  function bindMemberList(container) {
    if (!container || container.dataset.sortListBound) return;
    var head = container.querySelector('.adx-member-head');
    if (!head) return;
    container.dataset.sortListBound = '1';

    var cols = Array.from(head.children);
    var sortState = { col: -1, dir: 'asc' };

    function rowValue(row, key, type) {
      var attr = row.getAttribute('data-sort-' + key);
      if (attr != null) return parseValue(attr, type);
      return '';
    }

    function applySort(colIndex) {
      var col = cols[colIndex];
      var key = col.dataset.sortKey;
      var type = col.dataset.sortable || 'text';
      if (!key) return;

      if (sortState.col === colIndex) {
        sortState.dir = sortState.dir === 'asc' ? 'desc' : 'asc';
      } else {
        sortState.col = colIndex;
        sortState.dir = 'asc';
      }

      cols.forEach(function (c, i) {
        var icon = c.querySelector('.adx-sort-icon');
        if (!icon) return;
        if (i === colIndex) {
          c.setAttribute('aria-sort', sortState.dir === 'asc' ? 'ascending' : 'descending');
          icon.textContent = sortIcon(sortState.dir);
          c.classList.add('adx-sort-th--active');
        } else {
          c.setAttribute('aria-sort', 'none');
          icon.textContent = '↕';
          c.classList.remove('adx-sort-th--active');
        }
      });

      var rows = Array.from(container.querySelectorAll('.adx-member-row'));
      if (rows.length < 2) return;
      var dir = sortState.dir;
      rows.sort(function (a, b) {
        return compareValues(rowValue(a, key, type), rowValue(b, key, type), dir);
      });
      rows.forEach(function (row) { container.appendChild(row); });
    }

    cols.forEach(function (col, colIndex) {
      if (!col.dataset.sortKey || col.dataset.sortable === 'false') return;
      enhanceHeader(col, function () { applySort(colIndex); });
    });
  }

  function bindAll(root) {
    var scope = root || document;
    scope.querySelectorAll('table').forEach(bindTable);
    scope.querySelectorAll('.adx-member-list').forEach(bindMemberList);
  }

  window.AdminTableSort = { bind: bindTable, bindMemberList: bindMemberList, bindAll: bindAll };
})(window);

/* ponytail: O(n log n) client sort; upgrade path = server-side sort for large lists */
if (typeof process === 'undefined') {
  (function () {
    function cmp(a, b, dir) {
      if (a < b) return dir === 'asc' ? -1 : 1;
      if (a > b) return dir === 'asc' ? 1 : -1;
      return 0;
    }
    if (cmp(1, 2, 'asc') !== -1 || cmp(2, 1, 'desc') !== 1) throw new Error('AdminTableSort compare failed');
  })();
}
