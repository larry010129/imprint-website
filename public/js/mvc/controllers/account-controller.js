(function (global) {
  'use strict';
  var M = global.ImprintMVC;
  var Model = global.ImprintModels.Account;
  var View = global.ImprintViews.Account;

  function importMessage(res) {
    if (!res || res.error) {
      return (global.imprintAPI && global.imprintAPI.apiErrorMessage)
        ? global.imprintAPI.apiErrorMessage(res)
        : (res && res.error) || '匯入失敗，請稍後再試';
    }
    if (res.message) return res.message;
    var parts = [];
    if (res.imported && res.imported.phone) parts.push('電話');
    if (res.imported && res.imported.address) parts.push('地址');
    if (parts.length) return '已從 Google 匯入：' + parts.join('、') + '。';
    return 'Google 帳戶中沒有可匯入的資料，請手動填寫。';
  }

  M.createController({
    run: function () {
      if (!M.isPage('account')) return;
      if (!M.api()) return;

      View.bindCityDistrict();

      M.requireSession('/account').then(function (res) {
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
              global.location.href = '/login?next=' + encodeURIComponent('/account');
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
            Model.getSession().then(function (session) {
              if (session && session.user) View.renderProfile(session);
            });
          });
        });
      }

      if (e.googleImportBtn && global.imprintGoogleProfileImport) {
        e.googleImportBtn.addEventListener('click', function () {
          View.setMsg('');
          View.setGoogleImportLoading(true);
          global.imprintGoogleProfileImport.requestImport(function (res) {
            View.setGoogleImportLoading(false);
            if (res && res._httpStatus === 401) {
              global.location.href = '/login?next=' + encodeURIComponent('/account?complete=1');
              return;
            }
            if (!res || res.error || !res.ok) {
              View.setMsg(importMessage(res), 'err');
              return;
            }
            View.setMsg(importMessage(res), res.imported && (res.imported.phone || res.imported.address) ? 'ok' : 'info');
            Model.getSession().then(function (session) {
              if (session && session.user) View.renderProfile(session);
            });
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
