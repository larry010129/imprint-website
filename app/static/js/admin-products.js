/* 銘印鑽石｜商品上架管理 */
(function () {
  'use strict';

  var api = window.imprintAPI;
  if (!api || !api.admin) return;

  var CATEGORY_ORDER = ['pendant', 'ring', 'earring', 'bracelet', 'chain'];
  var GOLDS = ['9k', '14k', '18k', 'pt950', 's925'];
  var CARATS = ['0.1', '0.2', '0.3', '0.5', '1.0'];
  var CHAIN_CARATS = ['3fen', '4fen'];
  var COLORS = ['white', 'yellow', 'rose'];
  var GOLD_LABELS = { '9k': '9K', '14k': '14K', '18k': '18K', 'pt950': 'PT950', 's925': 'S925' };
  var COLOR_LABELS = { white: '白金', yellow: '黃金', rose: '玫瑰金' };
  var IMAGE_SLOT_OPTIONS = [
    { value: 'white', label: '金屬 · 白金', group: 'metal' },
    { value: 'yellow', label: '金屬 · 黃金', group: 'metal' },
    { value: 'rose', label: '金屬 · 玫瑰金', group: 'metal' },
    { value: 'diamond-d', label: '鑽石 · D 色', group: 'diamond' },
    { value: 'diamond-e', label: '鑽石 · E 色', group: 'diamond' },
    { value: 'diamond-f', label: '鑽石 · F 色', group: 'diamond' },
    { value: 'diamond-g', label: '鑽石 · G 色', group: 'diamond' },
    { value: 'diamond-h', label: '鑽石 · H 色', group: 'diamond' },
    { value: '__custom__', label: '其他（自訂）', group: 'other' },
  ];
  var IMAGE_SLOT_PRESET_VALUES = IMAGE_SLOT_OPTIONS
    .filter(function (o) { return o.value !== '__custom__'; })
    .map(function (o) { return o.value; });

  var root = document.getElementById('productsRoot');
  if (!root) return;

  var state = { products: [], categoryLabels: {}, activeTab: 'cat-pendant', editingId: null, view: 'list' };
  var _loaded = false;
  var _slotCounter = 0;

  function esc(s) {
    return window.AdminPanel && window.AdminPanel.escapeHtml
      ? window.AdminPanel.escapeHtml(s)
      : String(s == null ? '' : s);
  }

  function imageUrl(path, color) {
    if (window.AdminImageUrls && window.AdminImageUrls.productPhoto) {
      return window.AdminImageUrls.productPhoto(path, color);
    }
    return window.AdminImageUrls ? window.AdminImageUrls.resolve(path) : path;
  }

  function productThumb(product) {
    var images = product.images || [];
    var def = product.default_color || 'white';
    var match = images.find(function (img) { return img.color === def; }) || images[0];
    if (match) return imageUrl(match.file_path, def);
    return window.AdminImageUrls
      ? window.AdminImageUrls.categoryFallback(product.category)
      : '';
  }

  function productStatus(product) {
    if (product.is_published) return { label: '已上架', cls: 'ap-status-badge--live' };
    if (product.first_published_at) return { label: '已下架', cls: 'ap-status-badge--offline' };
    return { label: '草稿', cls: 'ap-status-badge--draft' };
  }

  function publishReady(product) {
    var variants = product.variants || [];
    var images = product.images || [];
    if (!variants.length) return { ok: false, reason: '請先新增至少一個款式選項' };
    if (!images.length) return { ok: false, reason: '請先上傳至少一張商品照片' };
    var def = product.default_color || 'white';
    if (!images.some(function (img) { return img.color === def; })) {
      return { ok: false, reason: '預設顏色必須至少有一張商品照片' };
    }
    return { ok: true, reason: '' };
  }

  function previewUrl(product) {
    return '/shop/calculator/?preview=1&category=' + encodeURIComponent(product.category)
      + '&product=' + encodeURIComponent(product.id);
  }

  function caratsFor(category) {
    return category === 'chain' ? CHAIN_CARATS : CARATS;
  }

  function productsInCategory(cat) {
    return state.products.filter(function (p) { return p.category === cat; });
  }

  function setRoot(html, bindList) {
    root.innerHTML = html;
    if (bindList !== false) bindRootEvents();
  }

  function renderShell() {
    state.view = 'list';
    var tabs = CATEGORY_ORDER.map(function (cat, i) {
      var label = state.categoryLabels[cat] || cat;
      var count = productsInCategory(cat).length;
      var active = state.activeTab === 'cat-' + cat;
      return '<button type="button" class="ap-tab-btn' + (active ? ' is-active' : '') + '" data-tab="cat-' + cat + '" role="tab" aria-selected="' + (active ? 'true' : 'false') + '">' +
        esc(label) + '<span class="ap-tab-count">' + count + '</span></button>';
    }).join('');

    var panels = CATEGORY_ORDER.map(function (cat) {
      var rows = productsInCategory(cat);
      var body = rows.length
        ? rows.map(function (p) { return renderRow(p); }).join('')
        : '<tr><td colspan="6" class="ap-empty">此品項尚無商品。</td></tr>';
      var hidden = state.activeTab !== 'cat-' + cat ? ' hidden' : '';
      return '<div class="ap-tab-panel" data-tab-panel="cat-' + cat + '"' + hidden + '>' +
        '<table class="ap-table"><thead><tr>' +
        '<th data-sortable="false" aria-label="排序"></th>' +
        '<th data-sortable="false">縮圖</th>' +
        '<th data-sort-key="category" data-sortable="text">品項</th>' +
        '<th data-sort-key="name" data-sortable="text">名稱</th>' +
        '<th data-sort-key="status" data-sortable="text">狀態</th>' +
        '<th data-sortable="false">操作</th>' +
        '</tr></thead><tbody data-category="' + cat + '">' + body + '</tbody></table></div>';
    }).join('');

    setRoot(
      '<p class="note">管理商品款式、金屬選項與照片。上架後會顯示於客製試算頁；拖曳列可調整排序。</p>' +
      '<div class="ap-toolbar"><button type="button" class="btn-sm btn-primary" id="btnNewProduct">+ 新增商品</button></div>' +
      '<div class="ap-category-tabs" role="tablist">' + tabs + '</div>' +
      panels +
      '<dialog id="apDeleteDialog" class="ap-delete-dialog"><form method="dialog" id="apDeleteForm">' +
        '<h3>刪除商品</h3><p id="apDeleteTarget"></p>' +
        '<p class="ap-hint">刪除後無法復原，若已有訂單引用建議改為下架。</p>' +
        '<div class="ap-delete-actions">' +
          '<button type="button" class="btn-sm" id="apDeleteCancel">取消</button>' +
          '<button type="submit" class="btn-sm btn-primary">確認刪除</button>' +
        '</div></form></dialog>'
    );
    if (window.AdminTableSort) {
      root.querySelectorAll('.ap-table').forEach(function (t) { window.AdminTableSort.bind(t); });
    }
  }

  function renderRow(product) {
    var thumb = productThumb(product);
    var status = productStatus(product);
    var ready = publishReady(product);
    var catLabel = state.categoryLabels[product.category] || product.category;
    var thumbHtml = thumb
      ? '<img class="ap-thumb" src="' + esc(thumb) + '" alt="" data-fallback="' + esc(window.AdminImageUrls ? window.AdminImageUrls.categoryFallback(product.category) : '') + '">'
      : '<span class="ap-thumb ap-thumb--empty">-</span>';
    var publishBtn = product.is_published
      ? '<button type="button" class="btn-sm ap-action" data-action="unpublish" data-id="' + esc(product.id) + '">下架</button>'
      : '<button type="button" class="btn-sm ap-action' + (ready.ok ? ' btn-primary' : '') + '" data-action="publish" data-id="' + esc(product.id) + '"' +
        (ready.ok ? '' : ' disabled title="' + esc(ready.reason) + '"') + '>上架</button>';

    return '<tr data-id="' + esc(product.id) + '" data-category="' + esc(product.category) + '" draggable="true"' +
      ' data-sort-category="' + esc(catLabel) + '" data-sort-name="' + esc(product.name_zh) + '" data-sort-status="' + esc(status.label) + '">' +
      '<td><button type="button" class="ap-drag-handle" aria-label="拖曳排序">⋮⋮</button></td>' +
      '<td>' + thumbHtml + '</td>' +
      '<td>' + esc(catLabel) + '</td>' +
      '<td><span class="name">' + esc(product.name_zh) + '</span>' +
        (product.name_en ? '<span class="sub">' + esc(product.name_en) + '</span>' : '') + '</td>' +
      '<td><span class="ap-status-badge ' + status.cls + '">' + status.label + '</span></td>' +
      '<td class="ap-actions">' +
        '<button type="button" class="btn-sm ap-action" data-action="edit" data-id="' + esc(product.id) + '">編輯</button>' +
        '<a class="btn-sm ap-action" href="' + esc(previewUrl(product)) + '" target="_blank" rel="noopener">預覽</a>' +
        publishBtn +
        '<button type="button" class="btn-sm ap-action" data-action="duplicate" data-id="' + esc(product.id) + '">複製</button>' +
        '<button type="button" class="btn-sm ap-action ap-action--danger" data-action="delete" data-id="' + esc(product.id) + '" data-name="' + esc(product.name_zh) + '">刪除</button>' +
      '</td></tr>';
  }

  function bindRootEvents() {
    root.querySelectorAll('.ap-tab-btn').forEach(function (btn) {
      btn.addEventListener('click', function () {
        state.activeTab = btn.dataset.tab;
        renderShell();
      });
    });

    var newBtn = document.getElementById('btnNewProduct');
    if (newBtn) {
      newBtn.addEventListener('click', function () {
        var cat = state.activeTab.replace('cat-', '');
        openEditor(null, cat);
      });
    }

    root.querySelectorAll('[data-action]').forEach(function (btn) {
      btn.addEventListener('click', function () {
        var action = btn.dataset.action;
        var id = btn.dataset.id;
        if (action === 'edit') {
          var product = state.products.find(function (p) { return p.id === id; });
          if (product) openEditor(product);
          return;
        }
        if (action === 'delete') {
          openDeleteDialog(id, btn.dataset.name);
          return;
        }
        runAction(id, action);
      });
    });

    bindDragReorder();
    bindDeleteDialog();
  }

  var deleteId = null;
  function bindDeleteDialog() {
    var dialog = document.getElementById('apDeleteDialog');
    var cancel = document.getElementById('apDeleteCancel');
    var form = document.getElementById('apDeleteForm');
    if (!dialog || !form) return;
    cancel && cancel.addEventListener('click', function () { dialog.close(); });
    form.addEventListener('submit', function (e) {
      e.preventDefault();
      if (!deleteId) return;
      runAction(deleteId, 'delete').then(function () {
        dialog.close();
        deleteId = null;
      });
    });
  }

  function openDeleteDialog(id, name) {
    deleteId = id;
    var target = document.getElementById('apDeleteTarget');
    if (target) target.textContent = '即將刪除：' + (name || id);
    document.getElementById('apDeleteDialog')?.showModal();
  }

  function bindDragReorder() {
    var dragged = null;
    root.querySelectorAll('.ap-table tbody').forEach(function (tbody) {
      tbody.querySelectorAll('tr[data-id]').forEach(function (row) {
        row.addEventListener('dragstart', function () {
          dragged = row;
          row.classList.add('is-dragging');
        });
        row.addEventListener('dragend', function () {
          row.classList.remove('is-dragging');
          dragged = null;
          var ids = [...tbody.querySelectorAll('tr[data-id]')].map(function (r) { return r.dataset.id; });
          if (!ids.length) return;
          api.admin.reorderProducts(ids).then(function (res) {
            if (res.error) {
              alert('排序失敗：' + res.error);
              load(true, true);
            }
          });
        });
        row.addEventListener('dragover', function (e) {
          e.preventDefault();
          if (!dragged || dragged === row) return;
          var box = row.getBoundingClientRect();
          tbody.insertBefore(dragged, e.clientY < box.top + box.height / 2 ? row : row.nextSibling);
        });
      });
    });
  }

  function runAction(id, action) {
    return api.admin.productAction(id, action).then(function (res) {
      if (res.error) {
        alert(res.error.message || res.error);
        return;
      }
      load(true, true);
    });
  }

  function variantRowHtml(variant, category) {
    var carats = caratsFor(category);
    var goldOpts = GOLDS.map(function (g) {
      var sel = variant && variant.gold === g ? ' selected' : '';
      return '<option value="' + g + '"' + sel + '>' + (GOLD_LABELS[g] || g) + '</option>';
    }).join('');
    var caratOpts = carats.map(function (c) {
      var sel = variant && String(variant.carat) === c ? ' selected' : '';
      return '<option value="' + c + '"' + sel + '>' + c + '</option>';
    }).join('');
    var weight = variant ? variant.weight_chin : '';
    var price = variant && variant.manual_price_twd != null ? variant.manual_price_twd : '';
    return '<div class="ap-variant-row">' +
      '<select name="gold">' + goldOpts + '</select>' +
      '<select name="carat">' + caratOpts + '</select>' +
      '<input type="number" name="weight" step="0.0001" min="0.0001" placeholder="金重（錢）" value="' + esc(weight) + '">' +
      '<input type="number" name="price" step="1" min="0" placeholder="手動定價" value="' + esc(price) + '">' +
      '<button type="button" class="ap-remove-row" aria-label="移除">✕</button></div>';
  }

  function imageSlideHtml(url, color) {
    var src = imageUrl(url, color);
    return (
      '<div class="ap-carousel-item" data-url="' + esc(url) + '">' +
        '<div class="ap-carousel-card">' +
          '<div class="ap-carousel-card-media">' +
            '<img class="ap-carousel-img" src="' + esc(src) + '" alt="" data-fallback="' + esc(src) + '">' +
            '<button type="button" class="ap-remove-image" aria-label="移除">✕</button>' +
          '</div>' +
        '</div>' +
      '</div>'
    );
  }

  function slotKeySelectHtml(selected, usedKeys) {
    var used = usedKeys || {};
    return IMAGE_SLOT_OPTIONS.map(function (opt) {
      var taken = opt.value !== '__custom__' && opt.value !== selected && used[opt.value];
      var sel = (opt.value === selected || (selected && opt.value === '__custom__' && IMAGE_SLOT_PRESET_VALUES.indexOf(selected) < 0)) ? ' selected' : '';
      return '<option value="' + opt.value + '"' + sel + (taken ? ' disabled' : '') + '>' + esc(opt.label) + '</option>';
    }).join('');
  }

  function groupImagesForSlots(images) {
    var groups = {};
    (images || []).forEach(function (img) {
      var color = img.color || 'white';
      if (!groups[color]) groups[color] = [];
      groups[color].push(img.file_path || img.url);
    });
    var keys = Object.keys(groups);
    if (!keys.length) return [{ color: 'white', urls: [] }];
    return keys.map(function (color) {
      return { color: color, urls: groups[color] };
    });
  }

  function imageSlotHtml(slot, usedKeys) {
    var slotId = 'slot-' + (++_slotCounter);
    var color = slot.color || 'white';
    var isCustom = IMAGE_SLOT_PRESET_VALUES.indexOf(color) < 0;
    var selectValue = isCustom ? '__custom__' : color;
    var slides = (slot.urls || []).map(function (url) {
      return imageSlideHtml(url, color);
    }).join('');
    var used = Object.assign({}, usedKeys || {});
    if (!isCustom) used[color] = true;

    return (
      '<div class="ap-image-slot" data-slot-id="' + slotId + '">' +
        '<div class="ap-image-slot-head">' +
          '<label class="ap-image-slot-label">' +
            '<span>圖片選項</span>' +
            '<select class="ap-image-slot-key">' + slotKeySelectHtml(selectValue, used) + '</select>' +
          '</label>' +
          '<input type="text" class="ap-image-slot-custom" maxlength="32" placeholder="自訂代碼（例：side-view）" value="' +
            esc(isCustom ? color : '') + '"' + (isCustom ? '' : ' hidden') + '>' +
          '<button type="button" class="ap-remove-slot" aria-label="移除此選項">✕</button>' +
        '</div>' +
        '<div class="ap-carousel" data-carousel>' +
          '<button type="button" class="ap-carousel-btn ap-carousel-prev" aria-label="上一張" disabled>' +
            '<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><path d="M15 18l-6-6 6-6"/></svg>' +
          '</button>' +
          '<div class="ap-carousel-viewport">' +
            '<div class="ap-carousel-track">' +
              slides +
              '<div class="ap-carousel-item ap-carousel-item--upload">' +
                '<div class="ap-carousel-card ap-carousel-card--upload">' +
                  '<label class="ap-image-upload-btn">' +
                    '<span class="ap-upload-plus">+</span>' +
                    '<span>上傳圖片</span>' +
                    '<input type="file" class="ap-image-input" accept="image/png,image/jpeg,image/webp" multiple hidden>' +
                  '</label>' +
                  '<span class="ap-uploading" hidden>上傳中…</span>' +
                '</div>' +
              '</div>' +
            '</div>' +
          '</div>' +
          '<button type="button" class="ap-carousel-btn ap-carousel-next" aria-label="下一張">' +
            '<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><path d="M9 18l6-6-6-6"/></svg>' +
          '</button>' +
        '</div>' +
      '</div>'
    );
  }

  function imageSlotsHtml(images) {
    var slots = groupImagesForSlots(images);
    var used = {};
    return slots.map(function (slot, i) {
      var html = imageSlotHtml(slot, used);
      if (IMAGE_SLOT_PRESET_VALUES.indexOf(slot.color) >= 0) used[slot.color] = true;
      return html;
    }).join('');
  }

  function initCarousel(carousel) {
    if (carousel.dataset.carouselBound) return;
    carousel.dataset.carouselBound = '1';
    var viewport = carousel.querySelector('.ap-carousel-viewport');
    var track = carousel.querySelector('.ap-carousel-track');
    var prev = carousel.querySelector('.ap-carousel-prev');
    var next = carousel.querySelector('.ap-carousel-next');
    if (!viewport || !track || !prev || !next) return;

    function updateButtons() {
      var maxScroll = track.scrollWidth - viewport.clientWidth;
      prev.disabled = viewport.scrollLeft <= 1;
      next.disabled = viewport.scrollLeft >= maxScroll - 1;
    }

    function scrollByItem(dir) {
      var item = track.querySelector('.ap-carousel-item');
      var gap = 8;
      var step = item ? item.offsetWidth + gap : viewport.clientWidth * 0.85;
      viewport.scrollBy({ left: dir * step, behavior: 'smooth' });
      window.setTimeout(updateButtons, 280);
    }

    prev.addEventListener('click', function () { scrollByItem(-1); });
    next.addEventListener('click', function () { scrollByItem(1); });
    viewport.addEventListener('scroll', updateButtons, { passive: true });
    window.addEventListener('resize', updateButtons);
    updateButtons();
    carousel._refreshCarousel = updateButtons;
  }

  function refreshAllCarousels(form) {
    form.querySelectorAll('[data-carousel]').forEach(function (el) {
      if (el._refreshCarousel) el._refreshCarousel();
    });
  }

  function slotColorKey(slotEl) {
    var sel = slotEl.querySelector('.ap-image-slot-key');
    var custom = slotEl.querySelector('.ap-image-slot-custom');
    if (!sel) return '';
    if (sel.value === '__custom__') {
      return String(custom && custom.value || '').trim().toLowerCase();
    }
    return sel.value;
  }

  function usedSlotKeys(form, exceptSlot) {
    var used = {};
    form.querySelectorAll('.ap-image-slot').forEach(function (slot) {
      if (slot === exceptSlot) return;
      var key = slotColorKey(slot);
      if (key && key !== '__custom__') used[key] = true;
    });
    return used;
  }

  function syncSlotKeySelects(form) {
    form.querySelectorAll('.ap-image-slot').forEach(function (slot) {
      var sel = slot.querySelector('.ap-image-slot-key');
      if (!sel) return;
      var current = slotColorKey(slot);
      var isCustom = sel.value === '__custom__' || IMAGE_SLOT_PRESET_VALUES.indexOf(current) < 0;
      var used = usedSlotKeys(form, slot);
      sel.innerHTML = slotKeySelectHtml(isCustom ? '__custom__' : current, used);
      if (!isCustom && current) sel.value = current;
      else if (isCustom) sel.value = '__custom__';
    });
  }

  function bindImageSlot(slot, form) {
    if (slot.dataset.bound) return;
    slot.dataset.bound = '1';

    var carousel = slot.querySelector('[data-carousel]');
    if (carousel) initCarousel(carousel);

    var sel = slot.querySelector('.ap-image-slot-key');
      var custom = slot.querySelector('.ap-image-slot-custom');
      var removeSlot = slot.querySelector('.ap-remove-slot');

      sel?.addEventListener('change', function () {
        var showCustom = sel.value === '__custom__';
        if (custom) {
          custom.hidden = !showCustom;
          if (showCustom) custom.focus();
        }
        syncSlotKeySelects(form);
      });

      custom?.addEventListener('input', function () {
        syncSlotKeySelects(form);
      });

      removeSlot?.addEventListener('click', function () {
        if (form.querySelectorAll('.ap-image-slot').length <= 1) {
          alert('至少保留一個圖片選項');
          return;
        }
        slot.remove();
        syncSlotKeySelects(form);
        refreshAllCarousels(form);
      });

      slot.querySelectorAll('.ap-remove-image').forEach(function (btn) {
        btn.addEventListener('click', function () {
          var item = btn.closest('.ap-carousel-item');
          if (item && !item.classList.contains('ap-carousel-item--upload')) item.remove();
          var carousel = slot.querySelector('[data-carousel]');
          if (carousel && carousel._refreshCarousel) carousel._refreshCarousel();
        });
      });

      var input = slot.querySelector('.ap-image-input');
      var uploading = slot.querySelector('.ap-uploading');
      var track = slot.querySelector('.ap-carousel-track');
      var uploadItem = slot.querySelector('.ap-carousel-item--upload');

      input?.addEventListener('change', function () {
        var files = Array.from(input.files || []);
        if (!files.length || !track || !uploadItem) return;
        if (uploading) uploading.hidden = false;
        var color = slotColorKey(slot) || 'white';
        var uploads = files.map(function (file) {
          var fd = new FormData();
          fd.append('file', file);
          return fetch('/api/admin/product-upload', { method: 'POST', credentials: 'include', body: fd })
            .then(function (r) { return r.json(); });
        });
        Promise.all(uploads).then(function (results) {
          if (uploading) uploading.hidden = true;
          results.forEach(function (res) {
            if (res.error || !res.url) return;
            var wrap = document.createElement('div');
            wrap.innerHTML = imageSlideHtml(res.url, color);
            var item = wrap.firstElementChild;
            item.dataset.url = res.url;
            track.insertBefore(item, uploadItem);
            item.querySelector('.ap-remove-image')?.addEventListener('click', function () {
              item.remove();
              var carousel = slot.querySelector('[data-carousel]');
              if (carousel && carousel._refreshCarousel) carousel._refreshCarousel();
            });
          });
          input.value = '';
          refreshAllCarousels(form);
        }).catch(function () {
          if (uploading) {
            uploading.hidden = false;
            uploading.textContent = '上傳失敗';
          }
        });
      });
  }

  function bindImageSlots(form) {
    form.querySelectorAll('.ap-image-slot').forEach(function (slot) {
      bindImageSlot(slot, form);
    });
  }

  function closeEditor() {
    state.view = 'list';
    state.editingId = null;
    renderShell();
  }

  function editorFormHtml(product, defaultCategory) {
    var isEdit = !!product;
    var category = (product && product.category) || defaultCategory || 'ring';
    var variants = (product && product.variants && product.variants.length)
      ? product.variants.map(function (v) { return variantRowHtml(v, category); }).join('')
      : variantRowHtml(null, category);

    var catOpts = CATEGORY_ORDER.map(function (c) {
      var sel = category === c ? ' selected' : '';
      return '<option value="' + c + '"' + sel + '>' + esc(state.categoryLabels[c] || c) + '</option>';
    }).join('');
    var colorOpts = COLORS.map(function (c) {
      var sel = (product ? product.default_color : 'white') === c ? ' selected' : '';
      return '<option value="' + c + '"' + sel + '>' + COLOR_LABELS[c] + '</option>';
    }).join('');

    return (
      '<div class="ap-editor-page">' +
        '<header class="ap-editor-head">' +
          '<button type="button" class="btn-sm ap-editor-back" id="apEditorBack">← 返回商品列表</button>' +
          '<div class="ap-editor-head-text">' +
            '<h2>' + (isEdit ? '編輯商品' : '新增商品') + '</h2>' +
            '<p class="ap-editor-sub">填寫款式選項並上傳商品照片後可上架至客製試算頁。</p>' +
          '</div>' +
        '</header>' +
        '<div class="ap-editor-body">' +
          '<p class="ap-form-error" id="apFormError" hidden></p>' +
          '<form id="apProductForm" class="ap-form">' +
            '<div class="ap-form-grid">' +
              '<label><span>品項</span><select name="category" id="apCategory">' + catOpts + '</select></label>' +
              '<label><span>預設顏色</span><select name="defaultColor">' + colorOpts + '</select></label>' +
              '<label><span>中文名稱 <span class="ap-required" aria-hidden="true">*</span></span><input name="nameZh" required maxlength="150" autocomplete="off" value="' + esc(product && product.name_zh) + '"></label>' +
              '<label><span>英文名稱</span><input name="nameEn" maxlength="150" value="' + esc(product && product.name_en) + '"></label>' +
              '<label class="ap-field-wide"><span>中文描述</span><textarea class="ap-textarea" name="descriptionZh" rows="3" placeholder="商品中文說明…">' + esc(product && product.description_zh) + '</textarea></label>' +
              '<label class="ap-field-wide"><span>英文描述</span><textarea class="ap-textarea" name="descriptionEn" rows="3" placeholder="Product description…">' + esc(product && product.description_en) + '</textarea></label>' +
              '<label class="ap-checkbox"><input type="checkbox" name="isPublished"' + (product && product.is_published ? ' checked' : '') + '> 立即上架</label>' +
            '</div>' +
            '<h4 class="ap-section-title">款式選項</h4>' +
            '<div class="ap-variant-block">' +
              '<div class="ap-variant-head"><span>金屬</span><span>克拉</span><span>金重</span><span>手動定價</span><span></span></div>' +
              '<div id="apVariantGrid">' + variants + '</div>' +
            '</div>' +
            '<button type="button" class="btn-sm" id="apAddVariant">+ 新增款式</button>' +
            '<h4 class="ap-section-title">商品照片</h4>' +
            '<p class="ap-section-hint">每個選項可上傳多張圖片（金屬色、鑽石色或其他），前台試算頁依選項顯示。</p>' +
            '<div class="ap-image-slots" id="apImageSlots">' + imageSlotsHtml(product && product.images) + '</div>' +
            '<button type="button" class="btn-sm" id="apAddImageSlot">+ 新增圖片選項</button>' +
            '<div class="ap-form-actions ap-editor-actions">' +
              '<button type="button" class="btn-sm" id="apEditorCancel">取消</button>' +
              '<button type="submit" class="btn-sm btn-primary" id="apSaveProduct">' + (isEdit ? '儲存變更' : '建立商品') + '</button>' +
            '</div>' +
          '</form>' +
        '</div>' +
      '</div>'
    );
  }

  function bindEditorEvents(product) {
    var form = document.getElementById('apProductForm');
    var grid = document.getElementById('apVariantGrid');
    var catSel = document.getElementById('apCategory');

    document.getElementById('apEditorBack')?.addEventListener('click', closeEditor);
    document.getElementById('apEditorCancel')?.addEventListener('click', closeEditor);

    document.getElementById('apAddVariant')?.addEventListener('click', function () {
      grid.insertAdjacentHTML('beforeend', variantRowHtml(null, catSel.value));
      bindRemoveRows();
    });

    function bindRemoveRows() {
      grid.querySelectorAll('.ap-remove-row').forEach(function (btn) {
        btn.onclick = function () { btn.closest('.ap-variant-row')?.remove(); };
      });
    }
    bindRemoveRows();

    bindImageSlots(form);

    document.getElementById('apAddImageSlot')?.addEventListener('click', function () {
      var host = document.getElementById('apImageSlots');
      if (!host) return;
      var used = usedSlotKeys(form);
      var pick = IMAGE_SLOT_PRESET_VALUES.find(function (v) { return !used[v]; }) || '__custom__';
      var wrap = document.createElement('div');
      wrap.innerHTML = imageSlotHtml({ color: pick === '__custom__' ? '' : pick, urls: [] }, used);
      var slot = wrap.firstElementChild;
      host.appendChild(slot);
      bindImageSlot(slot, form);
      syncSlotKeySelects(form);
      slot.querySelector('.ap-image-slot-key')?.focus();
    });

    catSel?.addEventListener('change', function () {
      grid.querySelectorAll('.ap-variant-row select[name="carat"]').forEach(function (sel) {
        var prev = sel.value;
        var opts = caratsFor(catSel.value);
        sel.innerHTML = opts.map(function (c) {
          return '<option value="' + c + '">' + c + '</option>';
        }).join('');
        if (opts.indexOf(prev) >= 0) sel.value = prev;
      });
    });

    form.addEventListener('submit', function (e) {
      e.preventDefault();
      saveProduct(form, product);
    });
  }

  function renderEditor(product, defaultCategory) {
    _slotCounter = 0;
    setRoot(editorFormHtml(product, defaultCategory), false);
    bindEditorEvents(product);
    root.scrollIntoView({ block: 'start', behavior: 'smooth' });
  }

  function openEditor(product, defaultCategory) {
    state.view = 'editor';
    state.editingId = product ? product.id : null;
    renderEditor(product, defaultCategory);
  }

  function isValidImageKey(key) {
    return /^[a-z0-9][a-z0-9_-]{0,31}$/.test(key);
  }

  function collectForm(form) {
    var fd = new FormData(form);
    var category = fd.get('category');
    var variants = [];
    form.querySelectorAll('#apVariantGrid .ap-variant-row').forEach(function (row) {
      var gold = row.querySelector('[name="gold"]')?.value;
      var carat = row.querySelector('[name="carat"]')?.value;
      var weight = row.querySelector('[name="weight"]')?.value;
      var price = row.querySelector('[name="price"]')?.value;
      if (!gold || !carat || !weight) return;
      variants.push({
        gold: gold,
        carat: carat,
        weightChin: parseFloat(weight),
        manualPriceTwd: price === '' ? null : parseFloat(price),
      });
    });
    var images = [];
    form.querySelectorAll('.ap-image-slot').forEach(function (slot) {
      var color = slotColorKey(slot);
      if (!color) return;
      slot.querySelectorAll('.ap-carousel-item[data-url]').forEach(function (item) {
        var url = item.dataset.url;
        if (url) images.push({ color: color, url: url });
      });
    });
    return {
      category: category,
      nameZh: String(fd.get('nameZh') || '').trim(),
      nameEn: String(fd.get('nameEn') || '').trim(),
      descriptionZh: String(fd.get('descriptionZh') || '').trim(),
      descriptionEn: String(fd.get('descriptionEn') || '').trim(),
      defaultColor: fd.get('defaultColor') || 'white',
      isPublished: !!form.querySelector('[name="isPublished"]')?.checked,
      variants: variants,
      images: images,
    };
  }

  function saveProduct(form, product) {
    var payload = collectForm(form);
    if (product) payload.id = product.id;
    var btn = document.getElementById('apSaveProduct');
    var errEl = document.getElementById('apFormError');

    if (!payload.nameZh) {
      if (errEl) {
        errEl.textContent = '請填寫中文名稱（必填）';
        errEl.hidden = false;
      }
      form.querySelector('[name="nameZh"]')?.focus();
      return;
    }

    var slotKeys = [];
    var slotError = '';
    form.querySelectorAll('.ap-image-slot').forEach(function (slot) {
      var key = slotColorKey(slot);
      if (!key) {
        slotError = '請為每個圖片選項設定代碼';
        return;
      }
      if (!isValidImageKey(key)) {
        slotError = '圖片選項代碼僅能使用英文小寫、數字、底線或連字號';
        return;
      }
      if (slotKeys.indexOf(key) >= 0) {
        slotError = '圖片選項代碼不可重複：' + key;
        return;
      }
      slotKeys.push(key);
    });
    if (slotError) {
      if (errEl) { errEl.textContent = slotError; errEl.hidden = false; }
      return;
    }

    if (errEl) errEl.hidden = true;
    if (btn) { btn.disabled = true; btn.textContent = '儲存中…'; }
    var req = product ? api.admin.updateProduct(payload) : api.admin.saveProduct(payload);
    req.then(function (res) {
      if (btn) { btn.disabled = false; btn.textContent = product ? '儲存變更' : '建立商品'; }
      if (res.error) {
        if (errEl) {
          errEl.textContent = typeof res.error === 'string' ? res.error : (res.error.message || '儲存失敗');
          errEl.hidden = false;
        } else {
          alert(res.error);
        }
        return;
      }
      state.view = 'list';
      state.editingId = null;
      load(true, true);
    });
  }

  function load(silent, force) {
    if (_loaded && !force && state.view === 'editor') return;
    if (_loaded && !force) return;
    if (!silent) root.innerHTML = '<p class="ap-loading">載入商品中…</p>';
    api.admin.getProducts().then(function (res) {
      if (res.error) {
        root.innerHTML = '<p class="note warn">載入失敗：' + esc(res.error) + '</p>';
        return;
      }
      state.products = res.products || [];
      state.categoryLabels = res.categoryLabels || {};
      _loaded = true;
      if (state.view === 'editor') return;
      renderShell();
    });
  }

  function ensureLoaded() {
    load(_loaded);
  }

  window.AdminProductsPanel = { load: load, ensureLoaded: ensureLoaded };
})();
