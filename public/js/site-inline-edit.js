/* Existing-site page editor bridge (?cms_edit=1, admin only). */
(function () {
  'use strict';

  if (window.parent === window || !window.__CMS_SITE_PAGE_KEY__) return;
  var pageKey = String(window.__CMS_SITE_PAGE_KEY__);

  function post(payload) {
    window.parent.postMessage(
      Object.assign({ source: 'cms-site-inline', pageKey: pageKey }, payload),
      window.location.origin
    );
  }

  function slotKey(el) {
    return (
      el.getAttribute('data-cms-text') ||
      el.getAttribute('data-cms-button') ||
      el.getAttribute('data-cms-slot') ||
      ''
    );
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

  var style = document.createElement('style');
  style.textContent =
    '[data-cms-text],[data-cms-button],[data-cms-slot]{' +
    'outline:1px dashed rgba(59,130,246,.55);outline-offset:3px;cursor:pointer;' +
    'transition:outline-color .15s,box-shadow .15s}' +
    '[data-cms-text]:hover,[data-cms-button]:hover,[data-cms-slot]:hover{' +
    'outline-color:#2563eb;box-shadow:0 0 0 4px rgba(37,99,235,.1)}' +
    '[data-cms-text]:focus,[data-cms-button]:focus{' +
    'outline:2px solid #2563eb;box-shadow:0 0 0 4px rgba(37,99,235,.14)}';
  document.head.appendChild(style);

  document.addEventListener(
    'click',
    function (event) {
      var editable = event.target.closest('[data-cms-text],[data-cms-button],[data-cms-slot]');
      var link = event.target.closest('a[href]');
      if (link) event.preventDefault();
      if (!editable) return;
      event.preventDefault();
      event.stopPropagation();
      post({
        type: editable.hasAttribute('data-cms-slot') ? 'select-image' : 'select-slot',
        slotKey: slotKey(editable),
      });
    },
    true
  );

  document.querySelectorAll('[data-cms-text],[data-cms-button]').forEach(function (el) {
    var original = (el.textContent || '').trim();
    el.setAttribute('contenteditable', 'true');
    el.setAttribute('spellcheck', 'false');
    el.title = '點擊編輯';
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
    el.addEventListener('blur', function () {
      var value = (el.textContent || '').trim();
      if (value === original) return;
      original = value;
      post({
        type: 'inline-edit',
        slotKey: slotKey(el),
        value: value,
        href: el.hasAttribute('data-cms-button') ? el.getAttribute('href') || '' : '',
      });
    });
  });

  document.querySelectorAll('[data-cms-slot]').forEach(function (el) {
    el.title = '點擊上傳／裁切更換圖片';
  });

  document.querySelectorAll('a[href]').forEach(function (link) {
    link.addEventListener('click', function (event) {
      event.preventDefault();
    });
  });

  function escapeAttr(value) {
    if (window.CSS && typeof CSS.escape === 'function') return CSS.escape(value);
    return String(value).replace(/\\/g, '\\\\').replace(/"/g, '\\"');
  }

  function findCopyEl(key) {
    if (!key) return null;
    var sel = escapeAttr(String(key));
    return (
      document.querySelector('[data-cms-text="' + sel + '"]') ||
      document.querySelector('[data-cms-button="' + sel + '"]') ||
      document.querySelector('[data-cms-slot="' + sel + '"]')
    );
  }

  function applyCopySlot(slotKey, text, href) {
    var el = findCopyEl(slotKey);
    if (!el) return false;
    if (el.hasAttribute('data-cms-slot')) return false;
    el.textContent = text == null ? '' : String(text);
    if (el.hasAttribute('data-cms-button') && href != null) {
      el.setAttribute('href', String(href));
    }
    return true;
  }

  function applyImageSlot(slotKey, url, alt) {
    var el = findCopyEl(slotKey);
    if (!el || !url) return false;
    var img = el.tagName === 'IMG' ? el : el.querySelector('img');
    if (!img) {
      if (el.tagName === 'IMG') img = el;
      else return false;
    }
    img.setAttribute('src', String(url));
    if (alt != null && alt !== '') img.setAttribute('alt', String(alt));
    var picture = img.closest('picture');
    if (picture) {
      picture.querySelectorAll('source').forEach(function (source) {
        source.removeAttribute('srcset');
      });
    }
    return true;
  }

  window.addEventListener('message', function (event) {
    if (event.origin !== window.location.origin) return;
    if (event.source !== window.parent) return;
    var data = event.data;
    if (!data || data.source !== 'cms-editor') return;
    if (data.type === 'apply-copy-slot') {
      post({
        type: 'preview-ack',
        action: 'apply-copy-slot',
        slotKey: data.slotKey,
        ok: applyCopySlot(data.slotKey, data.text, data.href),
      });
      return;
    }
    if (data.type === 'apply-image-slot') {
      post({
        type: 'preview-ack',
        action: 'apply-image-slot',
        slotKey: data.slotKey,
        ok: applyImageSlot(data.slotKey, data.url, data.alt),
      });
    }
  });

  post({ type: 'ready' });
})();
