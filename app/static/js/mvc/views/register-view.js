(function (global) {
  'use strict';
  global.ImprintViews = global.ImprintViews || {};
  global.ImprintViews.Register = {
    els: function () {
      return {
        form: document.getElementById('registerForm'),
        btn: document.getElementById('registerSubmitBtn'),
        msg: document.getElementById('registerFormMsg'),
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
      e.btn.textContent = loading ? '註冊中…' : '建立會員帳號';
    },
  };
})(window);
