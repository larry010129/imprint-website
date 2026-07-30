/* Editor-only canvas gaps, section toolbar, shortcuts, and patch ACKs. */
(function () {
  'use strict';
  var root = document.querySelector('[data-cms-inline]');
  if (!root || window.parent === window) return;

  var selectedId = null;
  var sectionIndex = Object.create(null);
  var observer = new MutationObserver(scheduleRender);
  var renderQueued = false;
  var typeLabels = {
    hero: 'Hero',
    rich_text: '文字',
    image_text: '圖文',
    cta_band: 'CTA',
    faq_embed: 'FAQ',
    testimonials_embed: '見證',
    button_row: '按鈕列',
    spacer: '間距',
    freeform: '自由版面'
  };
  var primaryProps = {
    button_row: 'buttons',
    spacer: 'size',
    faq_embed: 'limit',
    testimonials_embed: 'limit',
    freeform: 'height'
  };

  function post(payload) {
    window.parent.postMessage(
      Object.assign({ source: 'cms-inline' }, payload),
      window.location.origin
    );
  }

  function hosts() {
    var site = Array.prototype.slice.call(
      document.querySelectorAll('[data-cms-site-stack][data-cms-anchor]')
    );
    return site.length ? site : [root];
  }

  function directSections(host) {
    return Array.prototype.filter.call(host.children, function (node) {
      return node.hasAttribute && node.hasAttribute('data-cms-section-id');
    });
  }

  function sectionById(id) {
    if (!id) return null;
    var key = String(id);
    var cached = sectionIndex[key];
    if (cached && cached.isConnected) return cached;
    var section = document.querySelector(
      '[data-cms-section-id="' + String(id).replace(/\\/g, '\\\\').replace(/"/g, '\\"') + '"]'
    );
    if (section) sectionIndex[key] = section;
    return section;
  }

  function addButton(host, anchor, index, beforeId) {
    var wrap = document.createElement('div');
    wrap.className = 'cms-canvas-add';
    wrap.setAttribute('data-cms-add-control', '1');
    var button = document.createElement('button');
    button.type = 'button';
    button.className = 'cms-canvas-add__button';
    button.textContent = '+ 新增區塊';
    button.setAttribute('aria-label', '在第 ' + (index + 1) + ' 個位置新增區塊');
    button.setAttribute('data-cms-add-anchor', anchor);
    button.setAttribute('data-cms-add-index', String(index));
    if (beforeId) button.setAttribute('data-cms-add-before', beforeId);
    button.addEventListener('click', function (event) {
      event.preventDefault();
      event.stopPropagation();
      post({
        type: 'open-add',
        anchor: anchor,
        index: index,
        beforeId: beforeId || null
      });
    });
    wrap.appendChild(button);
    return wrap;
  }

  function toolbarButton(label, action, extra) {
    var button = document.createElement('button');
    button.type = 'button';
    button.textContent = label;
    button.setAttribute('aria-label', label);
    button.addEventListener('click', function (event) {
      event.preventDefault();
      event.stopPropagation();
      post(Object.assign({ type: action, sectionId: selectedId }, extra || {}));
    });
    return button;
  }

  function renderToolbar(section) {
    if (!section || !selectedId) return;
    var sectionType = section.getAttribute('data-cms-section-type') || '';
    var toolbar = document.createElement('div');
    toolbar.className = 'cms-canvas-toolbar';
    toolbar.setAttribute('data-cms-context-toolbar', '1');
    toolbar.setAttribute('role', 'toolbar');
    toolbar.setAttribute('aria-label', '所選區塊工具');
    toolbar.appendChild(
      toolbarButton('快速編輯', 'focus-prop', { prop: primaryProps[sectionType] || 'title' })
    );
    toolbar.appendChild(toolbarButton('複製', 'duplicate-section'));
    toolbar.appendChild(toolbarButton('上移', 'move-section', { direction: 'up' }));
    toolbar.appendChild(toolbarButton('下移', 'move-section', { direction: 'down' }));
    toolbar.appendChild(
      toolbarButton(
        section.getAttribute('data-cms-visible') === '0' ? '顯示' : '隱藏',
        'toggle-section'
      )
    );
    toolbar.appendChild(toolbarButton('刪除', 'delete-section'));
    section.appendChild(toolbar);
  }

  function render() {
    renderQueued = false;
    observer.disconnect();
    sectionIndex = Object.create(null);
    document.querySelectorAll('[data-cms-add-control],[data-cms-context-toolbar]').forEach(
      function (node) { node.remove(); }
    );
    hosts().forEach(function (host) {
      var anchor = host.getAttribute('data-cms-anchor') || 'end';
      var sections = directSections(host);
      for (var index = 0; index <= sections.length; index += 1) {
        var before = sections[index] || null;
        var beforeId = before ? before.getAttribute('data-cms-section-id') : null;
        var add = addButton(host, anchor, index, beforeId);
        if (before) host.insertBefore(add, before);
        else host.appendChild(add);
      }
      sections.forEach(function (section) {
        var id = section.getAttribute('data-cms-section-id') || '';
        if (id) sectionIndex[id] = section;
        var type = section.getAttribute('data-cms-section-type') || '內容';
        section.tabIndex = 0;
        section.setAttribute('role', 'group');
        section.setAttribute('aria-label', (typeLabels[type] || type) + ' 區塊');
        section.setAttribute('aria-selected', id === selectedId ? 'true' : 'false');
        section.classList.toggle('is-cms-selected', id === selectedId);
      });
    });
    renderToolbar(sectionById(selectedId));
    observer.observe(root, { childList: true, subtree: true });
  }

  function scheduleRender() {
    if (renderQueued) return;
    renderQueued = true;
    requestAnimationFrame(render);
  }

  function select(section, focusProp) {
    if (!section) return;
    selectedId = section.getAttribute('data-cms-section-id');
    post({ type: 'select-section', sectionId: selectedId });
    if (focusProp) {
      post({ type: 'focus-prop', sectionId: selectedId, prop: focusProp });
    }
    scheduleRender();
  }

  document.addEventListener('click', function (event) {
    if (event.target.closest('[data-cms-add-control],[data-cms-context-toolbar]')) return;
    var editable = event.target.closest('[data-cms-editable][data-cms-prop]');
    var section = event.target.closest('[data-cms-section-id]');
    if (!section || !section.closest('[data-cms-inline]')) return;
    select(section, editable ? editable.getAttribute('data-cms-prop') : null);
  }, true);

  document.addEventListener('keydown', function (event) {
    if (event.target.closest('input,textarea,select,[contenteditable="true"],button,a')) return;
    var section = event.target.closest('[data-cms-section-id]');
    if (!section) return;
    var id = section.getAttribute('data-cms-section-id');
    select(section);
    var key = event.key.toLowerCase();
    var action = null;
    var extra = {};
    if (event.key === 'Enter' || event.key === 'F2') {
      action = 'focus-prop';
      extra.prop =
        primaryProps[section.getAttribute('data-cms-section-type') || ''] || 'title';
    } else if ((event.ctrlKey || event.metaKey) && key === 'd') {
      action = 'duplicate-section';
    } else if (event.altKey && event.key === 'ArrowUp') {
      action = 'move-section';
      extra.direction = 'up';
    } else if (event.altKey && event.key === 'ArrowDown') {
      action = 'move-section';
      extra.direction = 'down';
    } else if ((event.key === 'Delete' || event.key === 'Backspace')) {
      action = 'delete-section';
    } else if ((event.ctrlKey || event.metaKey) && event.shiftKey && key === 'h') {
      action = 'toggle-section';
    } else if (event.key === 'Escape') {
      section.blur();
      return;
    }
    if (!action) return;
    event.preventDefault();
    post(Object.assign({ type: action, sectionId: id }, extra));
  });

  function acknowledge(data) {
    if (!data.requestId) return;
    window.setTimeout(function () {
      var ok = true;
      if (data.type === 'apply-section') ok = Boolean(sectionById(data.sectionId));
      if (data.type === 'remove-section') ok = !sectionById(data.sectionId);
      if (data.type === 'reorder-sections') {
        ok = Array.isArray(data.sectionIds) && data.sectionIds.every(sectionById);
      }
      if (data.type === 'set-visible') {
        var section = sectionById(data.sectionId);
        ok = Boolean(section) &&
          section.getAttribute('data-cms-visible') === (data.visible ? '1' : '0');
      }
      post({
        type: 'preview-ack',
        action: data.type,
        replyTo: data.requestId,
        ok: ok
      });
    }, 0);
  }

  window.addEventListener('message', function (event) {
    if (event.origin !== window.location.origin || event.source !== window.parent) return;
    var data = event.data;
    if (!data || data.source !== 'cms-editor') return;
    if (
      data.type === 'apply-section' ||
      data.type === 'remove-section' ||
      data.type === 'reorder-sections' ||
      data.type === 'set-visible'
    ) {
      acknowledge(data);
      scheduleRender();
    }
    if (data.type === 'select-section') {
      selectedId = data.sectionId ? String(data.sectionId) : null;
      scheduleRender();
    }
    if (data.type === 'focus-section') {
      var section = sectionById(data.sectionId);
      if (!section) return;
      selectedId = String(data.sectionId);
      scheduleRender();
      section.scrollIntoView({
        block: 'center',
        behavior: window.matchMedia('(prefers-reduced-motion: reduce)').matches
          ? 'auto'
          : 'smooth'
      });
      window.setTimeout(function () { section.focus(); }, 220);
    }
    if (data.type === 'focus-add-target') {
      var selector =
        '[data-cms-add-anchor="' + String(data.anchor) +
        '"][data-cms-add-index="' + String(data.index) + '"]';
      var add = document.querySelector(selector);
      if (add) add.focus();
    }
  });

  var style = document.createElement('style');
  style.textContent =
    '[data-cms-inline] [data-cms-section-id]{position:relative}' +
    '.cms-canvas-add{position:relative;height:0;z-index:70;text-align:center;overflow:visible}' +
    '.cms-canvas-add__button{position:relative;min-width:132px;min-height:44px;transform:translateY(-50%);' +
    'border:1px solid #2563eb;border-radius:999px;background:#fff;color:#1d4ed8;padding:0 16px;' +
    'font:600 13px/1 system-ui,sans-serif;box-shadow:0 4px 16px rgba(37,99,235,.18);opacity:.18;' +
    'transition:opacity .16s,transform .16s;cursor:pointer}' +
    '.cms-canvas-add:hover .cms-canvas-add__button,.cms-canvas-add__button:focus-visible{' +
    'opacity:1;transform:translateY(-50%) scale(1.03);outline:3px solid rgba(94,207,207,.75);outline-offset:2px}' +
    '.cms-canvas-toolbar{position:absolute;top:8px;right:8px;z-index:90;display:flex;flex-wrap:wrap;' +
    'gap:4px;padding:4px;border-radius:10px;background:rgba(15,23,42,.92);box-shadow:0 8px 24px rgba(0,0,0,.24)}' +
    '.cms-canvas-toolbar button{min-height:44px;border:0;border-radius:7px;background:transparent;color:#fff;' +
    'padding:0 10px;font:600 12px/1 system-ui,sans-serif;cursor:pointer}' +
    '.cms-canvas-toolbar button:hover{background:rgba(255,255,255,.16)}' +
    '.cms-canvas-toolbar button:focus-visible{outline:3px solid #5ecfcf;outline-offset:1px}' +
    '[data-cms-section-id]:focus-visible{outline:3px solid #5ecfcf!important;outline-offset:3px}' +
    '@media(max-width:640px),(pointer:coarse){.cms-canvas-add__button{opacity:.8}.cms-canvas-toolbar{' +
    'top:4px;right:4px;left:4px;justify-content:center}.cms-canvas-toolbar button{min-width:72px}}';
  document.head.appendChild(style);

  render();
})();
