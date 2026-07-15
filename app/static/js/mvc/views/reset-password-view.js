(function (global) {
  'use strict';
  global.ImprintViews = global.ImprintViews || {};
  global.ImprintViews.ResetPassword = {
    els: function () {
      return {
        form: document.getElementById('resetPasswordForm'),
        btn: document.getElementById('resetSubmitBtn'),
        msg: document.getElementById('resetFormMsg'),
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
      e.btn.textContent = loading ? '重設中…' : '重設密碼';
    },
    disableForm: function () {
      var e = this.els();
      if (e.form) {
        var submit = e.form.querySelector('button[type="submit"]');
        if (submit) submit.disabled = true;
      }
    },
  };
})(window);
