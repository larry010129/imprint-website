/* Freeform drag/resize + snap + keyboard nudge (Next preview document). */
(function () {
  'use strict';
  var root = document.querySelector('[data-cms-inline]');
  if (!root || window.parent === window) return;

  var SNAP = 2; // percent
  var NUDGE = 1;
  var active = null;
  var selectedBlocks = [];

  function post(payload) {
    var target = document.documentElement.getAttribute('data-cms-parent-origin') || '*';
    window.parent.postMessage(
      Object.assign({ source: 'cms-inline' }, payload),
      target
    );
  }

  function clamp(n, lo, hi) {
    return Math.max(lo, Math.min(hi, n));
  }

  function round2(n) {
    return Math.round(n * 100) / 100;
  }

  function snap(n) {
    return round2(Math.round(n / SNAP) * SNAP);
  }

  function deviceMode() {
    return document.documentElement.getAttribute('data-cms-device') || 'desktop';
  }

  function sectionOf(el) {
    return el && el.closest
      ? el.closest('[data-cms-section-type="freeform"][data-cms-section-id]')
      : null;
  }

  function activeLayer(section) {
    var mode = deviceMode();
    var layer = section.querySelector(
      '[data-cms-freeform-layer="' + (mode === 'mobile' ? 'mobile' : 'desktop') + '"]'
    );
    if (layer && layer.offsetParent !== null) return layer;
    return (
      section.querySelector('[data-cms-freeform-layer="desktop"]') ||
      section.querySelector('[data-cms-freeform-canvas]')
    );
  }

  function readLayout(section) {
    var layer = activeLayer(section);
    if (!layer) return [];
    var blocks = [];
    layer.querySelectorAll('[data-cms-freeform-block]').forEach(function (node, index) {
      var id = node.getAttribute('data-cms-freeform-block');
      var kind = node.getAttribute('data-cms-block-kind') || 'text';
      var style = node.style;
      var block = {
        id: id,
        kind: kind,
        x: parseFloat(style.left) || 0,
        y: parseFloat(style.top) || 0,
        w: parseFloat(style.width) || 30,
        h: parseFloat(style.minHeight) || 12,
        z: parseInt(style.zIndex, 10) || index + 1
      };
      var textEl = node.querySelector('[data-cms-block-field="text"]');
      if (textEl) block.text = (textEl.textContent || '').trim();
      if (kind === 'button' && textEl && textEl.tagName === 'A') {
        block.href = textEl.getAttribute('href') || '';
      }
      if (kind === 'image') {
        var img = node.querySelector('img');
        if (img) {
          block.image_url = img.getAttribute('src') || '';
          block.image_alt = img.getAttribute('alt') || '';
        } else {
          block.image_url = '';
          block.image_alt = '';
        }
      }
      blocks.push(block);
    });
    return blocks;
  }

  function applyBox(node, box) {
    node.style.left = box.x + '%';
    node.style.top = box.y + '%';
    node.style.width = box.w + '%';
    node.style.minHeight = box.h + '%';
  }

  function clearGuides(section) {
    var g = section.querySelector('[data-cms-freeform-guides]');
    if (g) g.remove();
  }

  function showGuides(section, xLines, yLines) {
    clearGuides(section);
    var canvas = section.querySelector('[data-cms-freeform-canvas]');
    if (!canvas) return;
    var wrap = document.createElement('div');
    wrap.setAttribute('data-cms-freeform-guides', '1');
    wrap.style.cssText =
      'position:absolute;inset:0;pointer-events:none;z-index:999;';
    xLines.forEach(function (x) {
      var line = document.createElement('div');
      line.style.cssText =
        'position:absolute;top:0;bottom:0;width:1px;background:#2563eb;left:' +
        x +
        '%;opacity:.7';
      wrap.appendChild(line);
    });
    yLines.forEach(function (y) {
      var line = document.createElement('div');
      line.style.cssText =
        'position:absolute;left:0;right:0;height:1px;background:#2563eb;top:' +
        y +
        '%;opacity:.7';
      wrap.appendChild(line);
    });
    canvas.appendChild(wrap);
  }

  function selectBlock(node, multi) {
    if (!multi) {
      selectedBlocks.forEach(function (n) {
        if (n.isConnected) n.classList.remove('is-freeform-selected');
      });
      selectedBlocks = [];
    }
    if (!node) return;
    if (selectedBlocks.indexOf(node) === -1) selectedBlocks.push(node);
    node.classList.add('is-freeform-selected');
  }

  function commitLayout(section) {
    var sectionId = section.getAttribute('data-cms-section-id');
    if (!sectionId) return;
    post({
      type: 'block-layout',
      sectionId: sectionId,
      blocks: readLayout(section),
      device: deviceMode()
    });
  }

  function endGesture(commit) {
    if (!active) return;
    var section = active.section;
    section.classList.remove('is-freeform-dragging');
    clearGuides(section);
    if (commit) commitLayout(section);
    active = null;
  }

  function onPointerMove(event) {
    if (!active) return;
    event.preventDefault();
    var rect = active.canvasRect;
    if (!rect.width || !rect.height) return;
    var dx = ((event.clientX - active.startX) / rect.width) * 100;
    var dy = ((event.clientY - active.startY) / rect.height) * 100;
    var next;
    if (active.mode === 'drag') {
      next = {
        x: snap(clamp(active.origin.x + dx, 0, 95)),
        y: snap(clamp(active.origin.y + dy, 0, 95)),
        w: active.origin.w,
        h: active.origin.h
      };
      applyBox(active.node, next);
      showGuides(active.section, [next.x, next.x + next.w], [next.y, next.y + next.h]);
      return;
    }
    next = {
      x: active.origin.x,
      y: active.origin.y,
      w: snap(clamp(active.origin.w + dx, 8, 100)),
      h: snap(clamp(active.origin.h + dy, 6, 100))
    };
    applyBox(active.node, next);
    showGuides(active.section, [next.x + next.w], [next.y + next.h]);
  }

  function onPointerUp() {
    endGesture(true);
  }

  function startGesture(event, mode) {
    var handle = event.currentTarget;
    var node = handle.closest('[data-cms-freeform-block]');
    var section = sectionOf(node);
    if (!node || !section) return;
    var canvas = section.querySelector('[data-cms-freeform-canvas]');
    if (!canvas) return;
    event.preventDefault();
    event.stopPropagation();
    selectBlock(node, event.shiftKey);
    post({
      type: 'select-section',
      sectionId: section.getAttribute('data-cms-section-id')
    });
    active = {
      mode: mode,
      node: node,
      section: section,
      canvasRect: canvas.getBoundingClientRect(),
      startX: event.clientX,
      startY: event.clientY,
      origin: {
        x: parseFloat(node.style.left) || 0,
        y: parseFloat(node.style.top) || 0,
        w: parseFloat(node.style.width) || 30,
        h: parseFloat(node.style.minHeight) || 12
      }
    };
    section.classList.add('is-freeform-dragging');
  }

  function alignSelected(axis) {
    if (selectedBlocks.length < 2) return;
    var section = sectionOf(selectedBlocks[0]);
    if (!section) return;
    var boxes = selectedBlocks.map(function (n) {
      return {
        node: n,
        x: parseFloat(n.style.left) || 0,
        y: parseFloat(n.style.top) || 0,
        w: parseFloat(n.style.width) || 30,
        h: parseFloat(n.style.minHeight) || 12
      };
    });
    if (axis === 'left') {
      var minX = Math.min.apply(
        null,
        boxes.map(function (b) {
          return b.x;
        })
      );
      boxes.forEach(function (b) {
        applyBox(b.node, { x: minX, y: b.y, w: b.w, h: b.h });
      });
    } else if (axis === 'top') {
      var minY = Math.min.apply(
        null,
        boxes.map(function (b) {
          return b.y;
        })
      );
      boxes.forEach(function (b) {
        applyBox(b.node, { x: b.x, y: minY, w: b.w, h: b.h });
      });
    } else if (axis === 'center-x') {
      var cx =
        boxes.reduce(function (s, b) {
          return s + b.x + b.w / 2;
        }, 0) / boxes.length;
      boxes.forEach(function (b) {
        applyBox(b.node, {
          x: round2(clamp(cx - b.w / 2, 0, 95)),
          y: b.y,
          w: b.w,
          h: b.h
        });
      });
    }
    commitLayout(section);
  }

  function wireBlock(node) {
    if (!node || node.getAttribute('data-freeform-wired') === '1') return;
    node.setAttribute('data-freeform-wired', '1');
    var drag = node.querySelector('[data-cms-freeform-drag]');
    var resize = node.querySelector('[data-cms-freeform-resize]');
    if (drag) {
      drag.addEventListener('pointerdown', function (event) {
        startGesture(event, 'drag');
      });
    }
    if (resize) {
      resize.addEventListener('pointerdown', function (event) {
        startGesture(event, 'resize');
      });
    }
    node.addEventListener('mousedown', function (event) {
      if (event.target.closest('[data-cms-freeform-drag], [data-cms-freeform-resize]'))
        return;
      selectBlock(node, event.shiftKey);
    });
  }

  function wireAll() {
    root.querySelectorAll('[data-cms-freeform-block]').forEach(wireBlock);
  }

  document.addEventListener('pointermove', onPointerMove, { passive: false });
  document.addEventListener('pointerup', onPointerUp);
  document.addEventListener('pointercancel', onPointerUp);

  document.addEventListener('keydown', function (event) {
    if (!selectedBlocks.length) return;
    var tag = (event.target && event.target.tagName) || '';
    if (tag === 'INPUT' || tag === 'TEXTAREA' || event.target.isContentEditable) return;
    var dx = 0;
    var dy = 0;
    if (event.key === 'ArrowLeft') dx = -NUDGE;
    else if (event.key === 'ArrowRight') dx = NUDGE;
    else if (event.key === 'ArrowUp') dy = -NUDGE;
    else if (event.key === 'ArrowDown') dy = NUDGE;
    else if (event.key === 'a' && event.altKey) {
      event.preventDefault();
      alignSelected('left');
      return;
    } else if (event.key === 't' && event.altKey) {
      event.preventDefault();
      alignSelected('top');
      return;
    } else if (event.key === 'c' && event.altKey) {
      event.preventDefault();
      alignSelected('center-x');
      return;
    } else return;
    event.preventDefault();
    var section = sectionOf(selectedBlocks[0]);
    selectedBlocks.forEach(function (node) {
      var box = {
        x: clamp((parseFloat(node.style.left) || 0) + dx, 0, 95),
        y: clamp((parseFloat(node.style.top) || 0) + dy, 0, 95),
        w: parseFloat(node.style.width) || 30,
        h: parseFloat(node.style.minHeight) || 12
      };
      applyBox(node, box);
    });
    if (section) commitLayout(section);
  });

  window.addEventListener('message', function (event) {
    var data = event.data;
    if (!data || data.source !== 'cms-editor') return;
    if (data.type === 'set-device' && (data.device === 'mobile' || data.device === 'desktop')) {
      document.documentElement.setAttribute('data-cms-device', data.device);
    }
    if (data.type === 'align-blocks' && data.axis) {
      alignSelected(String(data.axis));
    }
  });

  wireAll();
  var observer = new MutationObserver(function () {
    wireAll();
  });
  observer.observe(root, { childList: true, subtree: true });
})();
