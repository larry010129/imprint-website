(function (global) {
  'use strict';
  var M = global.ImprintMVC;
  var Model = global.ImprintModels.Register;
  var View = global.ImprintViews.Register;

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
        var email = e.form.email.value.trim();
        var password = e.form.password.value;

        if (!fullName || !phone || !email || !password) {
          View.setMsg('請完整填寫所有欄位。', 'err');
          return;
        }
        if (password.length < 6) {
          View.setMsg('密碼至少需要 6 碼。', 'err');
          return;
        }

        View.setLoading(true);
        Model.signup({ email: email, password: password, fullName: fullName, phone: phone }).then(function (res) {
          View.setLoading(false);
          if (res.error) {
            View.setMsg('註冊失敗：' + (res.error || '請稍後再試'), 'err');
            return;
          }
          View.setMsg('註冊成功，正在為您登入…', 'ok');
          setTimeout(function () { global.location.href = 'account.html'; }, 800);
        });
      });
    },
  });
})(window);
