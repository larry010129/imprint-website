/* Estimated foreign-currency amounts under the calculator's NT$ prices.
   Only /en, /ja and /ko; Chinese pages show nothing. */
(function () {
  'use strict';
  var LOCALES = {
    en: { code: 'USD', symbol: 'US$',
      note: 'Converted amounts are estimates only. Prices are set in NT$.' },
    ja: { code: 'JPY', symbol: '¥',
      note: '外貨の金額は目安です。価格の基準はNT$です。' },
    ko: { code: 'KRW', symbol: '₩',
      note: '외화 금액은 참고용이며, 기준 가격은 NT$입니다.' }
  };
  var config = window.IMPRINT_I18N && LOCALES[window.IMPRINT_I18N.lang];
  if (!config) return;

  var rate = null;
  var amounts = { total: null, diamond: null };
  var nodes = {};
  var credit = null;

  // translate="no" stops i18n-client.js from translating our own text again.
  function create(tag, className) {
    var el = document.createElement(tag);
    el.className = className;
    el.setAttribute('translate', 'no');
    el.hidden = true;
    return el;
  }

  function mount() {
    var hero = document.getElementById('hero-price');
    var diamond = document.getElementById('sum-diamond-price');
    var disclaimer = document.querySelector('.hero-price-disclaimer');
    // Never show converted amounts without the credit link the rate source requires.
    if (!hero || !diamond || !disclaimer) return false;
    nodes.total = create('span', 'fx-estimate fx-estimate--total');
    hero.appendChild(nodes.total);
    nodes.diamond = create('span', 'fx-estimate fx-estimate--row');
    diamond.parentElement.appendChild(nodes.diamond);

    credit = create('p', 'fx-credit');
    credit.appendChild(document.createTextNode(config.note + ' '));
    var link = document.createElement('a');
    link.href = 'https://www.exchangerate-api.com';
    link.target = '_blank';
    link.rel = 'noopener';
    link.textContent = 'Rates By Exchange Rate API';
    credit.appendChild(link);
    disclaimer.parentElement.insertBefore(credit, disclaimer.nextSibling);
    return true;
  }

  function render() {
    if (!credit) return;
    var any = false;
    Object.keys(nodes).forEach(function (key) {
      var amount = Number(amounts[key]);
      var show = !!rate && amount > 0;
      nodes[key].hidden = !show;
      nodes[key].textContent = show
        ? '≈ ' + config.symbol + Math.round(amount * rate).toLocaleString('en-US')
        : '';
      any = any || show;
    });
    credit.hidden = !any;
  }

  // Called by shop.js with NT$ numbers; null hides that estimate.
  window.shopFxEstimate = {
    show: function (total, diamond) {
      amounts.total = total;
      amounts.diamond = diamond;
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
