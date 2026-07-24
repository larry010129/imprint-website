(function (global) {
  'use strict';
  var M = global.ImprintMVC;
  var Model = global.ImprintModels.Account;
  var View = global.ImprintViews.Account;

  M.createController({
    run: function () {
      if (!M.isPage('account')) return;
      if (!M.api()) return;

      View.bindCityDistrict();

      M.requireSession('account.html').then(function (res) {
        if (!res) return;
        View.renderProfile(res);
      });

      var e = View.els();
      if (e.form) {
        e.form.addEventListener('submit', function (ev) {
          ev.preventDefault();
          View.setMsg('');
          var payload = View.collectProfile();
          if (!payload.fullName) {
            View.setMsg('請填寫姓名', 'err');
            return;
          }
          if (!payload.phone) {
            View.setMsg('請填寫聯絡電話', 'err');
            return;
          }
          View.setSaving(true);
          Model.updateProfile(payload).then(function (res) {
            View.setSaving(false);
            if (res && res._httpStatus === 401) {
              global.location.href = '/login.html?next=' + encodeURIComponent('/account.html');
              return;
            }
            if (!res || res.error || !res.ok) {
              var msg = (global.imprintAPI && global.imprintAPI.apiErrorMessage)
                ? global.imprintAPI.apiErrorMessage(res)
                : (res && res.error) || '儲存失敗，請稍後再試';
              View.setMsg(msg, 'err');
              return;
            }
            View.setMsg('已儲存帳戶資料', 'ok');
            if (res.profile) {
              View.renderProfile({ user: { email: e.email ? e.email.textContent : '' }, profile: res.profile });
            }
          });
        });
      }

      if (e.logoutBtn) {
        e.logoutBtn.addEventListener('click', function () {
          Model.logout().then(function () {
            global.location.href = '/';
          });
        });
      }
    },
  });
})(window);
