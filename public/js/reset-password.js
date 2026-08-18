(function () {
  'use strict';

  function showMsg(html) {
    var msg = document.getElementById('auth-form-msg');
    if (msg) msg.innerHTML = html;
  }

  function errMsg(text) {
    showMsg('<div class="form-msg is-err">' + text + '</div>');
  }

  function init() {
    var form = document.getElementById('resetPasswordForm');
    if (!form) return;

    form.addEventListener('submit', function (ev) {
      var pwdEl = form.querySelector('[name="password"]');
      var confirmEl = form.querySelector('[name="passwordConfirm"]');
      var pwd = pwdEl ? pwdEl.value : '';
      var confirm = confirmEl ? confirmEl.value : '';
      if (!pwd || !confirm) {
        ev.preventDefault();
        errMsg('請輸入新密碼並再次確認。');
        if (pwdEl && !pwd) pwdEl.focus();
        else if (confirmEl) confirmEl.focus();
        return;
      }
      if (pwd !== confirm) {
        ev.preventDefault();
        errMsg('兩次密碼不一致。');
        if (confirmEl) confirmEl.focus();
        return;
      }
      if (pwd.length < 8) {
        ev.preventDefault();
        errMsg('密碼至少需要 8 碼。');
        if (pwdEl) pwdEl.focus();
      }
    });

    document.body.addEventListener('htmx:beforeSwap', function (ev) {
      var xhr = ev.detail.xhr;
      if (!xhr || xhr.status < 400 || xhr.status >= 600) return;
      var elt = ev.detail.elt;
      if (!elt || !elt.closest) return;
      var target = elt.id === 'resetPasswordForm' ? elt : elt.closest('#resetPasswordForm');
      if (!target || target.getAttribute('hx-target') !== '#auth-form-msg') return;
      ev.detail.shouldSwap = true;
      ev.detail.isError = false;
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
