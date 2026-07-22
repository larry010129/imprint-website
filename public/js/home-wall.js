/* Home testimonials wall — fetch /api/testimonials, fallback keeps server HTML if any */
(function () {
  'use strict';

  var root = document.querySelector('[data-home-wall]');
  if (!root) return;

  function esc(s) {
    return String(s == null ? '' : s)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

  function excerpt(text, max) {
    max = max || 88;
    var plain = String(text || '').replace(/^「|」$/g, '');
    return plain.length > max ? plain.slice(0, max) + '…' : plain;
  }

  function avatarChar(name) {
    var s = String(name || '').trim();
    return s ? s.charAt(0) : '銘';
  }

  function cardHtml(t, hidden) {
    var quote = '「' + excerpt(t.text) + '」';
    var role = t.role || ((t.category || '') + (t.city ? '・' + t.city : ''));
    var avatar = t.image_url
      ? '<img class="gh-wall__avatar gh-wall__avatar--img" src="' + esc(t.image_url) + '" alt="" width="40" height="40" loading="lazy">'
      : '<span class="gh-wall__avatar">' + esc(avatarChar(t.name)) + '</span>';
    return (
      '<div class="gh-wall__card"' + (hidden ? ' aria-hidden="true"' : '') + '>' +
        '<p class="gh-wall__quote">' + esc(quote) + '</p>' +
        '<div class="gh-wall__meta">' +
          avatar +
          '<span class="gh-wall__who"><strong>' + esc(t.name) + '</strong><em>' + esc(role) + '</em></span>' +
        '</div>' +
      '</div>'
    );
  }

  function rowHtml(items, dir) {
    var cards = items.map(function (t) { return cardHtml(t, false); }).join('');
    var dup = items.map(function (t) { return cardHtml(t, true); }).join('');
    return (
      '<div class="gh-wall__row" data-dir="' + dir + '">' +
        '<div class="gh-wall__track">' + cards + dup + '</div>' +
      '</div>'
    );
  }

  function render(list) {
    if (!list.length) return;
    var mid = Math.ceil(list.length / 2);
    var left = list.slice(0, mid);
    var right = list.slice(mid);
    root.innerHTML =
      '<div class="gh-wall__rows reveal reveal-d3 is-in">' +
        rowHtml(left, 'left') +
        (right.length ? rowHtml(right, 'right') : '') +
      '</div>';
  }

  var base = (typeof window.IMPRINT_API_BASE === 'string' && window.IMPRINT_API_BASE) || '';
  fetch(base + '/api/testimonials', { credentials: 'same-origin' })
    .then(function (res) { return res.ok ? res.json() : null; })
    .then(function (data) {
      var list = (data && data.testimonials) || [];
      if (list.length) render(list);
    })
    .catch(function () { /* keep SSR/fallback HTML if present */ });
})();
