/* 銘印鑽石｜首頁品牌影片管理 */
(function () {
  'use strict';

  var api = window.imprintAPI;
  if (!api || !api.admin) return;

  var root = document.getElementById('featuredVideoRoot');
  if (!root) return;

  var _mounted = false;

  function mount(attempt) {
    if (!window.AdminTables || !window.AdminTables.renderFeaturedVideoEditor) {
      if ((attempt || 0) < 40) {
        setTimeout(function () { mount((attempt || 0) + 1); }, 50);
        return;
      }
      root.innerHTML =
        '<p class="adx-panel-note">品牌影片編輯器尚未載入，請重新整理頁面。</p>';
      return;
    }
    root.removeAttribute('aria-busy');
    root.classList.remove('skel-panel');
    window.AdminTables.renderFeaturedVideoEditor(root, {
      api: {
        getFeaturedVideo: function () {
          return api.admin.getFeaturedVideo();
        },
        saveFeaturedVideo: function (body) {
          return api.admin.saveFeaturedVideo(body);
        },
        syncFeaturedVideo: function () {
          return api.admin.syncFeaturedVideo();
        },
      },
      onRendered: function () {
        _mounted = true;
      },
    });
    _mounted = true;
  }

  function ensureLoaded() {
    if (_mounted && root.getAttribute('data-admin-root') != null) return;
    /* admin-tables.js 按需載入：等 bundle 就緒再掛載，避免超過 mount() 的重試上限。 */
    if (!window.AdminTables && typeof window.__adminLoadTables === 'function') {
      window.__adminLoadTables().then(
        function () { ensureLoaded(); },
        function () { mount(40); }
      );
      return;
    }
    mount();
  }

  window.AdminFeaturedVideoPanel = {
    load: mount,
    ensureLoaded: ensureLoaded,
  };

  document
    .querySelectorAll('.side-nav button[data-panel="featured-video"]')
    .forEach(function (btn) {
      btn.addEventListener('click', ensureLoaded);
    });

  var panel = document.getElementById('panel-featured-video');
  if (panel && panel.classList.contains('is-active')) ensureLoaded();
})();
