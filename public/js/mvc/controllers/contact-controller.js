(function (global) {
  'use strict';
  var M = global.ImprintMVC;
  var Model = global.ImprintModels.Contact;
  var View = global.ImprintViews.Contact;

  M.createController({
    run: function () {
      if (!M.isPage('contact')) return;
      var e = View.els();
      if (!e.form) return;

      var draft = Model.loadDraft();
      if (draft) {
        View.applyDraft(draft);
        Model.clearDraft();
      }

      e.form.addEventListener('submit', function (ev) {
        ev.preventDefault();
        View.setMsg('');

        if (!M.api()) {
          View.setMsg('系統連線異常，請直接透過 LINE 或電話聯繫我們。', 'err');
          return;
        }

        var name = e.form.name.value.trim();
        var phone = e.form.phone.value.trim();
        var email = e.form.email.value.trim();
        var message = e.form.message.value.trim();

        if (!name || !phone || !message) {
          View.setMsg('請填寫姓名、電話與您的需求。', 'err');
          return;
        }

        View.setLoading(true);
        Model.submit({
          name: name,
          phone: phone,
          email: email || null,
          message: message,
          sourcePage: 'contact.html',
        }).then(function (res) {
          View.setLoading(false);
          if (res.error) {
            View.setMsg('送出失敗，請稍後再試，或直接透過 LINE／電話聯繫我們。', 'err');
            return;
          }
          e.form.reset();
          View.setMsg('已收到您的留言，顧問會盡快與您聯繫，謝謝！', 'ok');
        });
      });
    },
  });
})(window);
