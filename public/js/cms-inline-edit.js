/* Inline click-to-edit bridge for CMS preview iframe (?inline=1 / cms_edit=1) */
(function () {
  'use strict';
  var root = document.querySelector('[data-cms-inline]');
  if (!root || window.parent === window) return;

  var selectedId = null;
  var menuEl = null;
  var dropGapsActive = false;
  var hoveredGap = null;
  var gapNodes = [];
  var sectionNodes = new Map();

  function post(payload) {
    window.parent.postMessage(Object.assign({ source: 'cms-inline' }, payload), window.location.origin);
  }
  function allStacks() {
    var stacks = Array.prototype.slice.call(
      document.querySelectorAll('[data-cms-site-stack][data-cms-anchor]')
    );
    if (stacks.length) return stacks;
    return [sectionRoot()];
  }
  function sectionRoot() {
    return document.querySelector('[data-cms-site-stack]') || root;
  }
  function endHost() {
    var stacks = allStacks();
    for (var i = 0; i < stacks.length; i++) {
      if (stacks[i].getAttribute('data-cms-anchor') === 'end') return stacks[i];
    }
    return stacks[stacks.length - 1] || sectionRoot();
  }
  function hostByAnchor(anchor) {
    if (!anchor) return null;
    var stacks = allStacks();
    for (var i = 0; i < stacks.length; i++) {
      if (stacks[i].getAttribute('data-cms-anchor') === String(anchor)) return stacks[i];
    }
    return null;
  }
  function hostSections(host) {
    return Array.prototype.slice.call(
      host.querySelectorAll(':scope > [data-cms-section-id]')
    );
  }
  function hideDropGaps() {
    dropGapsActive = false;
    hoveredGap = null;
    gapNodes.forEach(function (node) {
      if (node && node.parentNode) node.parentNode.removeChild(node);
    });
    gapNodes = [];
    post({ type: 'drop-index', index: null, anchor: null });
  }
  function highlightGap(gap) {
    hoveredGap = gap || null;
    gapNodes.forEach(function (node) {
      node.classList.toggle('is-active', hoveredGap !== null && node === hoveredGap);
    });
    if (!hoveredGap) {
      post({ type: 'drop-index', index: null, anchor: null });
      return;
    }
    var localIndex = Number(hoveredGap.getAttribute('data-cms-drop-index'));
    post({
      type: 'drop-index',
      index: Number.isFinite(localIndex) ? localIndex : null,
      anchor: hoveredGap.getAttribute('data-cms-drop-anchor') || null,
    });
  }
  function makeGap(anchor, localIndex) {
    var gap = document.createElement('div');
    gap.className = 'cms-drop-gap';
    gap.setAttribute('data-cms-drop-gap', String(localIndex));
    gap.setAttribute('data-cms-drop-anchor', String(anchor || 'end'));
    gap.setAttribute('data-cms-drop-index', String(localIndex));
    gap.setAttribute('aria-hidden', 'true');
    return gap;
  }
  function showDropGaps() {
    hideDropGaps();
    dropGapsActive = true;
    var stacks = allStacks();
    for (var s = 0; s < stacks.length; s++) {
      var host = stacks[s];
      var anchor = host.getAttribute('data-cms-anchor') || 'end';
      var sections = hostSections(host);
      var count = sections.length;
      for (var i = 0; i <= count; i++) {
        var gap = makeGap(anchor, i);
        if (i < count) {
          host.insertBefore(gap, sections[i]);
        } else if (count) {
          var last = sections[count - 1];
          if (last.nextSibling) host.insertBefore(gap, last.nextSibling);
          else host.appendChild(gap);
        } else {
          var empty = host.querySelector(':scope > .cms-section--empty');
          if (empty) host.insertBefore(gap, empty);
          else host.insertBefore(gap, host.firstChild);
        }
        gapNodes.push(gap);
      }
    }
    if (gapNodes.length) highlightGap(gapNodes[gapNodes.length - 1]);
  }
  function hoverDropAt(relativeY) {
    if (!dropGapsActive || !gapNodes.length) return;
    var y = Number(relativeY) + (window.scrollY || 0);
    var best = gapNodes[0];
    var bestDist = Infinity;
    for (var i = 0; i < gapNodes.length; i++) {
      var rect = gapNodes[i].getBoundingClientRect();
      var mid = rect.top + window.scrollY + rect.height / 2;
      var dist = Math.abs(mid - y);
      if (dist < bestDist) {
        bestDist = dist;
        best = gapNodes[i];
      }
    }
    highlightGap(best);
  }
  function escapeAttr(value) {
    if (window.CSS && typeof CSS.escape === 'function') return CSS.escape(value);
    return String(value).replace(/\\/g, '\\\\').replace(/"/g, '\\"');
  }
  function findSection(id) {
    if (!id) return null;
    var key = String(id);
    var cached = sectionNodes.get(key);
    if (cached && cached.isConnected) return cached;
    if (cached) sectionNodes.delete(key);
    var stacks = allStacks();
    var sel = '[data-cms-section-id="' + escapeAttr(key) + '"]';
    for (var i = 0; i < stacks.length; i++) {
      var found = stacks[i].querySelector(sel);
      if (found) {
        sectionNodes.set(key, found);
        return found;
      }
    }
    var fallback = document.querySelector(sel);
    if (fallback) sectionNodes.set(key, fallback);
    return fallback;
  }
  function insertPlainText(text) {
    var selection = window.getSelection();
    if (!selection || !selection.rangeCount) return;
    selection.deleteFromDocument();
    var node = document.createTextNode(text);
    var range = selection.getRangeAt(0);
    range.insertNode(node);
    range.setStartAfter(node);
    range.collapse(true);
    selection.removeAllRanges();
    selection.addRange(range);
  }
  function hideMenu() {
    if (menuEl) {
      menuEl.remove();
      menuEl = null;
    }
  }
  function showMenu(x, y, sectionId) {
    hideMenu();
    menuEl = document.createElement('div');
    menuEl.className = 'cms-section-ctx';
    menuEl.setAttribute('role', 'menu');
    var btn = document.createElement('button');
    btn.type = 'button';
    btn.className = 'cms-section-ctx__item';
    btn.setAttribute('role', 'menuitem');
    btn.textContent = '刪除區塊';
    btn.addEventListener('click', function (ev) {
      ev.preventDefault();
      hideMenu();
      post({ type: 'delete-section', sectionId: sectionId });
    });
    menuEl.appendChild(btn);
    document.body.appendChild(menuEl);
    var rect = menuEl.getBoundingClientRect();
    var left = Math.min(x, window.innerWidth - rect.width - 8);
    var top = Math.min(y, window.innerHeight - rect.height - 8);
    menuEl.style.left = Math.max(8, left) + 'px';
    menuEl.style.top = Math.max(8, top) + 'px';
  }
  function setSelected(sectionId) {
    selectedId = sectionId ? String(sectionId) : null;
    allStacks().forEach(function (host) {
      host.querySelectorAll('[data-cms-section-id].is-cms-selected').forEach(function (el) {
        el.classList.remove('is-cms-selected');
      });
    });
    if (!selectedId) return;
    var el = findSection(selectedId);
    if (el) el.classList.add('is-cms-selected');
  }
  function wireEditable(el) {
    if (el.getAttribute('data-cms-wired') === '1') return;
    var mode = el.getAttribute('data-cms-editable');
    var prop = el.getAttribute('data-cms-prop');
    if (!prop) return;
    var section = el.closest('[data-cms-section-id]');
    if (!section) return;
    var sectionId = section.getAttribute('data-cms-section-id');
    el.setAttribute('data-cms-wired', '1');

    if (mode === 'text' || mode === 'button') {
      el.setAttribute('contenteditable', 'true');
      el.setAttribute('spellcheck', 'false');
      el.addEventListener('paste', function (event) {
        event.preventDefault();
        insertPlainText(event.clipboardData ? event.clipboardData.getData('text/plain') : '');
      });
      el.addEventListener('keydown', function (event) {
        if (event.isComposing) return;
        if (event.key !== 'Enter') return;
        event.preventDefault();
        el.blur();
      });
      if (el.tagName === 'A') {
        el.addEventListener('click', function (ev) {
          ev.preventDefault();
        });
      }
      el.addEventListener('blur', function () {
        var blockId = el.getAttribute('data-cms-block-id');
        var blockField = el.getAttribute('data-cms-block-field');
        if (blockId && blockField) {
          var blockPayload = {
            type: 'block-edit',
            sectionId: sectionId,
            blockId: blockId,
            field: blockField,
            value: (el.textContent || '').trim(),
          };
          var blockHrefProp = el.getAttribute('data-cms-href-prop');
          if (blockHrefProp && el.tagName === 'A') {
            blockPayload.href = el.getAttribute('href') || '';
          }
          post(blockPayload);
          return;
        }
        var payload = {
          type: 'inline-edit',
          sectionId: sectionId,
          prop: prop,
          value: (el.textContent || '').trim(),
        };
        var hrefProp = el.getAttribute('data-cms-href-prop');
        if (hrefProp && el.tagName === 'A') {
          payload.hrefProp = hrefProp;
          payload.href = el.getAttribute('href') || '';
        }
        var buttonIndex = el.getAttribute('data-cms-button-index');
        if (buttonIndex !== null && buttonIndex !== '') {
          payload.buttonIndex = Number(buttonIndex);
          payload.href = el.getAttribute('href') || '';
        }
        post(payload);
      });
    }

    if (mode === 'image_url') {
      el.style.cursor = 'pointer';
      el.title = el.tagName === 'IMG' ? '點擊上傳／裁切更換圖片' : '點擊上傳圖片';
      el.addEventListener('click', function (ev) {
        ev.preventDefault();
        ev.stopPropagation();
        var blockId = el.getAttribute('data-cms-block-id');
        post({
          type: 'edit-image',
          sectionId: sectionId,
          prop: prop,
          blockId: blockId || null,
        });
      });
    }
  }

  function wireSection(sectionEl) {
    if (!sectionEl) return;
    var sectionId = sectionEl.getAttribute('data-cms-section-id');
    if (sectionId) sectionNodes.set(String(sectionId), sectionEl);
    sectionEl.querySelectorAll('[data-cms-editable]').forEach(wireEditable);
    if (sectionEl.getAttribute('data-cms-visible') === '0') {
      sectionEl.classList.add('cms-section--editor-hidden');
    }
  }

  function wireAll() {
    sectionNodes.clear();
    allStacks().forEach(function (host) {
      host.querySelectorAll('[data-cms-section-id]').forEach(wireSection);
    });
  }
  function clearEmptyPlaceholder(host) {
    var targets = host ? [host] : allStacks();
    targets.forEach(function (stack) {
      stack.querySelectorAll('.cms-section--empty').forEach(function (el) {
        el.remove();
      });
      stack.classList.remove('cms-site-stack--empty');
    });
  }
  function ensureEmptyPlaceholder(host) {
    if (!host || !host.hasAttribute('data-cms-site-stack')) return;
    if (host.querySelector('[data-cms-section-id]')) return;
    host.classList.add('cms-site-stack--empty');
    if (host.querySelector('.cms-section--empty')) return;
    var empty = document.createElement('section');
    empty.className = 'cms-section cms-section--empty';
    var anchor = host.getAttribute('data-cms-anchor') || 'end';
    empty.innerHTML =
      '<div class="container"><p>拖曳區塊到此藍色插入線放置（錨點：' +
      anchor +
      '）。</p></div>';
    host.appendChild(empty);
  }
  function applySectionHtml(html, sectionId, beforeId, anchor) {
    if (!html || !sectionId) return false;
    var wrap = document.createElement('div');
    wrap.innerHTML = String(html).trim();
    var next = wrap.querySelector('[data-cms-section-id]') || wrap.firstElementChild;
    if (!next) return false;
    var existing = findSection(sectionId);
    if (existing) {
      clearEmptyPlaceholder(existing.parentElement);
      existing.replaceWith(next);
      sectionNodes.delete(String(sectionId));
      wireSection(next);
      if (selectedId === String(sectionId)) next.classList.add('is-cms-selected');
      return true;
    }
    var before = beforeId ? findSection(beforeId) : null;
    var host =
      hostByAnchor(anchor) ||
      (before && before.parentElement) ||
      endHost();
    clearEmptyPlaceholder(host);
    // Never follow beforeId across hosts — that collapses mid-page inserts into end.
    if (before && before.parentNode === host) {
      host.insertBefore(next, before);
    } else {
      host.appendChild(next);
    }
    wireSection(next);
    if (selectedId === String(sectionId)) next.classList.add('is-cms-selected');
    return true;
  }
  function removeSection(sectionId) {
    var el = findSection(sectionId);
    if (!el) return false;
    var host = el.parentElement;
    el.remove();
    sectionNodes.delete(String(sectionId));
    if (selectedId === String(sectionId)) selectedId = null;
    if (host) ensureEmptyPlaceholder(host);
    return true;
  }
  function reorderSections(ids) {
    if (!Array.isArray(ids) || !ids.length) return false;
    var byParent = new Map();
    var orphans = [];
    for (var i = 0; i < ids.length; i++) {
      var node = findSection(ids[i]);
      if (!node) return false;
      var parent = node.parentNode;
      if (!parent) {
        orphans.push(node);
        continue;
      }
      if (!byParent.has(parent)) byParent.set(parent, []);
      byParent.get(parent).push(node);
    }
    byParent.forEach(function (nodes, parent) {
      nodes.forEach(function (node) {
        parent.appendChild(node);
      });
    });
    if (orphans.length) {
      var fallback = endHost();
      orphans.forEach(function (node) {
        fallback.appendChild(node);
      });
    }
    return true;
  }
  function setVisible(sectionId, visible) {
    var el = findSection(sectionId);
    if (!el) return false;
    el.classList.toggle('cms-section--editor-hidden', !visible);
    el.setAttribute('data-cms-visible', visible ? '1' : '0');
    return true;
  }

  // Never leave the page being edited — all pages used to navigate to the same
  // site destinations (nav/CTA), which made every preview feel identical.
  document.addEventListener(
    'click',
    function (e) {
      hideMenu();
      var link = e.target.closest('a[href]');
      if (!link) return;
      var href = link.getAttribute('href') || '';
      if (!href || href.charAt(0) === '#') return;
      e.preventDefault();
      e.stopPropagation();
    },
    true
  );

  document.addEventListener('click', function (e) {
    var section = e.target.closest('[data-cms-section-id]');
    if (!section || !section.closest('[data-cms-inline]')) return;
    var id = section.getAttribute('data-cms-section-id');
    setSelected(id);
    post({ type: 'select-section', sectionId: id });
  });

  document.addEventListener('contextmenu', function (e) {
    var section = e.target.closest('[data-cms-section-id]');
    if (!section || !section.closest('[data-cms-inline]')) return;
    e.preventDefault();
    e.stopPropagation();
    var id = section.getAttribute('data-cms-section-id');
    setSelected(id);
    post({ type: 'select-section', sectionId: id });
    showMenu(e.clientX, e.clientY, id);
  });

  document.addEventListener('keydown', function (event) {
    if (event.key !== 'Delete') return;
    if (event.target.closest('input, textarea, select, [contenteditable="true"]')) return;
    if (!selectedId) return;
    event.preventDefault();
    post({ type: 'delete-section', sectionId: selectedId });
  });

  window.addEventListener('message', function (event) {
    if (event.origin !== window.location.origin) return;
    if (event.source !== window.parent) return;
    var data = event.data;
    if (!data || data.source !== 'cms-editor') return;
    if (data.type === 'apply-section') {
      var ok = applySectionHtml(
        data.html,
        data.sectionId,
        data.beforeId || null,
        data.anchor || null
      );
      post({
        type: 'preview-ack',
        action: 'apply-section',
        replyTo: data.requestId || null,
        sectionId: data.sectionId,
        ok: ok
      });
      return;
    }
    if (data.type === 'remove-section') {
      post({
        type: 'preview-ack',
        action: 'remove-section',
        replyTo: data.requestId || null,
        sectionId: data.sectionId,
        ok: removeSection(data.sectionId),
      });
      return;
    }
    if (data.type === 'reorder-sections') {
      post({
        type: 'preview-ack',
        action: 'reorder-sections',
        replyTo: data.requestId || null,
        ok: reorderSections(data.sectionIds || []),
      });
      return;
    }
    if (data.type === 'select-section') {
      setSelected(data.sectionId || null);
      return;
    }
    if (data.type === 'set-visible') {
      post({
        type: 'preview-ack',
        action: 'set-visible',
        replyTo: data.requestId || null,
        sectionId: data.sectionId,
        ok: setVisible(data.sectionId, !!data.visible),
      });
      return;
    }
    if (data.type === 'show-drop-gaps') {
      showDropGaps();
      return;
    }
    if (data.type === 'hide-drop-gaps') {
      hideDropGaps();
      return;
    }
    if (data.type === 'hover-drop') {
      hoverDropAt(data.relativeY);
      return;
    }
    if (data.type === 'get-drop-index') {
      var index = null;
      var anchor = null;
      if (hoveredGap) {
        index = Number(hoveredGap.getAttribute('data-cms-drop-index'));
        if (!Number.isFinite(index)) index = null;
        anchor = hoveredGap.getAttribute('data-cms-drop-anchor') || null;
      } else if (dropGapsActive && gapNodes.length) {
        var fallback = gapNodes[gapNodes.length - 1];
        index = Number(fallback.getAttribute('data-cms-drop-index'));
        if (!Number.isFinite(index)) index = null;
        anchor = fallback.getAttribute('data-cms-drop-anchor') || null;
      }
      post({
        type: 'drop-index',
        index: index,
        anchor: anchor,
        replyTo: data.requestId || null,
      });
    }
  });

  wireAll();
  post({ type: 'ready' });
})();
