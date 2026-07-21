(function (global) {
  'use strict';
  var M = global.ImprintMVC;
  var Model = global.ImprintModels.Login;
  var View = global.ImprintViews.Login;

  function redirectAfterLogin() {
    var next = new URLSearchParams(global.location.search).get('next');
    var target = 'account.html';
    if (next) {
      try {
        var url = new URL(next, global.location.origin);
        if (url.origin === global.location.origin) {
          target = url.pathname + url.search + url.hash;
        }
      } catch (e) {
        // malformed `next` — fall back to the default target
      }
    }
    global.location.href = target;
  }

  M.createController({
    run: function () {
      if (!M.isPage('login')) return;
      var e = View.els();
      if (!e.form) return;

      if (M.api()) {
        Model.getSession().then(function (res) {
          if (res && res.user) redirectAfterLogin();
        });
      }

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
          if (res.error || !res.user) {
            View.setLoading(false);
            var msg = (M.api() && global.imprintAPI && global.imprintAPI.apiErrorMessage)
              ? global.imprintAPI.apiErrorMessage(res)
              : '';
            if (res._httpStatus === 429) {
              View.setMsg('登入失敗：' + (msg || '嘗試次數過多，請稍後再試。'), 'err');
            } else if (res._httpStatus && res._httpStatus >= 500) {
              View.setMsg('登入失敗：伺服器錯誤，請稍後再試或聯絡管理員。', 'err');
            } else if (res.networkError) {
              View.setMsg('登入失敗：系統連線異常，請稍後再試。', 'err');
            } else {
              View.setMsg('登入失敗：' + (msg || 'Email 或密碼不正確。'), 'err');
            }
            return;
          }
          return Model.getSession().then(function (sess) {
            View.setLoading(false);
            if (!sess || !sess.user) {
              View.setMsg('登入成功但無法保存登入狀態，請確認瀏覽器允許 Cookie 後再試。', 'err');
              return;
            }
            View.setMsg('登入成功，跳轉中…', 'ok');
            setTimeout(redirectAfterLogin, 300);
          });
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
