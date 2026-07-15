(function (global) {
  'use strict';
  var M = global.ImprintMVC;
  var Model = global.ImprintModels.Login;
  var View = global.ImprintViews.Login;

  M.createController({
    run: function () {
      if (!M.isPage('login')) return;
      var e = View.els();
      if (!e.form) return;

      e.form.addEventListener('submit', function (ev) {
        ev.preventDefault();
        View.setMsg('');

        if (!M.api()) {
          View.setMsg('系統連線異常，請稍後再試。', 'err');
          return;
        }

        var email = e.form.email.value.trim();
        var password = e.form.password.value;
        if (!email || !password) {
          View.setMsg('請輸入 Email 與密碼。', 'err');
          return;
        }

        View.setLoading(true);
        Model.login(email, password).then(function (res) {
          View.setLoading(false);
          if (res.error) {
            View.setMsg('登入失敗：Email 或密碼不正確。', 'err');
            return;
          }
          View.setMsg('登入成功，跳轉中…', 'ok');
          setTimeout(function () { global.location.href = 'account.html'; }, 500);
        });
      });

      if (e.forgotBtn) {
        e.forgotBtn.addEventListener('click', function () {
          var email = global.prompt('請輸入您註冊時使用的 Email，我們會寄送重設密碼連結：');
          if (!email || !M.api()) return;
          Model.requestReset(email.trim()).then(function () {
            View.setMsg('已寄送重設密碼信件至 ' + email.trim() + '，請至信箱查收。', 'ok');
          });
        });
      }
    },
  });
})(window);
