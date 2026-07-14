/* 銘印鑽石｜會員登入 */
(function () {
  'use strict';

  document.addEventListener('DOMContentLoaded', function () {
    var form = document.getElementById('loginForm');
    if (!form) return;

    var btn = document.getElementById('loginSubmitBtn');
    var msg = document.getElementById('loginFormMsg');
    var forgotBtn = document.getElementById('forgotPwBtn');

    form.addEventListener('submit', function (e) {
      e.preventDefault();
      msg.textContent = '';
      msg.className = 'form-msg';

      if (!window.imprintAPI) {
        msg.textContent = '系統連線異常，請稍後再試。';
        msg.className = 'form-msg is-err';
        return;
      }

      var email = form.email.value.trim();
      var password = form.password.value;

      if (!email || !password) {
        msg.textContent = '請輸入 Email 與密碼。';
        msg.className = 'form-msg is-err';
        return;
      }

      btn.disabled = true;
      btn.textContent = '登入中…';

      window.imprintAPI.login(email, password).then(function (res) {
        btn.disabled = false;
        btn.textContent = '登入';

        if (res.error) {
          console.error('[login]', res.error);
          msg.textContent = '登入失敗：Email 或密碼不正確。';
          msg.className = 'form-msg is-err';
          return;
        }

        msg.textContent = '登入成功，跳轉中…';
        msg.className = 'form-msg is-ok';
        setTimeout(function () { window.location.href = 'account.html'; }, 500);
      });
    });

    if (forgotBtn) {
      forgotBtn.addEventListener('click', function () {
        var email = window.prompt('請輸入您註冊時使用的 Email，我們會寄送重設密碼連結：');
        if (!email) return;
        if (!window.imprintAPI) return;
        window.imprintAPI.requestPasswordReset(email.trim()).then(function () {
          // 後端一律回傳成功(避免洩漏該 Email 是否已註冊)，訊息固定顯示已寄送。
          msg.textContent = '已寄送重設密碼信件至 ' + email.trim() + '，請至信箱查收。';
          msg.className = 'form-msg is-ok';
        });
      });
    }
  });
})();
