(function (global) {
  'use strict';
  var M = global.ImprintMVC;
  var Model = global.ImprintModels.Register;
  var View = global.ImprintViews.Register;

  var EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

  M.createController({
    run: function () {
      if (!M.isPage('register')) return;
      var e = View.els();
      if (!e.form) return;

      e.form.addEventListener('submit', function (ev) {
        ev.preventDefault();
        View.setMsg('');

        if (!M.api()) {
          View.setMsg('系統連線異常，請稍後再試。', 'err');
          return;
        }

        var fullName = e.form.fullName.value.trim();
        var phone = e.form.phone.value.trim();
        var emailField = e.form.querySelector('.form-field-email');
        var email = global.ImprintAuthShell.composeEmail(emailField);
        var password = e.form.password.value;
        var storeName = (e.form.storeName && e.form.storeName.value.trim()) || '';
        var inviteCode = (e.form.inviteCode && e.form.inviteCode.value.trim()) || '';

        if (!fullName || !phone || !email || !password) {
          View.setMsg('請完整填寫所有欄位。', 'err');
          return;
        }
        if (!EMAIL_RE.test(email)) {
          View.setMsg('請輸入有效的 Email。', 'err');
          return;
        }
        if (password.length < 6) {
          View.setMsg('密碼至少需要 6 碼。', 'err');
          return;
        }

        View.setLoading(true);
        Model.signup({
          email: email,
          password: password,
          fullName: fullName,
          phone: phone,
          storeName: storeName || undefined,
          inviteCode: inviteCode || undefined,
        }).then(function (res) {
          if (res.error || !res.user) {
            View.setLoading(false);
            View.setMsg('註冊失敗：' + (res.error || '請稍後再試'), 'err');
            return;
          }
          return global.imprintAPI.getSession().then(function (sess) {
            View.setLoading(false);
            if (!sess || !sess.user) {
              View.setMsg('註冊成功但無法保存登入狀態，請至登入頁重新登入。', 'err');
              return;
            }
            View.setMsg('註冊成功，正在為您登入…', 'ok');
            setTimeout(function () { global.location.href = 'account.html'; }, 300);
          });
        });
      });
    },
  });
})(window);
