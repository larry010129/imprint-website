(function (global) {
  'use strict';
  global.ImprintViews = global.ImprintViews || {};
  global.ImprintViews.Contact = {
    els: function () {
      return {
        form: document.getElementById('contactForm'),
        btn: document.getElementById('contactSubmitBtn'),
        msg: document.getElementById('contactFormMsg'),
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
      e.btn.textContent = loading ? '送出中…' : '送出留言';
    },
    applyDraft: function (draft) {
      var e = this.els();
      if (draft && e.form && e.form.message && !e.form.message.value.trim()) {
        e.form.message.value = draft;
      }
    },
  };
})(window);
