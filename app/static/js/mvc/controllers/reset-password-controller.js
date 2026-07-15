(function (global) {
  'use strict';
  var M = global.ImprintMVC;
  var Model = global.ImprintModels.ResetPassword;
  var View = global.ImprintViews.ResetPassword;

  M.createController({
    run: function () {
      if (!M.isPage('reset-password')) return;
      var e = View.els();
      if (!e.form) return;

      var token = Model.tokenFromUrl();
      if (!token) {
        View.setMsg('重設連結無效，請重新申請忘記密碼。', 'err');
        View.disableForm();
        return;
      }

      e.form.addEventListener('submit', function (ev) {
        ev.preventDefault();
        View.setMsg('');

        if (!M.api()) {
          View.setMsg('系統連線異常，請稍後再試。', 'err');
          return;
        }

        var password = e.form.password.value;
        if (password.length < 6) {
          View.setMsg('密碼至少需要 6 碼。', 'err');
          return;
        }

        View.setLoading(true);
        Model.reset(token, password).then(function (res) {
          View.setLoading(false);
          if (res.error) {
            View.setMsg('重設失敗：' + res.error, 'err');
            return;
          }
          View.setMsg('密碼已重設，請重新登入。', 'ok');
          setTimeout(function () { global.location.href = 'login.html'; }, 1200);
        });
      });
    },
  });
})(window);
