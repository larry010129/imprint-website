(function (global) {
  'use strict';
  global.ImprintViews = global.ImprintViews || {};
  global.ImprintViews.Login = {
    els: function () {
      return {
        form: document.getElementById('loginForm'),
        btn: document.getElementById('loginSubmitBtn'),
        msg: document.getElementById('loginFormMsg'),
        forgotBtn: document.getElementById('forgotPwBtn'),
        remember: document.getElementById('loginRemember'),
        email: document.getElementById('loginEmail'),
      };
    },
    setMsg: function (text, type) {
      var e = this.els();
      if (!e.msg) return;
      e.msg.textContent = text || '';
      e.msg.className = 'form-msg' + (type ? ' is-' + type : '');
    },
    setLoading: function (loading) {
      var e = this.els();
      if (!e.btn) return;
      e.btn.disabled = loading;
      e.btn.textContent = loading ? '登入中…' : '登入';
    },
  };
})(window);
