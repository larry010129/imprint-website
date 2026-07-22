/* 鑽石腰圍刻字 — contenteditable + 圖騰 + 預覽（shop 試算 step 3、configurator 共用） */
(function () {
  'use strict';

  var EMBLEMS = {
    bow: { label: '蝴蝶結', svg: '<svg viewBox="0 0 24 24"><path d="M12 12L4 6v12l8-6z" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linejoin="round"/><path d="M12 12l8-6v12l-8-6z" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linejoin="round"/><circle cx="12" cy="12" r="1.6" fill="currentColor"/></svg>' },
    clover: { label: '幸運草', svg: '<svg viewBox="0 0 24 24"><g fill="none" stroke="currentColor" stroke-width="1.6"><circle cx="12" cy="7.5" r="3.6"/><circle cx="12" cy="16.5" r="3.6"/><circle cx="7.5" cy="12" r="3.6"/><circle cx="16.5" cy="12" r="3.6"/></g></svg>' },
    infinity: { label: '無限', svg: '<svg viewBox="0 0 24 24"><path d="M7 9a3 3 0 100 6 5 5 0 004-2 5 5 0 004 2 3 3 0 100-6 5 5 0 00-4 2 5 5 0 00-4-2z" fill="none" stroke="currentColor" stroke-width="1.6"/></svg>' },
    heart: { label: '愛心', svg: '<svg viewBox="0 0 24 24"><path d="M12 20s-7-4.6-9.3-9A5 5 0 0112 6a5 5 0 019.3 5c-2.3 4.4-9.3 9-9.3 9z" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linejoin="round"/></svg>' },
    hearts: { label: '雙愛心', svg: '<svg viewBox="0 0 24 24"><path d="M9 17s-5-3.2-6.6-6.3A3.6 3.6 0 019 8a3.6 3.6 0 016.6 2.7C14 13.8 9 17 9 17z" fill="none" stroke="currentColor" stroke-width="1.4"/><path d="M16.5 19.2s-4.4-2.8-5.7-5.5a3.1 3.1 0 015.7-2.3 3.1 3.1 0 015.7 2.3c-1.3 2.7-5.7 5.5-5.7 5.5z" fill="none" stroke="currentColor" stroke-width="1.4"/></svg>' },
    paw: { label: '肉球', svg: '<svg viewBox="0 0 24 24"><g fill="currentColor"><ellipse cx="12" cy="16.2" rx="5" ry="4"/><circle cx="5.6" cy="9.2" r="2"/><circle cx="10.4" cy="5.8" r="2"/><circle cx="13.6" cy="5.8" r="2"/><circle cx="18.4" cy="9.2" r="2"/></g></svg>' },
    bone: { label: '骨頭', svg: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><path d="M4.9 4.9a2.5 2.5 0 013.5 0l.7.7a2.5 2.5 0 010 3.6L7.8 10.6l5.6 5.6 1.3-1.4a2.5 2.5 0 013.6 0l.7.7a2.5 2.5 0 01-3.6 3.5l-.7-.7a2.5 2.5 0 010-3.5l-1.3 1.3-5.6-5.6-1.4 1.3a2.5 2.5 0 01-3.5 0l-.7-.7a2.5 2.5 0 010-3.6z"/></svg>' },
    ring: { label: '戒圈', svg: '<svg viewBox="0 0 24 24"><circle cx="12" cy="14.5" r="6" fill="none" stroke="currentColor" stroke-width="1.6"/><path d="M9.4 8.6L12 4l2.6 4.6" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linejoin="round"/></svg>' }
  };

  var LABEL_TO_NAME = {};
  Object.keys(EMBLEMS).forEach(function (name) {
    LABEL_TO_NAME[EMBLEMS[name].label] = name;
  });

  var ZWS = '\u200B';
  var EMBLEM_SLOT_COST = 2;
  // Typed text: A-Z / a-z / 0-9 always; Chinese (CJK Unified Ideographs) only once
  // the caller says the selected diamond is large enough to engrave it legibly
  // (0.3ct+ -- see setAllowChinese). Emblem tokens insert via buttons, not keys.
  var CHARSET_BASE = 'A-Za-z0-9';
  var CHARSET_CJK = 'A-Za-z0-9一-鿿㐀-䶿';

  function allowedCharRe(allowChinese) {
    return new RegExp('^[' + (allowChinese ? CHARSET_CJK : CHARSET_BASE) + ']$');
  }

  function disallowedCharsRe(allowChinese) {
    return new RegExp('[^' + (allowChinese ? CHARSET_CJK : CHARSET_BASE) + ']', 'g');
  }

  function stripZws(text) {
    return (text || '').replace(/\u200B/g, '');
  }

  function sanitizePlainText(text, allowChinese) {
    return stripZws(text).replace(disallowedCharsRe(allowChinese), '');
  }

  function sanitizeTextNodes(input, allowChinese) {
    if (!input) return false;
    var changed = false;
    input.childNodes.forEach(function (node) {
      if (node.nodeType !== 3) return;
      var raw = node.textContent || '';
      var keptZws = raw.indexOf(ZWS) >= 0;
      var clean = sanitizePlainText(raw, allowChinese);
      var next = keptZws && clean ? ZWS + clean : (keptZws && !clean ? ZWS : clean);
      if (next !== raw) {
        node.textContent = next;
        changed = true;
      }
    });
    return changed;
  }

  function nodeSlotCost(node) {
    if (node.nodeType === 3) return stripZws(node.textContent).length;
    if (node.nodeType === 1 && node.classList.contains('cfg-emblem-token')) return EMBLEM_SLOT_COST;
    return 0;
  }

  function slots(input) {
    if (!input) return 0;
    var count = 0;
    input.childNodes.forEach(function (node) {
      count += nodeSlotCost(node);
    });
    return count;
  }

  function readable(input) {
    if (!input) return '';
    var parts = [];
    input.childNodes.forEach(function (node) {
      if (node.nodeType === 3) {
        var text = stripZws(node.textContent);
        if (text) parts.push(text);
      } else if (node.nodeType === 1 && node.classList.contains('cfg-emblem-token')) {
        parts.push('〔' + (node.getAttribute('data-label') || '') + '〕');
      }
    });
    return parts.join('').trim();
  }

  function escapeHtml(str) {
    return String(str == null ? '' : str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

  /** Readable string → HTML with same SVG icons as typing buttons (safe to inject). */
  function toDisplayHtml(str) {
    if (!str) return '';
    var re = /〔([^〕]+)〕|[^〔〕]+/g;
    var match;
    var out = '';
    while ((match = re.exec(String(str)))) {
      if (match[0].charAt(0) === '〔') {
        var emblemName = LABEL_TO_NAME[match[1]];
        var def = emblemName ? EMBLEMS[emblemName] : null;
        if (def) {
          out +=
            '<span class="cfg-emblem-token" data-emblem="' + escapeHtml(emblemName) +
            '" data-label="' + escapeHtml(def.label) + '" aria-label="' + escapeHtml(def.label) + '">' +
            def.svg + '</span>';
        } else {
          out += escapeHtml(match[0]);
        }
      } else {
        out += escapeHtml(match[0]);
      }
    }
    return out;
  }

  function fillDisplay(el, str, emptyText) {
    if (!el) return;
    if (!str) {
      el.textContent = emptyText == null ? '' : emptyText;
      return;
    }
    el.innerHTML = toDisplayHtml(str);
  }

  function caretToken(input, range) {
    if (!range || !input) return null;
    var node = range.startContainer;
    if (node.nodeType === 1 && node.classList.contains('cfg-emblem-token') && input.contains(node)) return node;
    var el = node.nodeType === 3 ? node.parentElement : node;
    if (!el || !input.contains(el)) return null;
    var token = el.closest('.cfg-emblem-token');
    return token && input.contains(token) ? token : null;
  }

  function removeToken(token) {
    if (!token) return;
    var next = token.nextSibling;
    if (next && next.nodeType === 3) {
      var rest = stripZws(next.textContent);
      if (!rest) next.remove();
      else next.textContent = rest;
    }
    token.remove();
  }

  function placeCaretIn(input, node, offset) {
    var range = document.createRange();
    range.setStart(node, offset);
    range.collapse(true);
    var sel = window.getSelection();
    if (sel) { sel.removeAllRanges(); sel.addRange(range); }
  }

  function collapseToEnd(input) {
    var range = document.createRange();
    range.selectNodeContents(input);
    range.collapse(false);
    var sel = window.getSelection();
    if (sel) { sel.removeAllRanges(); sel.addRange(range); }
    return range;
  }

  function saveInputRange(input, store) {
    var sel = window.getSelection();
    if (!sel || !sel.rangeCount || !input.contains(sel.anchorNode)) return;
    store.range = sel.getRangeAt(0).cloneRange();
  }

  function resolveInsertRange(input, store) {
    var hadFocus = document.activeElement === input;
    input.focus();
    var sel = window.getSelection();
    if (!hadFocus && store.range && input.contains(store.range.startContainer)) {
      var restored = store.range.cloneRange();
      if (sel) { sel.removeAllRanges(); sel.addRange(restored); }
      return restored;
    }
    if (sel && sel.rangeCount && input.contains(sel.anchorNode)) {
      return sel.getRangeAt(0);
    }
    if (store.range && input.contains(store.range.startContainer)) {
      restored = store.range.cloneRange();
      if (sel) { sel.removeAllRanges(); sel.addRange(restored); }
      return restored;
    }
    return collapseToEnd(input);
  }

  function ensureZwsAfter(token) {
    var next = token.nextSibling;
    if (next && next.nodeType === 3) {
      if (next.textContent.charAt(0) !== ZWS) next.textContent = ZWS + next.textContent;
      return next;
    }
    var zws = document.createTextNode(ZWS);
    token.parentNode.insertBefore(zws, token.nextSibling);
    return zws;
  }

  function selectedSlotsInRange(range) {
    if (!range || range.collapsed) return 0;
    var tmp = document.createElement('div');
    tmp.appendChild(range.cloneContents());
    return slots(tmp);
  }

  function allowedInsertSlots(input, max, range) {
    var removed = range && !range.collapsed ? selectedSlotsInRange(range) : 0;
    return max - (slots(input) - removed);
  }

  function trimOverflow(input, max) {
    if (!input) return;
    var count = 0;
    var nodes = Array.prototype.slice.call(input.childNodes);
    for (var i = 0; i < nodes.length; i++) {
      var node = nodes[i];
      var nodeSlots = nodeSlotCost(node);
      if (count + nodeSlots > max) {
        if (node.nodeType === 3) node.textContent = node.textContent.slice(0, max - count);
        else node.remove();
        for (var j = i + 1; j < nodes.length; j++) nodes[j].remove();
        break;
      }
      count += nodeSlots;
    }
  }

  function updatePreview(input, previewEl) {
    if (!previewEl || !input) return;
    previewEl.innerHTML = '';
    input.childNodes.forEach(function (node) {
      previewEl.appendChild(node.cloneNode(true));
    });
  }

  function createToken(name) {
    var def = EMBLEMS[name];
    if (!def) return null;
    var token = document.createElement('span');
    token.className = 'cfg-emblem-token';
    token.setAttribute('contenteditable', 'false');
    token.setAttribute('data-emblem', name);
    token.setAttribute('data-label', def.label);
    token.setAttribute('tabindex', '-1');
    token.innerHTML = def.svg;
    return token;
  }

  function tokenBeforeCaret(input) {
    var sel = window.getSelection();
    if (!sel || !sel.rangeCount) return null;
    var range = sel.getRangeAt(0);
    var onToken = caretToken(input, range);
    if (onToken && range.collapsed) return onToken;
    if (!range.collapsed) return null;
    var node = range.startContainer;
    var offset = range.startOffset;
    if (node.nodeType === 3) {
      var plain = stripZws(node.textContent);
      if (offset > 0 && plain.length > 0) return null;
      if (offset > 0 && node.textContent.charAt(offset - 1) === ZWS) {
        var prevZws = node.previousSibling;
        return prevZws && prevZws.nodeType === 1 && prevZws.classList.contains('cfg-emblem-token') ? prevZws : null;
      }
      var prevText = node.previousSibling;
      return prevText && prevText.nodeType === 1 && prevText.classList.contains('cfg-emblem-token') ? prevText : null;
    }
    if (node === input && offset > 0) {
      var prev = node.childNodes[offset - 1];
      return prev && prev.nodeType === 1 && prev.classList.contains('cfg-emblem-token') ? prev : null;
    }
    return null;
  }

  function tokenAfterCaret(input) {
    var sel = window.getSelection();
    if (!sel || !sel.rangeCount) return null;
    var range = sel.getRangeAt(0);
    if (!range.collapsed) return null;
    var node = range.startContainer;
    var offset = range.startOffset;
    if (node.nodeType === 3) {
      var plainLen = stripZws(node.textContent).length;
      if (offset < plainLen) return null;
      var nextText = node.nextSibling;
      return nextText && nextText.nodeType === 1 && nextText.classList.contains('cfg-emblem-token') ? nextText : null;
    }
    if (node === input) {
      var next = node.childNodes[offset];
      return next && next.nodeType === 1 && next.classList.contains('cfg-emblem-token') ? next : null;
    }
    return null;
  }

  function selectedTokens(input) {
    var sel = window.getSelection();
    if (!sel || !sel.rangeCount) return [];
    var range = sel.getRangeAt(0);
    if (range.collapsed) return [];
    var found = [];
    input.querySelectorAll('.cfg-emblem-token').forEach(function (token) {
      if (range.intersectsNode(token)) found.push(token);
    });
    return found;
  }

  function deleteLastOrSelection(input, afterChange) {
    var sel = window.getSelection();
    if (sel && sel.rangeCount && input.contains(sel.anchorNode)) {
      var range = sel.getRangeAt(0);
      if (!range.collapsed) {
        range.deleteContents();
        afterChange();
        input.focus();
        return;
      }
    }
    var tokens = selectedTokens(input);
    if (tokens.length) {
      tokens.forEach(function (t) { removeToken(t); });
      afterChange();
      input.focus();
      return;
    }
    var token = tokenBeforeCaret(input);
    if (token) {
      removeToken(token);
      afterChange();
      input.focus();
      return;
    }
    var nodes = input.childNodes;
    if (!nodes.length) return;
    var last = nodes[nodes.length - 1];
    if (last.nodeType === 3) {
      if (last.textContent.length > 1) last.textContent = last.textContent.slice(0, -1);
      else last.remove();
    } else if (last.nodeType === 1 && last.classList.contains('cfg-emblem-token')) {
      removeToken(last);
    } else {
      last.remove();
    }
    afterChange();
    input.focus();
  }

  function ensureDeleteToolbar(input, countEl, afterChange) {
    if (!input || input.closest('.cfg-engrave-input-wrap')) return;
    var host = input.parentElement;
    if (!host) return;
    var wrap = document.createElement('div');
    wrap.className = 'cfg-engrave-input-wrap';
    host.insertBefore(wrap, input);
    wrap.appendChild(input);

    var meta = document.createElement('div');
    meta.className = 'cfg-engrave-input-meta';
    var actions = document.createElement('div');
    actions.className = 'cfg-engrave-input-actions';

    var deleteBtn = document.createElement('button');
    deleteBtn.type = 'button';
    deleteBtn.className = 'cfg-engrave-action cfg-engrave-action--delete';
    deleteBtn.textContent = '刪除';
    deleteBtn.setAttribute('aria-label', '刪除最後一個字或圖騰');

    var clearBtn = document.createElement('button');
    clearBtn.type = 'button';
    clearBtn.className = 'cfg-engrave-action cfg-engrave-action--clear';
    clearBtn.textContent = '清除';
    clearBtn.setAttribute('aria-label', '清除全部刻字內容');

    actions.appendChild(deleteBtn);
    actions.appendChild(clearBtn);
    meta.appendChild(actions);
    if (countEl && countEl.parentElement === host) {
      host.removeChild(countEl);
      meta.appendChild(countEl);
    }
    wrap.appendChild(meta);

    function syncActionState() {
      var empty = slots(input) === 0;
      deleteBtn.disabled = empty;
      clearBtn.disabled = empty;
    }

    deleteBtn.addEventListener('click', function () {
      deleteLastOrSelection(input, afterChange);
    });
    clearBtn.addEventListener('click', function () {
      input.innerHTML = '';
      afterChange();
      input.focus();
    });

    return syncActionState;
  }

  function insertEmblem(input, name, max, afterChange, store) {
    var token = createToken(name);
    if (!token || !input) return;

    var range = resolveInsertRange(input, store || {});
    if (allowedInsertSlots(input, max, range) < EMBLEM_SLOT_COST) return;

    range.deleteContents();
    range.insertNode(token);
    var zwsNode = ensureZwsAfter(token);
    var caretOffset = Math.min(zwsNode.textContent.length, 1);
    range.setStart(zwsNode, caretOffset);
    range.collapse(true);
    var sel = window.getSelection();
    if (sel) { sel.removeAllRanges(); sel.addRange(range); }
    if (store) saveInputRange(input, store);
    afterChange();
  }

  function setFromReadable(input, str, max, allowChinese, afterChange) {
    if (!input) return;
    input.innerHTML = '';
    if (!str) {
      afterChange();
      return;
    }
    var re = /〔([^〕]+)〕|[^〔〕]+/g;
    var match;
    while ((match = re.exec(str))) {
      if (match[0].charAt(0) === '〔') {
        var emblemName = LABEL_TO_NAME[match[1]];
        var token = emblemName ? createToken(emblemName) : null;
        if (token) {
          input.appendChild(token);
          ensureZwsAfter(token);
        }
      } else {
        var plain = sanitizePlainText(match[0], allowChinese);
        if (plain) input.appendChild(document.createTextNode(plain));
      }
    }
    trimOverflow(input, max);
    afterChange();
  }

  var GIRDLE_PREVIEW_BASE = '/static/images/shop/girdle-diamond-preview';
  var GIRDLE_MATRIX_BASE = '/static/images/diamonds/girdle-matrix';
  var GIRDLE_MATRIX_VERSION = '4';
  var GIRDLE_PREVIEW_BY_COLOR = {
    white: GIRDLE_PREVIEW_BASE + '-white.png',
    yellow: GIRDLE_PREVIEW_BASE + '-yellow.png',
    blue: GIRDLE_PREVIEW_BASE + '-blue.png',
    pink: GIRDLE_PREVIEW_BASE + '-pink.png'
  };

  function girdleMatrixSrc(shapeId, colorId) {
    var shape = shapeId || 'round';
    var color = colorId && GIRDLE_PREVIEW_BY_COLOR[colorId] ? colorId : 'white';
    return GIRDLE_MATRIX_BASE + '/' + shape + '-' + color + '.png?v=' + GIRDLE_MATRIX_VERSION;
  }

  function girdlePreviewSrc(colorId) {
    return GIRDLE_PREVIEW_BY_COLOR[colorId] || GIRDLE_PREVIEW_BY_COLOR.white;
  }

  function setGirdlePreview(previewEl, shapeId, colorId) {
    var wrap = previewEl && previewEl.parentElement;
    if (!wrap) return;
    var color = colorId && GIRDLE_PREVIEW_BY_COLOR[colorId] ? colorId : 'white';
    var shape = shapeId || 'round';
    wrap.setAttribute('data-girdle-color', color);
    wrap.setAttribute('data-girdle-shape', shape);
    var img = wrap.querySelector('img.cfg-engrave-gem');
    if (!img) return;
    var src = girdleMatrixSrc(shape, color);
    img.onerror = null;
    if (img.getAttribute('src') === src) {
      img.removeAttribute('src');
    }
    img.setAttribute('src', src);
  }

  function setGirdlePreviewColor(previewEl, colorId) {
    setGirdlePreview(previewEl, wrapShapeId(previewEl), colorId);
  }

  function wrapShapeId(previewEl) {
    var wrap = previewEl && previewEl.parentElement;
    return (wrap && wrap.getAttribute('data-girdle-shape')) || 'round';
  }

  function useRealGirdlePreview(previewEl, shapeId, colorId) {
    var wrap = previewEl && previewEl.parentElement;
    if (!wrap) return;
    var svg = wrap.querySelector('svg.cfg-engrave-gem');
    var img = wrap.querySelector('img.cfg-engrave-gem');
    if (!img) {
      img = document.createElement('img');
      img.className = 'cfg-engrave-gem';
      img.alt = '';
      img.width = 640;
      img.height = 360;
      img.loading = 'lazy';
      img.decoding = 'async';
      img.setAttribute('aria-hidden', 'true');
      if (svg) svg.replaceWith(img);
      else wrap.insertBefore(img, previewEl);
    }
    setGirdlePreview(previewEl, shapeId || 'round', colorId || 'white');
  }

  function init(opts) {
    var input = typeof opts.input === 'string' ? document.getElementById(opts.input) : opts.input;
    if (!input) return null;
    var max = opts.max || 12;
    var countEl = typeof opts.countEl === 'string' ? document.getElementById(opts.countEl) : opts.countEl;
    var previewEl = typeof opts.previewEl === 'string' ? document.getElementById(opts.previewEl) : opts.previewEl;
    var emblemsRoot = typeof opts.emblemsRoot === 'string' ? document.getElementById(opts.emblemsRoot) : opts.emblemsRoot;
    var previewColor = opts.previewColor || 'white';
    var previewShape = opts.previewShape || 'round';
    var allowChinese = !!opts.allowChinese;
    useRealGirdlePreview(previewEl, previewShape, previewColor);
    var lastValidHtml = input.innerHTML;
    var rangeStore = { range: null };

    function rememberValid() {
      lastValidHtml = input.innerHTML;
    }

    function restoreValid() {
      input.innerHTML = lastValidHtml;
      input.focus();
      var range = document.createRange();
      range.selectNodeContents(input);
      range.collapse(false);
      var sel = window.getSelection();
      if (sel) { sel.removeAllRanges(); sel.addRange(range); }
    }

    function afterChange() {
      sanitizeTextNodes(input, allowChinese);
      if (slots(input) > max) {
        restoreValid();
      } else {
        rememberValid();
      }
      trimOverflow(input, max);
      if (countEl) countEl.textContent = slots(input) + ' / ' + max;
      updatePreview(input, previewEl);
      if (typeof syncActionState === 'function') syncActionState();
      if (typeof opts.onChange === 'function') opts.onChange(readable(input));
    }

    function insertAllowedText(text) {
      var clean = sanitizePlainText(text, allowChinese);
      if (!clean) return;
      var sel = window.getSelection();
      var range = sel && sel.rangeCount && input.contains(sel.anchorNode)
        ? sel.getRangeAt(0)
        : resolveInsertRange(input, rangeStore);
      var room = allowedInsertSlots(input, max, range);
      if (room < 1) return;
      if (clean.length > room) clean = clean.slice(0, room);
      range.deleteContents();
      var textNode = document.createTextNode(clean);
      range.insertNode(textNode);
      range.setStart(textNode, textNode.textContent.length);
      range.collapse(true);
      if (sel) { sel.removeAllRanges(); sel.addRange(range); }
      saveInputRange(input, rangeStore);
      afterChange();
    }

    function blockIfFull(e, addSlots) {
      var sel = window.getSelection();
      if (!sel || !sel.rangeCount || !input.contains(sel.anchorNode)) return;
      var range = sel.getRangeAt(0);
      if (allowedInsertSlots(input, max, range) < addSlots) e.preventDefault();
    }

    var syncActionState = opts.deleteButtons !== false
      ? ensureDeleteToolbar(input, countEl, afterChange)
      : null;

    var composing = false;
    input.addEventListener('keyup', function () { saveInputRange(input, rangeStore); });
    input.addEventListener('mouseup', function () { saveInputRange(input, rangeStore); });
    document.addEventListener('selectionchange', function () {
      if (document.activeElement === input) saveInputRange(input, rangeStore);
    });

    input.addEventListener('compositionstart', function () { composing = true; });
    input.addEventListener('compositionend', function () {
      composing = false;
      afterChange();
    });

    input.addEventListener('beforeinput', function (e) {
      if (composing || e.isComposing) return;
      if (e.inputType && e.inputType.indexOf('delete') === 0) {
        var sel = window.getSelection();
        if (!sel || !sel.rangeCount || !input.contains(sel.anchorNode)) return;
        var range = sel.getRangeAt(0);
        var tokens = selectedTokens(input);
        if (tokens.length) {
          e.preventDefault();
          tokens.forEach(function (t) { removeToken(t); });
          afterChange();
          return;
        }
        var token = e.inputType === 'deleteContentForward'
          ? tokenAfterCaret(input)
          : (caretToken(input, range) || tokenBeforeCaret(input));
        if (token) {
          e.preventDefault();
          removeToken(token);
          afterChange();
        }
        return;
      }
      if (e.inputType === 'historyUndo' || e.inputType === 'historyRedo') return;
      // IME (Chinese) composition commit — some browsers fire this beforeinput
      // after isComposing has already flipped back to false. Let it through as-is;
      // compositionend -> afterChange() sanitizes/trims it right after.
      if (e.inputType === 'insertFromComposition' || e.inputType === 'insertCompositionText') return;
      if (e.inputType === 'insertText' || e.inputType === 'insertReplacementText') {
        var raw = e.data || '';
        var clean = sanitizePlainText(raw, allowChinese);
        if (!clean || clean !== raw) {
          e.preventDefault();
          if (clean) insertAllowedText(clean);
          return;
        }
        blockIfFull(e, clean.length || 1);
        return;
      }
      if (e.inputType === 'insertFromPaste' || e.inputType === 'insertFromDrop') {
        e.preventDefault();
        return;
      }
      // Block other insert types (HTML, line break, etc.)
      if (e.inputType && e.inputType.indexOf('insert') === 0) {
        e.preventDefault();
      }
    });

    input.addEventListener('input', afterChange);

    input.addEventListener('keydown', function (e) {
      if (e.key === 'Backspace' || e.key === 'Delete') {
        var sel = window.getSelection();
        var range = sel && sel.rangeCount ? sel.getRangeAt(0) : null;
        var tokens = selectedTokens(input);
        if (tokens.length) {
          e.preventDefault();
          tokens.forEach(function (t) { removeToken(t); });
          afterChange();
          return;
        }
        var token = e.key === 'Backspace'
          ? (range && caretToken(input, range)) || tokenBeforeCaret(input)
          : tokenAfterCaret(input);
        if (token) {
          e.preventDefault();
          removeToken(token);
          afterChange();
        }
        return;
      }
      if (e.ctrlKey || e.metaKey || e.altKey) return;
      if (e.key.length !== 1) return;
      if (!allowedCharRe(allowChinese).test(e.key)) {
        e.preventDefault();
        return;
      }
      var selKey = window.getSelection();
      if (selKey && selKey.rangeCount && input.contains(selKey.anchorNode)) {
        var rangeKey = selKey.getRangeAt(0);
        var onToken = caretToken(input, rangeKey);
        if (onToken) {
          e.preventDefault();
          var zws = ensureZwsAfter(onToken);
          placeCaretIn(input, zws, zws.textContent.length);
          insertAllowedText(e.key);
          return;
        }
      }
      blockIfFull(e, 1);
    });

    input.addEventListener('paste', function (e) {
      e.preventDefault();
      var text = (e.clipboardData && e.clipboardData.getData('text')) || '';
      insertAllowedText(text);
    });

    input.addEventListener('click', function (e) {
      var token = e.target.closest('.cfg-emblem-token');
      if (!token || !input.contains(token)) return;
      var zws = ensureZwsAfter(token);
      placeCaretIn(input, zws, zws.textContent.length);
    });

    if (emblemsRoot) {
      emblemsRoot.addEventListener('mousedown', function (e) {
        var btn = e.target.closest('.cfg-emblem');
        if (!btn || !emblemsRoot.contains(btn)) return;
        e.preventDefault();
      });
      emblemsRoot.addEventListener('click', function (e) {
        var btn = e.target.closest('.cfg-emblem');
        if (!btn || !emblemsRoot.contains(btn)) return;
        e.preventDefault();
        insertEmblem(input, btn.getAttribute('data-emblem'), max, afterChange, rangeStore);
      });
    }

    afterChange();

    return {
      readable: function () { return readable(input); },
      setValue: function (str) { setFromReadable(input, str || '', max, allowChinese, afterChange); },
      setPreviewColor: function (colorId) {
        setGirdlePreview(previewEl, wrapShapeId(previewEl), colorId);
      },
      setPreviewShapeAndColor: function (shapeId, colorId) {
        setGirdlePreview(previewEl, shapeId || 'round', colorId || 'white');
      },
      setAllowChinese: function (flag) {
        flag = !!flag;
        if (flag === allowChinese) return;
        allowChinese = flag;
        if (!allowChinese) {
          // Downgrading (carat dropped below threshold) — strip any Chinese
          // already typed instead of silently keeping now-disallowed content.
          sanitizeTextNodes(input, false);
          afterChange();
        }
      },
      focus: function () { input.focus(); }
    };
  }

  window.GirdleEngrave = {
    EMBLEMS: EMBLEMS,
    EMBLEM_LABELS: Object.keys(LABEL_TO_NAME).reduce(function (acc, label) { acc[label] = true; return acc; }, {}),
    PREVIEW_BY_COLOR: GIRDLE_PREVIEW_BY_COLOR,
    matrixSrc: girdleMatrixSrc,
    previewSrc: girdlePreviewSrc,
    init: init,
    readable: readable,
    toDisplayHtml: toDisplayHtml,
    fillDisplay: fillDisplay,
    slots: slots
  };
})();
