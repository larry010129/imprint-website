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
  var METAL_SLOT_OPTIONS = [
    { value: 'white', label: '白金' },
    { value: 'yellow', label: '黃金' },
    { value: 'rose', label: '玫瑰金' },
  ];
  var DIAMOND_SLOT_OPTIONS = [
    { value: 'white', label: '白鑽' },
    { value: 'yellow', label: '黃鑽' },
    { value: 'blue', label: '藍鑽' },
    { value: 'pink', label: '粉鑽' },
  ];
  var METAL_SLOT_VALUES = METAL_SLOT_OPTIONS.map(function (o) { return o.value; });
  var DIAMOND_SLOT_VALUES = DIAMOND_SLOT_OPTIONS.map(function (o) { return o.value; });

  function buildSlotKey(metal, diamond) {
    return String(metal) + '-' + String(diamond);
  }

  function parseSlotKey(key) {
    var parts = String(key || '').split('-');
    if (parts.length >= 2 && METAL_SLOT_VALUES.indexOf(parts[0]) >= 0 && DIAMOND_SLOT_VALUES.indexOf(parts[1]) >= 0) {
      return { metal: parts[0], diamond: parts[1] };
    }
    if (METAL_SLOT_VALUES.indexOf(key) >= 0) return { metal: key, diamond: 'white' };
    return null;
  }

  function allPresetSlotKeys() {
    var keys = [];
    METAL_SLOT_VALUES.forEach(function (metal) {
      DIAMOND_SLOT_VALUES.forEach(function (diamond) {
        keys.push(buildSlotKey(metal, diamond));
      });
    });
    return keys;
  }

  function slotSelectHtml(options, selected) {
    return options.map(function (opt) {
      return '<option value="' + opt.value + '"' + (opt.value === selected ? ' selected' : '') + '>' + esc(opt.label) + '</option>';
    }).join('');
  }

  var root = document.getElementById('productsRoot');
  if (!root) return;

  var state = { products: [], categoryLabels: {}, activeTab: 'cat-pendant', editingId: null, view: 'list' };
  var _loaded = false;
  var _loading = false;
  var _slotCounter = 0;
  var LOAD_TIMEOUT_MS = 25000;

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

  function setRoot(html) {
    root.innerHTML = html;
    root.removeAttribute('aria-busy');
    root.classList.remove('ap-skeleton-shell');
  }

  function loadingSkeletonHtml() {
    return window.SkeletonUI ? window.SkeletonUI.productsShell() : '';
  }

  function tableAreaSkeletonHtml() {
    return window.SkeletonUI
      ? window.SkeletonUI.table({ headers: ['', '縮圖', '品項', '名稱', '狀態', '操作'], rows: 4, label: '載入表格中' })
      : '';
  }

  function showLoadingSkeleton() {
    unmountProductsTable();
    root.classList.add('ap-skeleton-shell');
    root.setAttribute('aria-busy', 'true');
    root.setAttribute('aria-label', '載入商品中');
    root.innerHTML = loadingSkeletonHtml();
  }

  function unmountProductsTable() {
    if (!window.AdminTables) return;
    var el = document.getElementById('apProductsTableRoot');
    if (el) window.AdminTables.unmount(el);
  }

  function renderShell() {
    unmountProductsTable();
    state.view = 'list';
    var tabs = CATEGORY_ORDER.map(function (cat, i) {
      var label = state.categoryLabels[cat] || cat;
      var count = productsInCategory(cat).length;
      var active = state.activeTab === 'cat-' + cat;
      return '<button type="button" class="ap-tab-btn' + (active ? ' is-active' : '') + '" data-tab="cat-' + cat + '" role="tab" aria-selected="' + (active ? 'true' : 'false') + '">' +
        esc(label) + '<span class="ap-tab-count">' + count + '</span></button>';
    }).join('');

    setRoot(
      '<p class="note">管理商品款式、金屬選項與照片。上架後會顯示於客製試算頁；拖曳列可調整排序。</p>' +
      '<div class="ap-toolbar"><button type="button" class="btn-sm btn-primary" id="btnNewProduct">+ 新增商品</button></div>' +
      '<div class="ap-category-tabs" role="tablist">' + tabs + '</div>' +
      '<div class="ap-table-root" id="apProductsTableRoot">' + tableAreaSkeletonHtml() + '</div>' +
      '<dialog id="apDeleteDialog" class="ap-delete-dialog"><form method="dialog" id="apDeleteForm">' +
        '<h3>刪除商品</h3><p id="apDeleteTarget"></p>' +
        '<p class="ap-hint">刪除後無法復原，若已有訂單引用建議改為下架。</p>' +
        '<div class="ap-delete-actions">' +
          '<button type="button" class="btn-sm" id="apDeleteCancel">取消</button>' +
          '<button type="submit" class="btn-sm btn-primary">確認刪除</button>' +
        '</div></form></dialog>'
    );
    bindShellEvents();
    renderActiveCategoryTable();
  }

  function toProductTableRow(product) {
    var status = productStatus(product);
    var ready = publishReady(product);
    return {
      id: product.id,
      category: product.category,
      categoryLabel: state.categoryLabels[product.category] || product.category,
      name: product.name_zh,
      nameEn: product.name_en || '',
      thumbUrl: productThumb(product) || '',
      thumbFallback: window.AdminImageUrls ? window.AdminImageUrls.categoryFallback(product.category) : '',
      statusLabel: status.label,
      statusClass: status.cls,
      previewUrl: previewUrl(product),
      publishAction: product.is_published ? 'unpublish' : 'publish',
      publishLabel: product.is_published ? '下架' : '上架',
      publishDisabled: !product.is_published && !ready.ok,
      publishDisabledReason: ready.reason,
      publishPrimary: !product.is_published && ready.ok,
    };
  }

  function apiError(data) {
    return (api && api.apiErrorMessage) ? api.apiErrorMessage(data) : (data && data.error) || '未知錯誤';
  }

  function whenAdminTablesReady(fn, tries) {
    tries = tries == null ? 120 : tries;
    if (window.AdminTables) {
      fn();
      return;
    }
    if (tries <= 0) {
      var container = document.getElementById('apProductsTableRoot');
      if (container) {
        container.innerHTML = '<p class="ap-empty">載入失敗：表格元件未載入，請重新整理頁面</p>';
      }
      return;
    }
    setTimeout(function () { whenAdminTablesReady(fn, tries - 1); }, 50);
  }

  function renderActiveCategoryTable() {
    var container = document.getElementById('apProductsTableRoot');
    if (!container) return;
    whenAdminTablesReady(function () {
      var cat = state.activeTab.replace('cat-', '');
      window.AdminTables.renderProductsTable(container, {
        rows: productsInCategory(cat).map(toProductTableRow),
        emptyLabel: '此品項尚無商品。',
        onRendered: bindProductRowEvents,
      });
    });
  }

  function bindShellEvents() {
    root.querySelectorAll('.ap-tab-btn').forEach(function (btn) {
      btn.addEventListener('click', function () {
        state.activeTab = btn.dataset.tab;
        root.querySelectorAll('.ap-tab-btn').forEach(function (b) {
          var active = b.dataset.tab === state.activeTab;
          b.classList.toggle('is-active', active);
          b.setAttribute('aria-selected', active ? 'true' : 'false');
        });
        renderActiveCategoryTable();
      });
    });

    var newBtn = document.getElementById('btnNewProduct');
    if (newBtn) {
      newBtn.addEventListener('click', function () {
        var cat = state.activeTab.replace('cat-', '');
        openEditor(null, cat);
      });
    }

    bindDeleteDialog();
  }

  function bindProductRowEvents() {
    var container = document.getElementById('apProductsTableRoot');
    if (!container) return;
    container.querySelectorAll('[data-action]').forEach(function (btn) {
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

    bindDragReorder(container);
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

  function bindDragReorder(scope) {
    var dragged = null;
    (scope || root).querySelectorAll('.ap-table tbody').forEach(function (tbody) {
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
              alert('排序失敗：' + apiError(res));
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
        alert(apiError(res));
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

  function slotKeySelectHtml(selectedKey, used) {
    var parsed = parseSlotKey(selectedKey) || { metal: 'white', diamond: 'white' };
    var taken = used || {};
    return (
      '<label class="ap-image-slot-pair">' +
        '<span>金屬</span>' +
        '<select class="ap-image-slot-metal">' + slotSelectHtml(METAL_SLOT_OPTIONS, parsed.metal) + '</select>' +
      '</label>' +
      '<label class="ap-image-slot-pair">' +
        '<span>鑽石</span>' +
        '<select class="ap-image-slot-diamond">' + slotSelectHtml(DIAMOND_SLOT_OPTIONS, parsed.diamond) + '</select>' +
      '</label>'
    );
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
    var color = slot.color || 'white-white';
    var parsed = parseSlotKey(color) || { metal: 'white', diamond: 'white' };
    var slides = (slot.urls || []).map(function (url) {
      return imageSlideHtml(url, color);
    }).join('');
    var used = Object.assign({}, usedKeys || {});
    used[color] = true;

    return (
      '<div class="ap-image-slot" data-slot-id="' + slotId + '">' +
        '<div class="ap-image-slot-head">' +
          '<div class="ap-image-slot-label ap-image-slot-label--pair">' +
            '<span>圖片選項</span>' +
            slotKeySelectHtml(color, used) +
          '</div>' +
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
                '<div class="ap-carousel-card ap-carousel-card--upload" data-dropzone>' +
                  '<label class="ap-image-upload-btn">' +
                    '<span class="ap-upload-icon">' +
                      '<svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/></svg>' +
                    '</span>' +
                    '<span class="ap-upload-title">上傳圖片</span>' +
                    '<span class="ap-upload-hint">或點擊瀏覽<br>PNG / JPG / WEBP，5MB 內</span>' +
                    '<input type="file" class="ap-image-input" accept="image/png,image/jpeg,image/webp" multiple hidden>' +
                  '</label>' +
                  '<div class="ap-upload-progress" hidden><div class="ap-upload-progress-bar"></div></div>' +
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
    return slots.map(function (slot) {
      var html = imageSlotHtml(slot, used);
      if (parseSlotKey(slot.color)) used[slot.color] = true;
      else if (slot.color) used[slot.color] = true;
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
    var metalSel = slotEl.querySelector('.ap-image-slot-metal');
    var diamondSel = slotEl.querySelector('.ap-image-slot-diamond');
    if (metalSel && diamondSel) {
      return buildSlotKey(metalSel.value, diamondSel.value);
    }
    var legacy = slotEl.querySelector('.ap-image-slot-key');
    return legacy ? legacy.value : '';
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
      var current = slotColorKey(slot);
      var parsed = parseSlotKey(current) || { metal: 'white', diamond: 'white' };
      var metalSel = slot.querySelector('.ap-image-slot-metal');
      var diamondSel = slot.querySelector('.ap-image-slot-diamond');
      if (metalSel) metalSel.value = parsed.metal;
      if (diamondSel) diamondSel.value = parsed.diamond;
    });
  }

  function uploadFilesToSlot(files, slot, form) {
    var track = slot.querySelector('.ap-carousel-track');
    var uploadItem = slot.querySelector('.ap-carousel-item--upload');
    var uploading = slot.querySelector('.ap-uploading');
    var progressWrap = slot.querySelector('.ap-upload-progress');
    var progressBar = slot.querySelector('.ap-upload-progress-bar');
    if (!files.length || !track || !uploadItem) return;

    var color = slotColorKey(slot) || 'white';
    var progressByIndex = files.map(function () { return 0; });

    function updateProgress() {
      if (!progressBar) return;
      var avg = progressByIndex.reduce(function (a, b) { return a + b; }, 0) / progressByIndex.length;
      progressBar.style.width = avg + '%';
    }

    function uploadOne(file, index) {
      return new Promise(function (resolve) {
        var xhr = new XMLHttpRequest();
        xhr.open('POST', '/api/admin/product-upload');
        xhr.withCredentials = true;
        xhr.upload.addEventListener('progress', function (ev) {
          if (ev.lengthComputable) {
            progressByIndex[index] = (ev.loaded / ev.total) * 100;
            updateProgress();
          }
        });
        xhr.onload = function () {
          var res = {};
          try { res = JSON.parse(xhr.responseText); } catch (e) { res = { error: 'parse' }; }
          if (!res.error && xhr.status >= 400) {
            if (typeof res.detail === 'string') res.error = res.detail;
            else res.error = (api && api.apiErrorMessage) ? api.apiErrorMessage(res) : ('HTTP ' + xhr.status);
          }
          progressByIndex[index] = 100;
          updateProgress();
          resolve(res);
        };
        xhr.onerror = function () { resolve({ error: 'network' }); };
        var fd = new FormData();
        fd.append('file', file);
        xhr.send(fd);
      });
    }

    if (uploading) uploading.hidden = true;
    if (progressWrap) progressWrap.hidden = false;
    updateProgress();

    Promise.all(files.map(uploadOne)).then(function (results) {
      if (progressWrap) progressWrap.hidden = true;
      if (progressBar) progressBar.style.width = '0%';
      var hadError = false;
      results.forEach(function (res) {
        if (res.error || !res.url) { hadError = true; return; }
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
      refreshAllCarousels(form);
      if (hadError && uploading) {
        uploading.hidden = false;
        uploading.textContent = '上傳失敗';
      }
    });
  }

  function bindImageSlot(slot, form) {
    if (slot.dataset.bound) return;
    slot.dataset.bound = '1';

    var carousel = slot.querySelector('[data-carousel]');
    if (carousel) initCarousel(carousel);

    var metalSel = slot.querySelector('.ap-image-slot-metal');
    var diamondSel = slot.querySelector('.ap-image-slot-diamond');
    var removeSlot = slot.querySelector('.ap-remove-slot');

    function onSlotKeyChange() {
      var key = slotColorKey(slot);
      slot.querySelectorAll('.ap-carousel-item[data-url]').forEach(function (item) {
        item.dataset.color = key;
      });
      syncSlotKeySelects(form);
    }

    metalSel?.addEventListener('change', onSlotKeyChange);
    diamondSel?.addEventListener('change', onSlotKeyChange);

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
      var dropzone = slot.querySelector('[data-dropzone]');

      input?.addEventListener('change', function () {
        var files = Array.from(input.files || []);
        uploadFilesToSlot(files, slot, form);
        input.value = '';
      });

      if (dropzone) {
        dropzone.addEventListener('dragover', function (e) {
          e.preventDefault();
          dropzone.classList.add('is-dragover');
        });
        dropzone.addEventListener('dragleave', function () {
          dropzone.classList.remove('is-dragover');
        });
        dropzone.addEventListener('drop', function (e) {
          e.preventDefault();
          dropzone.classList.remove('is-dragover');
          var files = Array.from((e.dataTransfer && e.dataTransfer.files) || []).filter(function (f) {
            return /^image\//.test(f.type);
          });
          uploadFilesToSlot(files, slot, form);
        });
      }
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

  function isSaveForLater(form) {
    return !!form.querySelector('[name="saveForLater"]')?.checked;
  }

  function updateSaveButton(form, isEdit) {
    var btn = document.getElementById('apSaveProduct');
    if (!btn || !form) return;
    if (isSaveForLater(form)) {
      btn.classList.remove('btn-primary');
      btn.textContent = '儲存草稿';
    } else {
      btn.classList.add('btn-primary');
      btn.textContent = isEdit ? '儲存並上架' : '建立並上架';
    }
  }

  function saveForLaterToggleHtml(product) {
    var saveForLater = product ? !product.is_published : true;
    var checked = saveForLater ? ' checked' : '';
    return (
      '<div class="ap-switch-wrap">' +
        '<label class="ap-switch">' +
          '<input type="checkbox" class="ap-switch-input" name="saveForLater"' + checked + '>' +
          '<span class="ap-switch-track" aria-hidden="true"><span class="ap-switch-thumb"></span></span>' +
          '<span class="ap-switch-label">稍後上架</span>' +
        '</label>' +
      '</div>'
    );
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
              '<label><span>中文名稱 <span class="ap-required" aria-hidden="true">*</span></span><input name="nameZh" maxlength="150" autocomplete="off" value="' + esc(product && product.name_zh) + '"></label>' +
              '<label><span>英文名稱</span><input name="nameEn" maxlength="150" value="' + esc(product && product.name_en) + '"></label>' +
              '<label class="ap-field-wide"><span>中文描述</span><textarea class="ap-textarea" name="descriptionZh" rows="3" placeholder="商品中文說明…">' + esc(product && product.description_zh) + '</textarea></label>' +
              '<label class="ap-field-wide"><span>英文描述</span><textarea class="ap-textarea" name="descriptionEn" rows="3" placeholder="Product description…">' + esc(product && product.description_en) + '</textarea></label>' +
              saveForLaterToggleHtml(product) +
            '</div>' +
            '<h4 class="ap-section-title">款式選項</h4>' +
            '<div class="ap-variant-block">' +
              '<div class="ap-variant-head"><span>金屬</span><span>克拉</span><span>金重</span><span>手動定價</span><span></span></div>' +
              '<div id="apVariantGrid">' + variants + '</div>' +
            '</div>' +
            '<button type="button" class="btn-sm" id="apAddVariant">+ 新增款式</button>' +
            '<h4 class="ap-section-title">商品照片</h4>' +
            '<p class="ap-section-hint">每個選項可上傳多張圖片，請分別選擇「金屬」與「鑽石顏色」（例如：白金 + 黃鑽 → white-yellow）。前台試算頁會依選項切換商品圖。</p>' +
            '<div class="ap-image-slots" id="apImageSlots">' + imageSlotsHtml(product && product.images) + '</div>' +
            '<button type="button" class="btn-sm" id="apAddImageSlot">+ 新增圖片選項</button>' +
            '<div class="ap-form-actions ap-editor-actions">' +
              '<button type="button" class="btn-sm" id="apEditorCancel">取消</button>' +
              '<button type="submit" class="btn-sm" id="apSaveProduct">儲存草稿</button>' +
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
      var pick = allPresetSlotKeys().find(function (v) { return !used[v]; }) || buildSlotKey('white', 'white');
      var wrap = document.createElement('div');
      wrap.innerHTML = imageSlotHtml({ color: pick, urls: [] }, used);
      var slot = wrap.firstElementChild;
      host.appendChild(slot);
      bindImageSlot(slot, form);
      syncSlotKeySelects(form);
      slot.querySelector('.ap-image-slot-metal')?.focus();
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

    form.querySelector('[name="saveForLater"]')?.addEventListener('change', function () {
      updateSaveButton(form, !!product);
    });
    updateSaveButton(form, !!product);
  }

  function renderEditor(product, defaultCategory) {
    _slotCounter = 0;
    unmountProductsTable();
    setRoot(editorFormHtml(product, defaultCategory));
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
      isPublished: !isSaveForLater(form),
      variants: variants,
      images: images,
    };
  }

  function saveProduct(form, product) {
    var payload = collectForm(form);
    if (product) payload.id = product.id;
    var btn = document.getElementById('apSaveProduct');
    var errEl = document.getElementById('apFormError');
    var isDraft = isSaveForLater(form);

    // 儲存草稿不要求任何欄位；只有正式上架才需要完整資料。
    if (!isDraft) {
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
    }

    if (errEl) errEl.hidden = true;
    if (btn) { btn.disabled = true; btn.textContent = '儲存中…'; }
    var req = product ? api.admin.updateProduct(payload) : api.admin.saveProduct(payload);
    req.then(function (res) {
      if (btn) { btn.disabled = false; updateSaveButton(form, !!product); }
      if (res.error) {
        if (errEl) {
          errEl.textContent = apiError(res);
          errEl.hidden = false;
        } else {
          alert(apiError(res));
        }
        return;
      }
      state.view = 'list';
      state.editingId = null;
      load(true, true);
    });
  }

  function fetchProducts() {
    return new Promise(function (resolve) {
      var done = false;
      var timer = setTimeout(function () {
        if (done) return;
        done = true;
        resolve({ error: '載入逾時，請檢查網路後重試。', timeout: true });
      }, LOAD_TIMEOUT_MS);
      api.admin.getProducts().then(function (res) {
        if (done) return;
        done = true;
        clearTimeout(timer);
        resolve(res);
      });
    });
  }

  function load(silent, force) {
    if (_loading && !force) {
      if (!silent && state.view !== 'editor') showLoadingSkeleton();
      return;
    }
    if (_loaded && !force && state.view === 'editor') return;
    if (_loaded && !force) {
      if (state.view === 'list') renderShell();
      return;
    }

    if (!silent && state.view !== 'editor') showLoadingSkeleton();

    _loading = true;
    fetchProducts().then(function (res) {
      _loading = false;
      if (res.error) {
        unmountProductsTable();
        var retry = res.timeout
          ? ' <button type="button" class="btn-sm" id="apRetryLoad">重試</button>'
          : '';
        root.innerHTML = '<p class="note warn">載入失敗：' + esc(apiError(res)) + retry + '</p>';
        var retryBtn = document.getElementById('apRetryLoad');
        if (retryBtn) retryBtn.addEventListener('click', function () { load(false, true); });
        return;
      }
      state.products = res.products || [];
      state.categoryLabels = res.categoryLabels || {};
      _loaded = true;
      if (state.view === 'editor') return;
      renderShell();
    });
  }

  function prefetch() {
    if (_loaded || _loading) return;
    load(true, false);
  }

  function ensureLoaded() {
    if (_loaded) {
      if (state.view === 'list') renderShell();
      return;
    }
    load(false, false);
  }

  window.AdminProductsPanel = { load: load, ensureLoaded: ensureLoaded, prefetch: prefetch };

  if (root && !root.innerHTML.trim() && window.SkeletonUI) {
    showLoadingSkeleton();
  }
})();
