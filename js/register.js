/* 銘印鑽石｜會員註冊 */
(function () {
  'use strict';

  document.addEventListener('DOMContentLoaded', function () {
    var form = document.getElementById('registerForm');
    if (!form) return;

    var btn = document.getElementById('registerSubmitBtn');
    var msg = document.getElementById('registerFormMsg');

    form.addEventListener('submit', function (e) {
      e.preventDefault();
      msg.textContent = '';
      msg.className = 'form-msg';

      if (!window.imprintAPI) {
        msg.textContent = '系統連線異常，請稍後再試。';
        msg.className = 'form-msg is-err';
        return;
      }

      var fullName = form.fullName.value.trim();
      var phone = form.phone.value.trim();
      var email = form.email.value.trim();
      var password = form.password.value;

      if (!fullName || !phone || !email || !password) {
        msg.textContent = '請完整填寫所有欄位。';
        msg.className = 'form-msg is-err';
        return;
      }
      if (password.length < 6) {
        msg.textContent = '密碼至少需要 6 碼。';
        msg.className = 'form-msg is-err';
        return;
      }

      btn.disabled = true;
      btn.textContent = '註冊中…';

      window.imprintAPI.signup({ email: email, password: password, fullName: fullName, phone: phone }).then(function (res) {
        btn.disabled = false;
        btn.textContent = '建立會員帳號';

        if (res.error) {
          console.error('[register]', res.error);
          msg.textContent = '註冊失敗：' + (res.error || '請稍後再試');
          msg.className = 'form-msg is-err';
          return;
        }

        msg.textContent = '註冊成功，正在為您登入…';
        msg.className = 'form-msg is-ok';
        setTimeout(function () { window.location.href = 'account.html'; }, 800);
      });
    });
  });
})();
