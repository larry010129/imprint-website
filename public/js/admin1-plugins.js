/**
 * admin1 plugins page — list built-in registry, toggle enabled, deep-link 設定.
 */
(function () {
  'use strict';

  var HINT_FALLBACK = { media: 'content' };
  var DESCRIPTIONS = {
    'seo-tools': '頁面 SEO 與搜尋相關設定',
    'media-optimize': '圖片與媒體壓縮優化',
    analytics: '儀表板數據與分析',
    'cms-content': '頁面內容與圖片管理',
    'pricing-tools': '價格與克拉設定',
  };

  var grid = document.getElementById('pluginGrid');
  var statusEl = document.getElementById('pluginStatus');
  if (!grid) return;

  function api() {
    return window.imprintAPI;
  }

  function setStatus(msg, isError) {
    if (!statusEl) return;
    statusEl.textContent = msg || '';
    statusEl.classList.toggle('is-error', !!isError);
  }

  function settingsHref(panelHint) {
    var hint = String(panelHint || '').trim();
    if (!hint) return '';
    if (HINT_FALLBACK[hint]) hint = HINT_FALLBACK[hint];
    return '/admin/' + encodeURIComponent(hint);
  }

  function escapeHtml(s) {
    return String(s == null ? '' : s)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

  function renderCard(plugin) {
    var slug = plugin.slug || '';
    var label = plugin.labelZh || plugin.labelEn || slug;
    var desc = DESCRIPTIONS[slug] || (plugin.labelEn || '內建插件');
    var enabled = !!plugin.enabled;
    var href = settingsHref(plugin.panelHint);
    var article = document.createElement('article');
    article.className = 'a1-plugin-card' + (enabled ? '' : ' is-disabled');
    article.dataset.slug = slug;

    var settingsHtml = href
      ? '<a class="a1-plugin-settings" href="' + escapeHtml(href) + '">設定</a>'
      : '';

    article.innerHTML =
      '<div class="a1-plugin-card-head">' +
        '<h3>' + escapeHtml(label) + '</h3>' +
        '<label class="a1-plugin-toggle">' +
          '<input type="checkbox" data-plugin-toggle' + (enabled ? ' checked' : '') + ' aria-label="啟用 ' + escapeHtml(label) + '">' +
          '<span>' + (enabled ? '已啟用' : '已停用') + '</span>' +
        '</label>' +
      '</div>' +
      '<p>' + escapeHtml(desc) + '</p>' +
      '<div class="a1-plugin-card-foot">' +
        '<code class="a1-plugin-slug">' + escapeHtml(slug) + '</code>' +
        settingsHtml +
      '</div>';

    var input = article.querySelector('[data-plugin-toggle]');
    if (input) {
      input.addEventListener('change', function () {
        onToggle(article, slug, input);
      });
    }
    return article;
  }

  function onToggle(card, slug, input) {
    var next = !!input.checked;
    var labelSpan = card.querySelector('.a1-plugin-toggle span');
    input.disabled = true;
    setStatus('儲存中…');

    var client = api();
    if (!client || !client.admin || typeof client.admin.updatePlugin !== 'function') {
      input.checked = !next;
      input.disabled = false;
      setStatus('無法連線 API', true);
      return;
    }

    client.admin.updatePlugin(slug, { enabled: next }).then(function (res) {
      input.disabled = false;
      if (res.error) {
        input.checked = !next;
        setStatus(res.error, true);
        return;
      }
      var plugin = res.plugin || { enabled: next, slug: slug };
      card.classList.toggle('is-disabled', !plugin.enabled);
      if (labelSpan) labelSpan.textContent = plugin.enabled ? '已啟用' : '已停用';
      setStatus(plugin.enabled ? '已啟用「' + (plugin.labelZh || slug) + '」' : '已停用「' + (plugin.labelZh || slug) + '」');
      if (window.Admin1Shell && typeof window.Admin1Shell.applyPluginNav === 'function') {
        window.Admin1Shell.applyPluginNav([{ slug: slug, enabled: !!plugin.enabled }]);
      }
    });
  }

  function renderList(plugins) {
    grid.innerHTML = '';
    grid.setAttribute('aria-busy', 'false');
    if (!plugins.length) {
      setStatus('尚無內建插件', true);
      return;
    }
    plugins.forEach(function (p) {
      grid.appendChild(renderCard(p));
    });
    setStatus('共 ' + plugins.length + ' 個內建插件');
    if (window.Admin1Shell && typeof window.Admin1Shell.applyPluginNav === 'function') {
      window.Admin1Shell.applyPluginNav(plugins);
    }
  }

  function load() {
    var client = api();
    if (!client || !client.admin || typeof client.admin.getPlugins !== 'function') {
      setStatus('無法連線 API', true);
      grid.setAttribute('aria-busy', 'false');
      return;
    }
    client.admin.getPlugins().then(function (res) {
      if (res.error) {
        setStatus(res.error, true);
        grid.setAttribute('aria-busy', 'false');
        return;
      }
      renderList(Array.isArray(res.plugins) ? res.plugins : []);
    });
  }

  load();
})();
