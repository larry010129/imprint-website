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
        slotKey:
          editable.getAttribute('data-cms-text') ||
          editable.getAttribute('data-cms-button') ||
          editable.getAttribute('data-cms-slot'),
      });
    },
    true
  );

  document.querySelectorAll('[data-cms-text],[data-cms-button],[data-cms-slot]').forEach(function (el) {
    el.style.outline = '1px dashed rgba(59,130,246,.7)';
    el.style.outlineOffset = '3px';
    el.style.cursor = 'pointer';
    el.title = '點擊編輯';
  });

  document.querySelectorAll('a[href]').forEach(function (link) {
    link.addEventListener('click', function (event) {
      event.preventDefault();
    });
  });

  post({ type: 'ready' });
})();
