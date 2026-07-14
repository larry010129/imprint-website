/* 銘印鑽石｜重設密碼(消耗 Email 中的連結 token) */
(function () {
  'use strict';

  document.addEventListener('DOMContentLoaded', function () {
    var form = document.getElementById('resetPasswordForm');
    if (!form) return;

    var btn = document.getElementById('resetSubmitBtn');
    var msg = document.getElementById('resetFormMsg');

    var token = new URLSearchParams(window.location.search).get('token');
    if (!token) {
      msg.textContent = '重設連結無效，請重新申請忘記密碼。';
      msg.className = 'form-msg is-err';
      form.querySelector('button[type="submit"]').disabled = true;
      return;
    }

    form.addEventListener('submit', function (e) {
      e.preventDefault();
      msg.textContent = '';
      msg.className = 'form-msg';

      if (!window.imprintAPI) {
        msg.textContent = '系統連線異常，請稍後再試。';
        msg.className = 'form-msg is-err';
        return;
      }

      var password = form.password.value;
      if (password.length < 6) {
        msg.textContent = '密碼至少需要 6 碼。';
        msg.className = 'form-msg is-err';
        return;
      }

      btn.disabled = true;
      btn.textContent = '重設中…';

      window.imprintAPI.resetPassword(token, password).then(function (res) {
        btn.disabled = false;
        btn.textContent = '重設密碼';

        if (res.error) {
          msg.textContent = '重設失敗：' + res.error;
          msg.className = 'form-msg is-err';
          return;
        }

        msg.textContent = '密碼已重設，請重新登入。';
        msg.className = 'form-msg is-ok';
        setTimeout(function () { window.location.href = 'login.html'; }, 1200);
      });
    });
  });
})();
