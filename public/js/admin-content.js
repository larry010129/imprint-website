/* 銘印鑽石｜內容管理（見證 + FAQ + 首頁輪播） */
(function () {
  'use strict';

  var api = window.imprintAPI;
  if (!api || !api.admin) return;

  var root = document.getElementById('contentRoot');
  if (!root) return;

  var _loaded = false;
  var _tab = 'testimonials';
  var _testimonials = [];
  var _faqItems = [];
  var _faqCategories = [];
  var _banners = [];

  function esc(s) {
    return window.AdminPanel && window.AdminPanel.escapeHtml
      ? window.AdminPanel.escapeHtml(s)
      : String(s == null ? '' : s);
  }

  function truncate(s, n) {
    s = String(s || '');
    return s.length > n ? s.slice(0, n) + '…' : s;
  }

  function findTestimonial(id) {
    for (var i = 0; i < _testimonials.length; i++) {
      if (String(_testimonials[i].id) === String(id)) return _testimonials[i];
    }
    return null;
  }

  function findFaq(id) {
    for (var i = 0; i < _faqItems.length; i++) {
      if (String(_faqItems[i].id) === String(id)) return _faqItems[i];
    }
    return null;
  }

  function findBanner(id) {
    for (var i = 0; i < _banners.length; i++) {
      if (String(_banners[i].id) === String(id)) return _banners[i];
    }
    return null;
  }

  function catTitle(id) {
    for (var i = 0; i < _faqCategories.length; i++) {
      if (_faqCategories[i].id === id) return _faqCategories[i].title;
    }
    return id || '—';
  }

  function renderShell() {
    root.innerHTML =
      '<p class="adx-panel-note">管理首頁輪播、FAQ 與客戶見證。見證上架前請確認已取得同意；文案請迴避「培育鑽石與天然鑽石的比較」。FAQ 變更後，頁面 JSON-LD 結構化資料可能需部署更新。</p>' +
      '<div class="adx-tabs" role="tablist">' +
        '<button type="button" class="adx-tab' + (_tab === 'banners' ? ' is-active' : '') + '" data-tab="banners">輪播</button>' +
        '<button type="button" class="adx-tab' + (_tab === 'testimonials' ? ' is-active' : '') + '" data-tab="testimonials">見證</button>' +
        '<button type="button" class="adx-tab' + (_tab === 'faq' ? ' is-active' : '') + '" data-tab="faq">FAQ</button>' +
      '</div>' +
      '<div id="contentPanelBody"></div>';

    root.querySelectorAll('[data-tab]').forEach(function (btn) {
      btn.addEventListener('click', function () {
        _tab = btn.dataset.tab;
        renderShell();
      });
    });

    var body = document.getElementById('contentPanelBody');
    if (_tab === 'banners') renderBanners(body);
    else if (_tab === 'testimonials') renderTestimonials(body);
    else renderFaq(body);
  }

  function renderBanners(body) {
    var rows = _banners.map(function (b) {
      var pub = b.is_published;
      var thumb = b.image_url
        ? '<img class="adx-thumb" src="' + esc(b.image_url) + '" alt="" width="56" height="36" loading="lazy">'
        : '—';
      return '<tr data-id="' + esc(b.id) + '">' +
        '<td>' + thumb + '</td>' +
        '<td>' + esc(b.title) + '</td>' +
        '<td class="adx-muted">' + esc(b.eyebrow || '—') + '</td>' +
        '<td>' + esc(String(b.sort_order || 0)) + '</td>' +
        '<td><span class="adx-badge ' + (pub ? 'adx-badge--active' : 'adx-badge--revoked') + '">' +
          (pub ? '已發布' : '未發布') + '</span></td>' +
        '<td><div class="adx-actions">' +
          '<button type="button" class="btn-sm" data-action="edit-b" data-id="' + esc(b.id) + '">編輯</button>' +
          (pub
            ? '<button type="button" class="btn-sm" data-action="unpublish-b" data-id="' + esc(b.id) + '">下架</button>'
            : '<button type="button" class="btn-sm" data-action="publish-b" data-id="' + esc(b.id) + '">發布</button>') +
          '<button type="button" class="btn-sm adx-action--danger" data-action="delete-b" data-id="' + esc(b.id) + '">刪除</button>' +
        '</div></td></tr>';
    }).join('');

    body.innerHTML =
      '<div class="adx-panel-toolbar"><button type="button" class="btn-sm btn-primary" id="btnAddBanner">+ 新增輪播</button></div>' +
      (_banners.length
        ? '<div class="adx-table-card"><div class="adx-table-wrap"><table class="adx-table adx-table--center">' +
          '<thead><tr><th>圖</th><th>標題</th><th>眉題</th><th>排序</th><th>狀態</th><th>操作</th></tr></thead>' +
          '<tbody>' + rows + '</tbody></table></div></div>'
        : '<p class="adx-table-empty">尚無輪播</p>');

    var addBtn = document.getElementById('btnAddBanner');
    if (addBtn) addBtn.addEventListener('click', function () { openBannerModal(null); });
    body.querySelectorAll('[data-action]').forEach(bindBannerAction);
  }

  function bindBannerAction(btn) {
    btn.addEventListener('click', function (e) {
      e.preventDefault();
      var action = btn.dataset.action;
      var id = btn.dataset.id;
      if (action === 'edit-b') {
        openBannerModal(findBanner(id));
        return;
      }
      var apiAction = action === 'publish-b' ? 'publish' : action === 'unpublish-b' ? 'unpublish' : action === 'delete-b' ? 'delete' : null;
      if (!apiAction || !id) return;
      if (apiAction === 'delete' && !confirm('確定刪除此輪播？')) return;
      btn.disabled = true;
      api.admin.bannerAction(id, apiAction).then(function (res) {
        btn.disabled = false;
        if (res.error) { alert(res.error.message || res.error); return; }
        load(true, true);
      });
    });
  }

  function openBannerModal(b) {
    var isEdit = !!(b && b.id);
    var tone = isEdit ? (b.tone || 'warm') : 'warm';
    var html =
      '<div class="qr-modal ai-modal" role="dialog" aria-modal="true">' +
        '<button type="button" class="qr-modal-close" data-modal-close aria-label="關閉">&times;</button>' +
        '<h3>' + (isEdit ? '編輯輪播' : '新增輪播') + '</h3>' +
        '<p class="ap-form-error" id="acFormError" hidden></p>' +
        '<form id="acBannerForm" class="ap-form" data-id="' + esc(isEdit ? b.id : '') + '">' +
          '<div class="ap-form-grid">' +
            '<label class="ap-field"><span>眉題</span><input name="eyebrow" placeholder="Imprint Diamond" value="' + esc(isEdit ? b.eyebrow : '') + '"></label>' +
            '<label class="ap-field"><span>色調</span><select name="tone">' +
              '<option value="warm"' + (tone === 'warm' ? ' selected' : '') + '>warm</option>' +
              '<option value="light"' + (tone === 'light' ? ' selected' : '') + '>light</option>' +
              '<option value="soft"' + (tone === 'soft' ? ' selected' : '') + '>soft</option>' +
            '</select></label>' +
            '<label class="ap-field ap-field--full"><span>標題</span><input name="title" required value="' + esc(isEdit ? b.title : '') + '"></label>' +
            '<label class="ap-field ap-field--full"><span>說明</span><textarea name="lead" class="ap-textarea" rows="3">' + esc(isEdit ? b.lead : '') + '</textarea></label>' +
            '<label class="ap-field ap-field--full"><span>圖片 URL</span>' +
              '<div class="ap-field-row">' +
                '<input name="imageUrl" id="acBannerImageUrl" required value="' + esc(isEdit ? b.image_url : '') + '">' +
                '<label class="btn-sm" style="cursor:pointer;white-space:nowrap">' +
                  '上傳<input type="file" id="acBannerFile" accept="image/png,image/jpeg,image/webp" hidden>' +
                '</label>' +
              '</div></label>' +
            '<label class="ap-field"><span>WebP URL（選填）</span><input name="imageWebp" value="' + esc(isEdit ? (b.image_webp || '') : '') + '"></label>' +
            '<label class="ap-field"><span>圖片 alt</span><input name="imageAlt" value="' + esc(isEdit ? b.image_alt : '') + '"></label>' +
            '<label class="ap-field"><span>主按鈕文字</span><input name="ctaPrimaryLabel" value="' + esc(isEdit ? b.cta_primary_label : '') + '"></label>' +
            '<label class="ap-field"><span>主按鈕連結</span><input name="ctaPrimaryHref" placeholder="/shop/calculator/" value="' + esc(isEdit ? b.cta_primary_href : '') + '"></label>' +
            '<label class="ap-field"><span>次按鈕文字</span><input name="ctaSecondaryLabel" value="' + esc(isEdit ? b.cta_secondary_label : '') + '"></label>' +
            '<label class="ap-field"><span>次按鈕連結</span><input name="ctaSecondaryHref" placeholder="#home-poem 或 /path" value="' + esc(isEdit ? b.cta_secondary_href : '') + '"></label>' +
            '<label class="ap-field"><span>排序</span><input type="number" name="sortOrder" value="' + esc(String(isEdit ? b.sort_order : 0)) + '"></label>' +
            '<label class="ap-field ap-field--check"><input type="checkbox" name="isPublished"' + (!isEdit || b.is_published ? ' checked' : '') + '><span>發布</span></label>' +
          '</div>' +
          '<div class="ap-form-actions">' +
            '<button type="button" class="btn-sm" data-modal-close>取消</button>' +
            '<button type="submit" class="btn-sm btn-primary">' + (isEdit ? '儲存' : '建立') + '</button>' +
          '</div>' +
        '</form></div>';

    if (!window.AdminPanel || !window.AdminPanel.openModal) return;
    window.AdminPanel.openModal(html);
    var form = document.getElementById('acBannerForm');
    if (form) form.addEventListener('submit', submitBanner);
    var fileInput = document.getElementById('acBannerFile');
    if (fileInput) {
      fileInput.addEventListener('change', function () {
        var file = fileInput.files && fileInput.files[0];
        if (!file) return;
        fileInput.disabled = true;
        api.admin.uploadBanner(file).then(function (res) {
          fileInput.disabled = false;
          fileInput.value = '';
          if (res.error || !res.url) {
            alert(res.error || '上傳失敗');
            return;
          }
          var urlInput = document.getElementById('acBannerImageUrl');
          if (urlInput) urlInput.value = res.url;
        });
      });
    }
  }

  function submitBanner(e) {
    e.preventDefault();
    var form = e.target;
    var fd = new FormData(form);
    var errEl = document.getElementById('acFormError');
    var id = form.dataset.id;
    var payload = {
      id: id || undefined,
      eyebrow: String(fd.get('eyebrow') || '').trim(),
      title: String(fd.get('title') || '').trim(),
      lead: String(fd.get('lead') || '').trim(),
      imageUrl: String(fd.get('imageUrl') || '').trim(),
      imageWebp: String(fd.get('imageWebp') || '').trim(),
      imageAlt: String(fd.get('imageAlt') || '').trim(),
      ctaPrimaryLabel: String(fd.get('ctaPrimaryLabel') || '').trim(),
      ctaPrimaryHref: String(fd.get('ctaPrimaryHref') || '').trim(),
      ctaSecondaryLabel: String(fd.get('ctaSecondaryLabel') || '').trim(),
      ctaSecondaryHref: String(fd.get('ctaSecondaryHref') || '').trim(),
      tone: String(fd.get('tone') || 'warm').trim(),
      sortOrder: fd.get('sortOrder'),
      isPublished: !!form.querySelector('[name="isPublished"]').checked,
    };
    var req = id ? api.admin.updateBanner(payload) : api.admin.createBanner(payload);
    req.then(function (res) {
      if (res.error) {
        if (errEl) { errEl.textContent = res.error.message || res.error; errEl.hidden = false; }
        else alert(res.error);
        return;
      }
      if (window.AdminPanel.closeModal) window.AdminPanel.closeModal();
      load(true, true);
    });
  }

  function renderTestimonials(body) {
    var rows = _testimonials.map(function (t) {
      var pub = t.is_published;
      var thumb = t.image_url
        ? '<img class="adx-thumb" src="' + esc(t.image_url) + '" alt="" width="56" height="36" loading="lazy">'
        : '—';
      return '<tr data-id="' + esc(t.id) + '">' +
        '<td>' + thumb + '</td>' +
        '<td>' + esc(t.name) + '</td>' +
        '<td>' + esc(t.category || '—') + '</td>' +
        '<td>' + esc(t.city || '—') + '</td>' +
        '<td class="adx-muted">' + esc(truncate(t.text, 48)) + '</td>' +
        '<td>' + esc(String(t.sort_order || 0)) + '</td>' +
        '<td><span class="adx-badge ' + (pub ? 'adx-badge--active' : 'adx-badge--revoked') + '">' +
          (pub ? '已發布' : '未發布') + '</span></td>' +
        '<td><div class="adx-actions">' +
          '<button type="button" class="btn-sm" data-action="edit-t" data-id="' + esc(t.id) + '">編輯</button>' +
          (pub
            ? '<button type="button" class="btn-sm" data-action="unpublish-t" data-id="' + esc(t.id) + '">下架</button>'
            : '<button type="button" class="btn-sm" data-action="publish-t" data-id="' + esc(t.id) + '">發布</button>') +
          '<button type="button" class="btn-sm adx-action--danger" data-action="delete-t" data-id="' + esc(t.id) + '">刪除</button>' +
        '</div></td></tr>';
    }).join('');

    body.innerHTML =
      '<div class="adx-panel-toolbar"><button type="button" class="btn-sm btn-primary" id="btnAddTestimonial">+ 新增見證</button></div>' +
      (_testimonials.length
        ? '<div class="adx-table-card"><div class="adx-table-wrap"><table class="adx-table adx-table--center">' +
          '<thead><tr><th>圖</th><th>姓名</th><th>分類</th><th>城市</th><th>內容</th><th>排序</th><th>狀態</th><th>操作</th></tr></thead>' +
          '<tbody>' + rows + '</tbody></table></div></div>'
        : '<p class="adx-table-empty">尚無見證</p>');

    var addBtn = document.getElementById('btnAddTestimonial');
    if (addBtn) addBtn.addEventListener('click', function () { openTestimonialModal(null); });
    body.querySelectorAll('[data-action]').forEach(bindTestimonialAction);
  }

  function bindTestimonialAction(btn) {
    btn.addEventListener('click', function (e) {
      e.preventDefault();
      var action = btn.dataset.action;
      var id = btn.dataset.id;
      if (action === 'edit-t') {
        openTestimonialModal(findTestimonial(id));
        return;
      }
      var apiAction = action === 'publish-t' ? 'publish' : action === 'unpublish-t' ? 'unpublish' : action === 'delete-t' ? 'delete' : null;
      if (!apiAction || !id) return;
      if (apiAction === 'delete' && !confirm('確定刪除此見證？')) return;
      btn.disabled = true;
      api.admin.testimonialAction(id, apiAction).then(function (res) {
        btn.disabled = false;
        if (res.error) { alert(res.error.message || res.error); return; }
        load(true, true);
      });
    });
  }

  function openTestimonialModal(t) {
    var isEdit = !!(t && t.id);
    var html =
      '<div class="qr-modal ai-modal" role="dialog" aria-modal="true">' +
        '<button type="button" class="qr-modal-close" data-modal-close aria-label="關閉">&times;</button>' +
        '<h3>' + (isEdit ? '編輯見證' : '新增見證') + '</h3>' +
        '<p class="ap-form-error" id="acFormError" hidden></p>' +
        '<form id="acTestimonialForm" class="ap-form" data-id="' + esc(isEdit ? t.id : '') + '">' +
          '<div class="ap-form-grid">' +
            '<label class="ap-field"><span>姓名</span><input name="name" required value="' + esc(isEdit ? t.name : '') + '"></label>' +
            '<label class="ap-field"><span>顯示角色</span><input name="role" placeholder="寵物鑽石・高雄" value="' + esc(isEdit ? t.role : '') + '"></label>' +
            '<label class="ap-field"><span>分類</span><input name="category" placeholder="寵物鑽石" value="' + esc(isEdit ? t.category : '') + '"></label>' +
            '<label class="ap-field"><span>城市</span><input name="city" value="' + esc(isEdit ? t.city : '') + '"></label>' +
            '<label class="ap-field"><span>評分 (1–5)</span><input type="number" name="rating" min="1" max="5" value="' + esc(String(isEdit ? t.rating : 5)) + '"></label>' +
            '<label class="ap-field"><span>排序</span><input type="number" name="sortOrder" value="' + esc(String(isEdit ? t.sort_order : 0)) + '"></label>' +
            '<label class="ap-field ap-field--full"><span>圖片（訂製款式）</span>' +
              '<select id="acJewelryPreset">' +
                '<option value="">— 選擇與訂製頁相同款式 —</option>' +
                '<optgroup label="戒指">' +
                  '<option value="/static/images/testimonials/presets/ring-A.jpg">經典六爪（ring-A）</option>' +
                  '<option value="/static/images/testimonials/presets/ring-B.jpg">低語之光（ring-B）</option>' +
                  '<option value="/static/images/testimonials/presets/ring-C.jpg">羽翼（ring-C）</option>' +
                '</optgroup>' +
                '<optgroup label="項墜／項鍊">' +
                  '<option value="/static/images/testimonials/presets/pendant-A.jpg">四爪項墜（pendant-A）</option>' +
                  '<option value="/static/images/testimonials/presets/pendant-B.jpg">兔耳項墜（pendant-B）</option>' +
                  '<option value="/static/images/testimonials/presets/pendant-C.jpg">水滴項墜（pendant-C）</option>' +
                '</optgroup>' +
              '</select></label>' +
            '<label class="ap-field ap-field--full"><span>圖片 URL</span>' +
              '<div class="ap-field-row">' +
                '<input name="imageUrl" id="acTestimonialImageUrl" value="' + esc(isEdit ? (t.image_url || '') : '') + '" placeholder="/static/images/testimonials/...">' +
                '<label class="btn-sm" style="cursor:pointer;white-space:nowrap">' +
                  '上傳<input type="file" id="acTestimonialFile" accept="image/png,image/jpeg,image/webp" hidden>' +
                '</label>' +
              '</div></label>' +
            '<label class="ap-field ap-field--full"><span>見證內容</span><textarea name="text" class="ap-textarea" rows="4" required>' + esc(isEdit ? t.text : '') + '</textarea></label>' +
            '<label class="ap-field ap-field--check"><input type="checkbox" name="isPublished"' + (!isEdit || t.is_published ? ' checked' : '') + '><span>發布</span></label>' +
          '</div>' +
          '<div class="ap-form-actions">' +
            '<button type="button" class="btn-sm" data-modal-close>取消</button>' +
            '<button type="submit" class="btn-sm btn-primary">' + (isEdit ? '儲存' : '建立') + '</button>' +
          '</div>' +
        '</form></div>';

    if (!window.AdminPanel || !window.AdminPanel.openModal) return;
    window.AdminPanel.openModal(html);
    var form = document.getElementById('acTestimonialForm');
    if (form) form.addEventListener('submit', submitTestimonial);
    var preset = document.getElementById('acJewelryPreset');
    var urlInput = document.getElementById('acTestimonialImageUrl');
    if (preset && urlInput) {
      if (urlInput.value) {
        for (var i = 0; i < preset.options.length; i++) {
          if (preset.options[i].value === urlInput.value) {
            preset.selectedIndex = i;
            break;
          }
        }
      }
      preset.addEventListener('change', function () {
        if (preset.value) urlInput.value = preset.value;
      });
    }
    var fileInput = document.getElementById('acTestimonialFile');
    if (fileInput) {
      fileInput.addEventListener('change', function () {
        var file = fileInput.files && fileInput.files[0];
        if (!file) return;
        fileInput.disabled = true;
        api.admin.uploadTestimonial(file).then(function (res) {
          fileInput.disabled = false;
          fileInput.value = '';
          if (res.error || !res.url) {
            alert(res.error || '上傳失敗');
            return;
          }
          if (urlInput) urlInput.value = res.url;
          if (preset) preset.selectedIndex = 0;
        });
      });
    }
  }

  function submitTestimonial(e) {
    e.preventDefault();
    var form = e.target;
    var fd = new FormData(form);
    var errEl = document.getElementById('acFormError');
    var id = form.dataset.id;
    var payload = {
      id: id || undefined,
      name: String(fd.get('name') || '').trim(),
      role: String(fd.get('role') || '').trim(),
      category: String(fd.get('category') || '').trim(),
      city: String(fd.get('city') || '').trim(),
      text: String(fd.get('text') || '').trim(),
      imageUrl: String(fd.get('imageUrl') || '').trim(),
      rating: fd.get('rating'),
      sortOrder: fd.get('sortOrder'),
      isPublished: !!form.querySelector('[name="isPublished"]').checked,
    };
    var req = id ? api.admin.updateTestimonial(payload) : api.admin.createTestimonial(payload);
    req.then(function (res) {
      if (res.error) {
        if (errEl) { errEl.textContent = res.error.message || res.error; errEl.hidden = false; }
        else alert(res.error);
        return;
      }
      if (window.AdminPanel.closeModal) window.AdminPanel.closeModal();
      load(true, true);
    });
  }

  function renderFaq(body) {
    var rows = _faqItems.map(function (f) {
      var pub = f.is_published;
      return '<tr data-id="' + esc(f.id) + '">' +
        '<td><code class="adx-code">' + esc(f.id) + '</code></td>' +
        '<td>' + esc(catTitle(f.category_id)) + '</td>' +
        '<td>' + esc(truncate(f.question, 36)) + '</td>' +
        '<td>' + (f.show_in_teaser ? '是' : '—') + '</td>' +
        '<td><span class="adx-badge ' + (pub ? 'adx-badge--active' : 'adx-badge--revoked') + '">' +
          (pub ? '已發布' : '未發布') + '</span></td>' +
        '<td><div class="adx-actions">' +
          '<button type="button" class="btn-sm" data-action="edit-f" data-id="' + esc(f.id) + '">編輯</button>' +
          (pub
            ? '<button type="button" class="btn-sm" data-action="unpublish-f" data-id="' + esc(f.id) + '">下架</button>'
            : '<button type="button" class="btn-sm" data-action="publish-f" data-id="' + esc(f.id) + '">發布</button>') +
          '<button type="button" class="btn-sm adx-action--danger" data-action="delete-f" data-id="' + esc(f.id) + '">刪除</button>' +
        '</div></td></tr>';
    }).join('');

    body.innerHTML =
      '<div class="adx-panel-toolbar"><button type="button" class="btn-sm btn-primary" id="btnAddFaq">+ 新增 FAQ</button></div>' +
      (_faqItems.length
        ? '<div class="adx-table-card"><div class="adx-table-wrap"><table class="adx-table adx-table--center">' +
          '<thead><tr><th>ID</th><th>分類</th><th>問題</th><th>首頁精選</th><th>狀態</th><th>操作</th></tr></thead>' +
          '<tbody>' + rows + '</tbody></table></div></div>'
        : '<p class="adx-table-empty">尚無 FAQ</p>');

    var addBtn = document.getElementById('btnAddFaq');
    if (addBtn) addBtn.addEventListener('click', function () { openFaqModal(null); });
    body.querySelectorAll('[data-action]').forEach(bindFaqAction);
  }

  function bindFaqAction(btn) {
    btn.addEventListener('click', function (e) {
      e.preventDefault();
      var action = btn.dataset.action;
      var id = btn.dataset.id;
      if (action === 'edit-f') {
        openFaqModal(findFaq(id));
        return;
      }
      var apiAction = action === 'publish-f' ? 'publish' : action === 'unpublish-f' ? 'unpublish' : action === 'delete-f' ? 'delete' : null;
      if (!apiAction || !id) return;
      if (apiAction === 'delete' && !confirm('確定刪除此 FAQ？')) return;
      btn.disabled = true;
      api.admin.faqAction(id, apiAction).then(function (res) {
        btn.disabled = false;
        if (res.error) { alert(res.error.message || res.error); return; }
        load(true, true);
      });
    });
  }

  function openFaqModal(f) {
    var isEdit = !!(f && f.id);
    var opts = _faqCategories.map(function (c) {
      var sel = isEdit && f.category_id === c.id ? ' selected' : '';
      return '<option value="' + esc(c.id) + '"' + sel + '>' + esc(c.title) + '</option>';
    }).join('');

    var html =
      '<div class="qr-modal ai-modal" role="dialog" aria-modal="true">' +
        '<button type="button" class="qr-modal-close" data-modal-close aria-label="關閉">&times;</button>' +
        '<h3>' + (isEdit ? '編輯 FAQ' : '新增 FAQ') + '</h3>' +
        '<p class="ap-form-error" id="acFormError" hidden></p>' +
        '<form id="acFaqForm" class="ap-form" data-id="' + esc(isEdit ? f.id : '') + '">' +
          '<div class="ap-form-grid">' +
            '<label class="ap-field"><span>分類</span><select name="categoryId" required>' + opts + '</select></label>' +
            '<label class="ap-field"><span>排序</span><input type="number" name="sortOrder" value="' + esc(String(isEdit ? f.sort_order : 0)) + '"></label>' +
            '<label class="ap-field ap-field--full"><span>問題</span><input name="question" required value="' + esc(isEdit ? f.question : '') + '"></label>' +
            '<label class="ap-field ap-field--full"><span>回答</span><textarea name="answer" class="ap-textarea" rows="5" required>' + esc(isEdit ? f.answer : '') + '</textarea></label>' +
            '<label class="ap-field ap-field--check"><input type="checkbox" name="isPublished"' + (!isEdit || f.is_published ? ' checked' : '') + '><span>發布</span></label>' +
            '<label class="ap-field ap-field--check"><input type="checkbox" name="showInTeaser"' + (isEdit && f.show_in_teaser ? ' checked' : '') + '><span>首頁 FAQ 精選</span></label>' +
          '</div>' +
          '<div class="ap-form-actions">' +
            '<button type="button" class="btn-sm" data-modal-close>取消</button>' +
            '<button type="submit" class="btn-sm btn-primary">' + (isEdit ? '儲存' : '建立') + '</button>' +
          '</div>' +
        '</form></div>';

    if (!window.AdminPanel || !window.AdminPanel.openModal) return;
    window.AdminPanel.openModal(html);
    var form = document.getElementById('acFaqForm');
    if (form) form.addEventListener('submit', submitFaq);
  }

  function submitFaq(e) {
    e.preventDefault();
    var form = e.target;
    var fd = new FormData(form);
    var errEl = document.getElementById('acFormError');
    var id = form.dataset.id;
    var payload = {
      id: id || undefined,
      categoryId: String(fd.get('categoryId') || '').trim(),
      question: String(fd.get('question') || '').trim(),
      answer: String(fd.get('answer') || '').trim(),
      sortOrder: fd.get('sortOrder'),
      isPublished: !!form.querySelector('[name="isPublished"]').checked,
      showInTeaser: !!form.querySelector('[name="showInTeaser"]').checked,
    };
    var req = id ? api.admin.updateFaqItem(payload) : api.admin.createFaqItem(payload);
    req.then(function (res) {
      if (res.error) {
        if (errEl) { errEl.textContent = res.error.message || res.error; errEl.hidden = false; }
        else alert(res.error);
        return;
      }
      if (window.AdminPanel.closeModal) window.AdminPanel.closeModal();
      load(true, true);
    });
  }

  function load(silent, force) {
    if (_loaded && !force) return;
    if (!silent) {
      root.innerHTML = '<p class="adx-loading-inline">載入內容中…</p>';
    }
    Promise.all([
      api.admin.getTestimonials(),
      api.admin.getFaqItems(),
      api.admin.getBanners(),
    ]).then(function (results) {
      var tRes = results[0];
      var fRes = results[1];
      var bRes = results[2];
      if (tRes.error || fRes.error || bRes.error) {
        root.innerHTML = '<p class="note warn">載入失敗：' + esc(tRes.error || fRes.error || bRes.error) + '</p>';
        return;
      }
      _testimonials = tRes.testimonials || [];
      _faqItems = fRes.items || [];
      _faqCategories = fRes.categories || [];
      _banners = bRes.banners || [];
      _loaded = true;
      root.removeAttribute('aria-busy');
      renderShell();
    });
  }

  function ensureLoaded() {
    load(_loaded);
  }

  window.AdminContentPanel = { load: load, ensureLoaded: ensureLoaded };

  document.querySelectorAll('.side-nav button[data-panel="content"]').forEach(function (btn) {
    btn.addEventListener('click', ensureLoaded);
  });

  var panel = document.getElementById('panel-content');
  if (panel && panel.classList.contains('is-active')) ensureLoaded();
})();
