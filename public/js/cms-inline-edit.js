/* Inline click-to-edit bridge for CMS preview iframe (?inline=1) */
(function () {
  'use strict';
  var root = document.querySelector('[data-cms-inline]');
  if (!root || window.parent === window) return;

  function post(payload) {
    window.parent.postMessage(Object.assign({ source: 'cms-inline' }, payload), window.location.origin);
  }

  // Never leave the page being edited — all pages used to navigate to the same
  // site destinations (nav/CTA), which made every preview feel identical.
  document.addEventListener(
    'click',
    function (e) {
      var link = e.target.closest('a[href]');
      if (!link) return;
      var href = link.getAttribute('href') || '';
      if (!href || href.charAt(0) === '#') return;
      e.preventDefault();
      e.stopPropagation();
    },
    true
  );

  root.addEventListener('click', function (e) {
    var section = e.target.closest('[data-cms-section-id]');
    if (section) {
      post({ type: 'select-section', sectionId: section.getAttribute('data-cms-section-id') });
    }
  });

  root.querySelectorAll('[data-cms-editable]').forEach(function (el) {
    var mode = el.getAttribute('data-cms-editable');
    var prop = el.getAttribute('data-cms-prop');
    if (!prop) return;
    var section = el.closest('[data-cms-section-id]');
    if (!section) return;
    var sectionId = section.getAttribute('data-cms-section-id');

    if (mode === 'text' || mode === 'button') {
      el.setAttribute('contenteditable', 'true');
      if (el.tagName === 'A') {
        el.addEventListener('click', function (ev) {
          ev.preventDefault();
        });
      }
      el.addEventListener('blur', function () {
        var payload = {
          type: 'inline-edit',
          sectionId: sectionId,
          prop: prop,
          value: (el.textContent || '').trim(),
        };
        var hrefProp = el.getAttribute('data-cms-href-prop');
        if (hrefProp && el.tagName === 'A') {
          payload.hrefProp = hrefProp;
          payload.href = el.getAttribute('href') || '';
        }
        var buttonIndex = el.getAttribute('data-cms-button-index');
        if (buttonIndex !== null && buttonIndex !== '') {
          payload.buttonIndex = Number(buttonIndex);
          payload.href = el.getAttribute('href') || '';
        }
        post(payload);
      });
    }

    if (mode === 'image_url' && el.tagName === 'IMG') {
      el.style.cursor = 'pointer';
      el.title = '點擊開啟媒體庫更換圖片';
      el.addEventListener('click', function (ev) {
        ev.preventDefault();
        post({ type: 'edit-image', sectionId: sectionId, prop: prop });
      });
    }
  });
})();
