/* 銘印鑽石｜插件狀態：未開啟的插件從側邊欄隱藏（伺服器端 API 另外擋下）。 */
(function () {
  'use strict';

  /* sidebar panel key -> plugin slug (only plugins that can be switched) */
  var PANEL_PLUGIN = { booking: 'booking' };
  var states = null;

  function isOn(slug) {
    /* Unknown (still loading / request failed) counts as on: the server is the real gate. */
    return !states || !states[slug] || states[slug] === 'on';
  }

  function apply() {
    Object.keys(PANEL_PLUGIN).forEach(function (panel) {
      var off = !isOn(PANEL_PLUGIN[panel]);
      /* A class, not [hidden]: admin-nav-visibility.js rewrites [hidden] on its own schedule. */
      document.querySelectorAll('.side-nav button[data-panel="' + panel + '"]').forEach(function (btn) {
        btn.classList.toggle('plugin-off', off);
      });
    });
  }

  window.AdminPluginState = {
    isOn: isOn,
    refresh: load
  };

  function load() {
    return fetch('/api/admin/plugins', { credentials: 'include' })
      .then(function (res) { return res.ok ? res.json() : null; })
      .then(function (data) {
        if (data && data.plugins) {
          states = data.plugins;
          apply();
          document.dispatchEvent(new CustomEvent('admin-plugins-ready', { detail: states }));
        }
      })
      .catch(function () { /* keep everything visible; the server still enforces */ });
  }

  load();
})();
