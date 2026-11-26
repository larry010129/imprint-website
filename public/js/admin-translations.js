/* 銘印鑽石｜內容管理「翻譯」分頁：檢視與修正自動翻譯 */
(function () {
  'use strict';

  var LANGS = [
    { value: 'en', label: '英文' },
    { value: 'ja', label: '日文' },
    { value: 'ko', label: '韓文' },
  ];
  var PAGE_SIZE = 20;
  var state = { lang: 'en', search: '', page: 1, editing: '' };
  var latestRequest = 0;

  function el(tag, props, children) {
    var node = document.createElement(tag);
    Object.keys(props || {}).forEach(function (key) { node[key] = props[key]; });
    (children || []).forEach(function (child) { node.appendChild(child); });
    return node;
  }

  function note(text, warn) {
    return el('p', { className: warn ? 'note warn' : 'note', textContent: text });
  }

  function button(text, onClick, primary) {
    var node = el('button', {
      type: 'button',
      className: primary ? 'btn-sm btn-primary' : 'btn-sm',
      textContent: text,
    });
    node.addEventListener('click', onClick);
    return node;
  }

  function toast(message, type) {
    if (window.showToast) window.showToast(message, type);
  }

  function hasUnsavedEdit(root) {
    var box = root.querySelector('textarea[data-original]');
    return !!box && box.value !== box.getAttribute('data-original');
  }

  function mayDiscard(root) {
    return !hasUnsavedEdit(root) || window.confirm('尚未儲存的修改將會遺失，要繼續嗎？');
  }

  function translationCell(root, item) {
    var cell = el('td', { className: 'adx-tr-text' });
    if (state.editing !== item.sourceHash) {
      cell.appendChild(el('div', { className: 'adx-tr-value', lang: item.lang, textContent: item.translated }));
      return cell;
    }
    var box = el('textarea', {
      className: 'adx-tr-input',
      lang: item.lang,
      value: item.translated,
      rows: Math.min(14, Math.max(3, item.translated.split('\n').length + 1)),
    });
    box.setAttribute('aria-label', '翻譯內容');
    // The browser normalises line breaks, so compare against what the box holds.
    box.setAttribute('data-original', box.value);
    cell.appendChild(box);
    return cell;
  }

  function save(root, item, cell, buttons) {
    var box = cell.querySelector('textarea');
    var text = box.value;
    if (!text.trim()) {
      toast('翻譯內容不可空白', 'error');
      return;
    }
    buttons.forEach(function (b) { b.disabled = true; });
    window.imprintAPI.admin.updateTranslation({
      sourceHash: item.sourceHash,
      lang: item.lang,
      translated: text,
    }).then(function (res) {
      if (res.error) {
        // Keep the box open so the typed text is not lost.
        buttons.forEach(function (b) { b.disabled = false; });
        toast(String(res.error.message || res.error), 'error');
        if (!window.showToast) window.alert(String(res.error.message || res.error));
        return;
      }
      state.editing = '';
      toast('翻譯已儲存', 'success');
      // Repaint in place so the saved row does not jump to another page.
      root._items = root._items.map(function (other) {
        return other.sourceHash === item.sourceHash ? res.item : other;
      });
      paintRows(root);
    });
  }

  function row(root, item) {
    var source = el('td', { className: 'adx-tr-text' }, [
      el('div', { className: 'adx-tr-value', lang: 'zh-Hant', textContent: item.source }),
    ]);
    var translation = translationCell(root, item);
    var status = el('td', { textContent: item.edited ? '已手動修改' : '自動翻譯' });
    var actions = el('td', { className: 'adx-tr-actions' });
    if (state.editing === item.sourceHash) {
      var buttons = [];
      buttons.push(button('儲存', function () { save(root, item, translation, buttons); }, true));
      buttons.push(button('取消', function () {
        if (!mayDiscard(root)) return;
        state.editing = '';
        paintRows(root);
      }));
      buttons.forEach(function (b) { actions.appendChild(b); });
    } else {
      actions.appendChild(button('編輯', function () {
        if (!mayDiscard(root)) return;
        state.editing = item.sourceHash;
        paintRows(root);
        var box = root.querySelector('textarea[data-original]');
        if (box) box.focus();
      }));
    }
    return el('tr', {}, [source, translation, status, actions]);
  }

  function pager(root, total) {
    var pages = Math.max(1, Math.ceil(total / PAGE_SIZE));
    function go(next) {
      if (!mayDiscard(root)) return;
      // The tab and the sidebar panel share state: page within this copy's query.
      state.lang = root._query.lang;
      state.search = root._query.search;
      state.page = next;
      state.editing = '';
      load(root);
    }
    var previous = button('上一頁', function () { go(state.page - 1); });
    var next = button('下一頁', function () { go(state.page + 1); });
    previous.disabled = state.page <= 1;
    next.disabled = state.page >= pages;
    return el('div', { className: 'adx-tr-pager' }, [
      previous,
      el('span', { textContent: '第 ' + state.page + ' / ' + pages + ' 頁，共 ' + total + ' 筆' }),
      next,
    ]);
  }

  function paintRows(root) {
    var body = root.querySelector('.adx-tr-rows');
    var items = root._items;
    body.textContent = '';
    var head = el('tr', {}, ['中文原文', '翻譯', '狀態', '操作'].map(function (label) {
      return el('th', { textContent: label, scope: 'col' });
    }));
    var table = el('table', { className: 'adx-table adx-tr-table' }, [
      el('thead', {}, [head]),
      el('tbody', {}, items.map(function (item) { return row(root, item); })),
    ]);
    body.appendChild(el('div', { className: 'adx-table-wrap' }, [table]));
    body.appendChild(pager(root, root._total));
  }

  function load(root) {
    var body = root.querySelector('.adx-tr-results');
    var request = ++latestRequest;
    root._query = { lang: state.lang, search: state.search };
    body.setAttribute('aria-busy', 'true');
    window.imprintAPI.admin.getTranslations({
      lang: state.lang,
      q: state.search,
      page: state.page,
      pageSize: PAGE_SIZE,
    }).then(function (res) {
      // A slow earlier answer must not replace a newer one.
      if (request !== latestRequest || !body.isConnected) return;
      body.removeAttribute('aria-busy');
      body.textContent = '';
      state.editing = '';
      if (res.error) {
        body.appendChild(note('載入失敗：' + String(res.error.message || res.error), true));
        body.appendChild(button('重新載入', function () { load(root); }));
        return;
      }
      if (!res.ready) {
        body.appendChild(note('翻譯功能尚未完成設定：資料庫還沒有翻譯資料表。', true));
        return;
      }
      if (!res.enabled) {
        body.appendChild(note('自動翻譯未啟用（未設定 Google 金鑰）：新增或修改的內容不會自動翻譯，已儲存的翻譯仍會顯示在網站上。', true));
      }
      var items = res.items || [];
      var lastPage = Math.max(1, Math.ceil((res.total || 0) / PAGE_SIZE));
      if (!items.length && state.page > lastPage) {
        state.page = lastPage;
        load(root);
        return;
      }
      if (!items.length) {
        body.appendChild(note(state.search ? '找不到符合的翻譯。' : '目前沒有可修改的自動翻譯。'));
        return;
      }
      root._items = items;
      root._total = res.total || items.length;
      body.appendChild(el('div', { className: 'adx-tr-rows' }));
      paintRows(root);
    });
  }

  function render(container) {
    state.editing = '';
    var select = el('select', {}, LANGS.map(function (l) {
      return el('option', { value: l.value, textContent: l.label });
    }));
    select.value = state.lang;
    select.setAttribute('aria-label', '語言');
    var search = el('input', {
      type: 'search',
      value: state.search,
      placeholder: '搜尋中文或翻譯文字',
      maxLength: 200,
    });
    search.setAttribute('aria-label', '搜尋翻譯');
    var form = el('form', { className: 'adx-tr-tools' }, [
      select,
      search,
      el('button', { type: 'submit', className: 'btn-sm', textContent: '搜尋' }),
    ]);
    var results = el('div', { className: 'adx-tr-results' });
    var root = el('div', { className: 'adx-translations' }, [
      el('p', {
        className: 'adx-panel-note',
        textContent: '修正文章、商品、FAQ 等內容的自動翻譯。中文原文請到原本的分頁修改；原文一改會重新翻譯，之前的手動修改不會沿用。選單、按鈕等固定文字不在這裡。儲存後約一分鐘內顯示在網站上。',
      }),
      form,
      results,
    ]);
    function apply() {
      if (!mayDiscard(root)) {
        select.value = state.lang;
        return;
      }
      state.lang = select.value;
      state.search = search.value.trim();
      state.page = 1;
      state.editing = '';
      load(root);
    }
    select.addEventListener('change', apply);
    form.addEventListener('submit', function (event) {
      event.preventDefault();
      apply();
    });
    container.textContent = '';
    container.appendChild(root);
    load(root);
  }

  /* Sidebar panel: refresh on each visit, but never drop an unsaved edit. */
  function ensureLoaded(container) {
    if (container && !hasUnsavedEdit(container)) render(container);
  }

  window.AdminTranslations = {
    render: render,
    ensureLoaded: ensureLoaded,
    mayLeave: function (container) { return mayDiscard(container); },
  };
})();
