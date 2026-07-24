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

  var PAGE_LINKS = [
    { value: '/', label: '首頁' },
    { value: '/shop/calculator/', label: '客製試算' },
    { value: '/price.html', label: 'DNA 鑽石價格' },
    { value: '/gold-price.html', label: '台銀金價' },
    { value: '/series.html', label: '系列總覽' },
    { value: '/what-is-dna-diamond.html', label: 'DNA 鑽石的誕生' },
    { value: '/faq.html', label: '常見問題' },
    { value: '/about.html', label: '品牌故事' },
    { value: '/stories.html', label: '客戶見證' },
    { value: '/contact.html', label: '聯絡我們' },
    { value: '/track-order.html', label: '查詢訂製進度' },
    { value: '/jewelry/', label: '飾品訂製' },
    { value: '#home-poem', label: '首頁・詩文區塊' },
    { value: '#series', label: '首頁・系列區塊' },
    { value: 'https://lin.ee/ktVBtmx', label: '官方 LINE' },
  ];

  var TESTIMONIAL_CATEGORIES = [
    '寵物鑽石', '結髮鑽石', '生命鑽石', '毛髮鑽石', '全家福鑽石', '初生鑽石',
  ];

  var TAIWAN_CITIES = [
    '台北市', '新北市', '桃園市', '台中市', '台南市', '高雄市',
    '基隆市', '新竹市', '新竹縣', '苗栗縣', '彰化縣', '南投縣',
    '雲林縣', '嘉義市', '嘉義縣', '屏東縣', '宜蘭縣', '花蓮縣',
    '台東縣', '澎湖縣', '金門縣', '連江縣',
  ];

  function reqStar() {
    return ' <span class="ap-required" aria-hidden="true">*</span>';
  }

  function splitTestimonialName(t) {
    if (t && t.name_part != null) {
      return { part: t.name_part || '', honorific: t.honorific || '小姐' };
    }
    var full = String((t && t.name) || '').trim();
    if (full.endsWith('先生')) return { part: full.slice(0, -2), honorific: '先生' };
    if (full.endsWith('小姐')) return { part: full.slice(0, -2), honorific: '小姐' };
    return { part: full, honorific: '小姐' };
  }

  function categoryOptions(selected) {
    selected = String(selected || '').trim();
    var html = '<option value="">— 請選擇 —</option>';
    for (var i = 0; i < TESTIMONIAL_CATEGORIES.length; i++) {
      var c = TESTIMONIAL_CATEGORIES[i];
      html += '<option value="' + esc(c) + '"' + (selected === c ? ' selected' : '') + '>' + esc(c) + '</option>';
    }
    if (selected && TESTIMONIAL_CATEGORIES.indexOf(selected) < 0) {
      html += '<option value="' + esc(selected) + '" selected>' + esc(selected) + '</option>';
    }
    return html;
  }

  function cityDatalistOptions() {
    return TAIWAN_CITIES.map(function (c) {
      return '<option value="' + esc(c) + '">';
    }).join('');
  }

  function pageLinkOptions(current) {
    current = String(current || '').trim();
    var known = {};
    var html = '<option value="">— 選擇頁面 —</option>';
    for (var i = 0; i < PAGE_LINKS.length; i++) {
      var p = PAGE_LINKS[i];
      known[p.value] = true;
      html +=
        '<option value="' +
        esc(p.value) +
        '"' +
        (current === p.value ? ' selected' : '') +
        '>' +
        esc(p.label) +
        '</option>';
    }
    if (current && !known[current]) {
      html +=
        '<option value="' +
        esc(current) +
        '" selected>目前連結：' +
        esc(current) +
        '</option>';
    }
    return html;
  }

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
    var oldMount = document.getElementById('contentReactMount');
    if (oldMount && window.AdminTables && window.AdminTables.unmount) {
      try { window.AdminTables.unmount(oldMount); } catch (e) {}
    }

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
    renderContentReact(body);
  }

  function renderContentReact(body) {
    if (!body) return;
    if (!window.AdminTables || !window.AdminTables.renderContentTables) {
      body.innerHTML = '<p class="note warn">表格元件尚未載入，請重新整理頁面。</p>';
      return;
    }

    var mount = document.getElementById('contentReactMount');
    if (!mount) {
      body.innerHTML = '<div id="contentReactMount"></div>';
      mount = document.getElementById('contentReactMount');
    }

    var faqRows = _faqItems.map(function (f) {
      return {
        id: String(f.id),
        category_title: catTitle(f.category_id),
        question: f.question || '',
        show_in_teaser: !!f.show_in_teaser,
        is_published: !!f.is_published,
      };
    });

    var bannerRows = _banners.map(function (b) {
      return {
        id: String(b.id),
        title: b.title || '',
        eyebrow: b.eyebrow || '',
        sort_order: Number(b.sort_order || 0),
        is_published: !!b.is_published,
        image_url: b.image_url || '',
      };
    });

    var testimonialRows = _testimonials.slice().sort(function (a, b) {
      return Number(a.sort_order || 0) - Number(b.sort_order || 0);
    }).map(function (t) {
      return {
        id: String(t.id),
        name: t.name || '',
        category: t.category || '',
        city: t.city || '',
        text: t.text || '',
        sort_order: Number(t.sort_order || 0),
        is_published: !!t.is_published,
        image_url: t.image_url || '',
      };
    });

    window.AdminTables.renderContentTables(mount, {
      tab: _tab,
      banners: bannerRows,
      testimonials: testimonialRows,
      faqItems: faqRows,
      onAdd: function () {
        if (_tab === 'banners') openBannerModal(null);
        else if (_tab === 'testimonials') openTestimonialModal(null);
        else openFaqModal(null);
      },
      onEdit: function (id) {
        if (_tab === 'banners') openBannerModal(findBanner(id));
        else if (_tab === 'testimonials') openTestimonialModal(findTestimonial(id));
        else openFaqModal(findFaq(id));
      },
      onReorder: function (id, direction) {
        if (_tab !== 'testimonials' || !id || !direction) return;
        api.admin.reorderTestimonial(id, direction).then(function (res) {
          if (res.error) {
            alert(res.error.message || res.error);
            return;
          }
          load(true, true);
        });
      },
      onAction: function (id, action) {
        if (!id || !action) return;
        if (action === 'delete') {
          var label = _tab === 'banners' ? '輪播' : _tab === 'testimonials' ? '見證' : 'FAQ';
          if (!confirm('確定刪除此' + label + '？')) return;
        }
        var req =
          _tab === 'banners'
            ? api.admin.bannerAction(id, action)
            : _tab === 'testimonials'
              ? api.admin.testimonialAction(id, action)
              : api.admin.faqAction(id, action);
        req.then(function (res) {
          if (res.error) {
            alert(res.error.message || res.error);
            return;
          }
          load(true, true);
        });
      },
    });
  }

  function renderBanners(body) {
    renderContentReact(body);
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
            '<div class="ap-field" id="acPrimaryHrefMount"></div>' +
            '<label class="ap-field"><span>次按鈕文字</span><input name="ctaSecondaryLabel" value="' + esc(isEdit ? b.cta_secondary_label : '') + '"></label>' +
            '<div class="ap-field" id="acSecondaryHrefMount"></div>' +
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

    if (window.AdminTables && window.AdminTables.renderPageLinkSelect) {
      var primaryMount = document.getElementById('acPrimaryHrefMount');
      var secondaryMount = document.getElementById('acSecondaryHrefMount');
      if (primaryMount) {
        window.AdminTables.renderPageLinkSelect(primaryMount, {
          name: 'ctaPrimaryHref',
          label: '主按鈕連結',
          value: isEdit ? (b.cta_primary_href || '') : '/shop/calculator/',
          placeholder: '— 選擇頁面 —',
        });
      }
      if (secondaryMount) {
        window.AdminTables.renderPageLinkSelect(secondaryMount, {
          name: 'ctaSecondaryHref',
          label: '次按鈕連結',
          value: isEdit ? (b.cta_secondary_href || '') : '',
          placeholder: '— 選擇頁面 —',
        });
      }
    }

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
    renderContentReact(body);
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
    var nameParts = splitTestimonialName(t);
    var imageUrl = isEdit ? (t.image_url || '') : '';
    var html =
      '<div class="qr-modal ai-modal" role="dialog" aria-modal="true">' +
        '<button type="button" class="qr-modal-close" data-modal-close aria-label="關閉">&times;</button>' +
        '<h3>' + (isEdit ? '編輯見證' : '新增見證') + '</h3>' +
        '<p class="ap-form-error" id="acFormError" hidden></p>' +
        '<form id="acTestimonialForm" class="ap-form" data-id="' + esc(isEdit ? t.id : '') + '">' +
          '<div class="ap-form-grid">' +
            '<label class="ap-field"><span>姓名' + reqStar() + '</span>' +
              '<div class="ap-name-row">' +
                '<input name="namePart" required maxlength="30" autocomplete="off" placeholder="姓氏或名字" value="' + esc(nameParts.part) + '">' +
                '<select name="honorific" aria-label="稱謂">' +
                  '<option value="小姐"' + (nameParts.honorific === '小姐' ? ' selected' : '') + '>小姐</option>' +
                  '<option value="先生"' + (nameParts.honorific === '先生' ? ' selected' : '') + '>先生</option>' +
                '</select>' +
              '</div></label>' +
            '<label class="ap-field"><span>分類' + reqStar() + '</span>' +
              '<select name="category" required>' + categoryOptions(isEdit ? t.category : '') + '</select></label>' +
            '<label class="ap-field"><span>城市' + reqStar() + '</span>' +
              '<input name="city" list="acTaiwanCities" required autocomplete="off" placeholder="輸入或選擇縣市" value="' + esc(isEdit ? t.city : '') + '">' +
              '<datalist id="acTaiwanCities">' + cityDatalistOptions() + '</datalist></label>' +
            '<label class="ap-field ap-field--full"><span>訂製款式圖片' + reqStar() + '</span>' +
              '<div class="ap-testimonial-upload">' +
                '<div class="ap-testimonial-upload-preview" id="acTestimonialPreview">' +
                  (imageUrl
                    ? '<img src="' + esc(imageUrl) + '" alt="">'
                    : '<span class="ap-testimonial-upload-empty">尚未上傳</span>') +
                '</div>' +
                '<label class="btn-sm ap-testimonial-upload-btn">' +
                  '上傳圖片' +
                  '<input type="file" id="acTestimonialFile" accept="image/png,image/jpeg,image/webp" hidden>' +
                '</label>' +
                '<p class="ap-section-hint">PNG / JPG / WEBP，5MB 內。前台顯示角色為「分類・城市」。</p>' +
              '</div>' +
              '<input type="hidden" name="imageUrl" id="acTestimonialImageUrl" value="' + esc(imageUrl) + '">' +
            '</label>' +
            '<label class="ap-field ap-field--full"><span>見證內容（完整）' + reqStar() + '</span>' +
              '<textarea name="text" class="ap-textarea" rows="8" required placeholder="完整見證文案…">' + esc(isEdit ? t.text : '') + '</textarea></label>' +
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

    var urlInput = document.getElementById('acTestimonialImageUrl');
    var preview = document.getElementById('acTestimonialPreview');
    function setPreview(url) {
      if (!preview || !urlInput) return;
      urlInput.value = url || '';
      if (url) {
        preview.innerHTML = '<img src="' + esc(url) + '" alt="">';
      } else {
        preview.innerHTML = '<span class="ap-testimonial-upload-empty">尚未上傳</span>';
      }
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
          setPreview(res.url);
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
    var imageUrl = String(fd.get('imageUrl') || '').trim();
    var payload = {
      id: id || undefined,
      name: String(fd.get('namePart') || '').trim(),
      honorific: String(fd.get('honorific') || '小姐').trim(),
      category: String(fd.get('category') || '').trim(),
      city: String(fd.get('city') || '').trim(),
      text: String(fd.get('text') || '').trim(),
      imageUrl: imageUrl,
      isPublished: !!form.querySelector('[name="isPublished"]').checked,
    };
    if (!payload.name) {
      if (errEl) { errEl.textContent = '請填寫姓名'; errEl.hidden = false; }
      return;
    }
    if (!payload.category) {
      if (errEl) { errEl.textContent = '請選擇分類'; errEl.hidden = false; }
      return;
    }
    if (!payload.city) {
      if (errEl) { errEl.textContent = '請選擇城市'; errEl.hidden = false; }
      return;
    }
    if (!payload.imageUrl) {
      if (errEl) { errEl.textContent = '請上傳圖片'; errEl.hidden = false; }
      return;
    }
    if (!payload.text) {
      if (errEl) { errEl.textContent = '請填寫見證內容'; errEl.hidden = false; }
      return;
    }
    if (errEl) errEl.hidden = true;
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
    renderContentReact(body);
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
            '<label class="ap-field ap-field--full"><span>回答（完整）</span><textarea name="answer" class="ap-textarea" rows="8" required>' + esc(isEdit ? f.answer : '') + '</textarea></label>' +
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
      root.setAttribute('aria-busy', 'true');
      root.classList.add('skel-panel');
      root.innerHTML = window.SkeletonUI && window.SkeletonUI.contentShell
        ? window.SkeletonUI.contentShell()
        : '<p class="adx-loading-inline">載入內容中…</p>';
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
        root.removeAttribute('aria-busy');
        return;
      }
      _testimonials = tRes.testimonials || [];
      _faqItems = fRes.items || [];
      _faqCategories = fRes.categories || [];
      _banners = bRes.banners || [];
      _loaded = true;
      root.removeAttribute('aria-busy');
      root.classList.remove('skel-panel');
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

  if (root && window.SkeletonUI && !_loaded && root.querySelector('.skel-line')) {
    root.innerHTML = window.SkeletonUI.contentShell
      ? window.SkeletonUI.contentShell()
      : root.innerHTML;
  }

  var panel = document.getElementById('panel-content');
  if (panel && panel.classList.contains('is-active')) ensureLoaded();
})();
