/* Estimated foreign-currency amount beside the calculator's NT$ total.
   Only /en, /ja and /ko; Chinese pages show nothing. */
(function () {
  'use strict';
  var LOCALES = {
    en: { code: 'USD', symbol: 'US$' },
    ja: { code: 'JPY', symbol: '¥' },
    ko: { code: 'KRW', symbol: '₩' }
  };
  var config = window.IMPRINT_I18N && LOCALES[window.IMPRINT_I18N.lang];
  if (!config) return;

  var rate = null;
  var total = null;
  var node = null;

  function mount() {
    var hero = document.getElementById('hero-price');
    if (!hero) return false;
    node = document.createElement('span');
    node.className = 'fx-estimate';
    // translate="no" stops i18n-client.js from translating our own text again.
    node.setAttribute('translate', 'no');
    node.hidden = true;
    hero.appendChild(node);
    return true;
  }

  function render() {
    if (!node) return;
    var show = !!rate && Number(total) > 0;
    node.hidden = !show;
    node.textContent = show
      ? '≈ ' + config.symbol + Math.round(total * rate).toLocaleString('en-US')
      : '';
  }

  // Called by shop.js with the NT$ total; null hides the estimate.
  window.shopFxEstimate = {
    show: function (value) {
      total = value;
      render();
    }
  };

  if (!mount()) return;
  fetch('/i18n/fx.json')
    .then(function (response) { return response.ok ? response.json() : null; })
    .then(function (data) {
      var value = data && data.rates && Number(data.rates[config.code]);
      if (value > 0) {
        rate = value;
        render();
      }
    })
    .catch(function () { /* estimates stay hidden; NT$ prices are unaffected */ });
})();
