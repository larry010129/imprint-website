/* 銘印鑽石｜線上估價需求送出
   說明：這支程式在任何有 cfgForm 客製試算表單的頁面自動生效，
   會在「複製我的客製規格」旁邊插入「送出估價需求」按鈕，
   點擊後彈出視窗收集姓名/電話/Email，連同目前試算結果一起存進 Supabase 的 quote_requests。
*/
(function () {
  'use strict';

  document.addEventListener('DOMContentLoaded', function () {
    var form = document.getElementById('cfgForm');
    var actions = document.querySelector('.cfg-actions');
    if (!form || !actions || !window.ImprintConfigurator) return;

    var openBtn = document.createElement('button');
    openBtn.type = 'button';
    openBtn.className = 'btn btn-dark';
    openBtn.id = 'qrOpenBtn';
    openBtn.textContent = '送出估價需求';
    actions.insertBefore(openBtn, actions.firstChild);

    var overlay = document.createElement('div');
    overlay.className = 'qr-modal-overlay';
    overlay.id = 'qrOverlay';
    overlay.innerHTML =
      '<div class="qr-modal" role="dialog" aria-modal="true" aria-labelledby="qrTitle">' +
        '<button type="button" class="qr-modal-close" id="qrClose" aria-label="關閉">&times;</button>' +
        '<h3 id="qrTitle">送出估價需求</h3>' +
        '<p class="qr-modal-sub">留下聯絡方式，顧問會依您目前的規格為您確認正式報價。</p>' +
        '<div class="qr-modal-summary" id="qrSummary"></div>' +
        '<form id="qrForm" novalidate>' +
          '<div class="form-field"><label for="qrName">姓名 <span class="req">*</span></label><input type="text" id="qrName" name="name" autocomplete="name" required></div>' +
          '<div class="form-field"><label for="qrPhone">電話 <span class="req">*</span></label><input type="tel" id="qrPhone" name="phone" autocomplete="tel" required></div>' +
          '<div class="form-field"><label for="qrEmail">Email</label><input type="email" id="qrEmail" name="email" autocomplete="email"></div>' +
          '<button type="submit" class="btn btn-dark" id="qrSubmitBtn">送出估價需求</button>' +
          '<p class="form-msg" id="qrFormMsg" role="status" aria-live="polite"></p>' +
        '</form>' +
      '</div>';
    document.body.appendChild(overlay);

    var qrForm = overlay.querySelector('#qrForm');
    var qrSummary = overlay.querySelector('#qrSummary');
    var qrMsg = overlay.querySelector('#qrFormMsg');
    var qrSubmitBtn = overlay.querySelector('#qrSubmitBtn');
    var qrClose = overlay.querySelector('#qrClose');

    function formatMoney(n) { return 'NT$ ' + n.toLocaleString('en-US'); }

    function renderSummary() {
      var state = window.ImprintConfigurator.getState();
      qrSummary.innerHTML = '';
      if (!state) return;
      var lines = [];
      lines.push(['系列', state.series]);
      if (state.caratLabel) lines.push(['克拉數', state.caratLabel]);
      if (state.color) lines.push(['鑽石顏色', state.color === 'fancy' ? '彩鑽' : '白鑽']);
      if (state.jewelryLabel) lines.push(['飾品選擇', state.jewelryLabel]);
      if (state.quantity > 1) lines.push(['顆數', state.quantity + ' 顆']);
      if (state.engrave) lines.push(['腰圍刻字', state.engrave]);
      lines.push(['系統試算金額', state.estimatedPrice != null ? formatMoney(state.estimatedPrice) : '此規格暫無法試算，請洽顧問']);
      qrSummary.innerHTML = lines.map(function (l) {
        return '<div class="qr-summary-row"><span class="k">' + l[0] + '</span><span class="v">' + l[1] + '</span></div>';
      }).join('');
    }

    function openModal() {
      renderSummary();
      overlay.classList.add('is-open');
      document.body.style.overflow = 'hidden';
    }
    function closeModal() {
      overlay.classList.remove('is-open');
      document.body.style.overflow = '';
    }

    openBtn.addEventListener('click', openModal);
    qrClose.addEventListener('click', closeModal);
    overlay.addEventListener('click', function (e) { if (e.target === overlay) closeModal(); });
    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape' && overlay.classList.contains('is-open')) closeModal();
    });

    qrForm.addEventListener('submit', function (e) {
      e.preventDefault();
      qrMsg.textContent = '';
      qrMsg.className = 'form-msg';

      if (!window.imprintAPI) {
        qrMsg.textContent = '系統連線異常，請直接透過 LINE 聯繫我們。';
        qrMsg.className = 'form-msg is-err';
        return;
      }

      var name = qrForm.name.value.trim();
      var phone = qrForm.phone.value.trim();
      var email = qrForm.email.value.trim();
      if (!name || !phone) {
        qrMsg.textContent = '請填寫姓名與電話。';
        qrMsg.className = 'form-msg is-err';
        return;
      }

      var state = window.ImprintConfigurator.getState() || {};

      qrSubmitBtn.disabled = true;
      qrSubmitBtn.textContent = '送出中…';

      window.imprintAPI
        .submitQuoteRequest({
          name: name,
          phone: phone,
          email: email || null,
          series: state.series || null,
          productType: state.jewelryLabel || state.jewelry || null,
          carat: state.carat || null,
          color: state.color || null,
          shape: state.shape || null,
          metal: state.metal || null,
          ringSize: state.ringSize != null ? state.ringSize : null,
          quantity: state.quantity || 1,
          estimatedPrice: state.estimatedPrice != null ? state.estimatedPrice : null
        })
        .then(function (res) {
          qrSubmitBtn.disabled = false;
          qrSubmitBtn.textContent = '送出估價需求';
          if (res.error) {
            console.error('[quote-request]', res.error);
            qrMsg.textContent = '送出失敗，請稍後再試，或直接透過 LINE 聯繫我們。';
            qrMsg.className = 'form-msg is-err';
            return;
          }
          qrForm.reset();
          qrMsg.textContent = '已收到您的估價需求，顧問會盡快與您聯繫，謝謝！';
          qrMsg.className = 'form-msg is-ok';
          setTimeout(closeModal, 1800);
        });
    });
  });
})();
