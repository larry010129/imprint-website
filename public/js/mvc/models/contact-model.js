(function (global) {
  'use strict';
  global.ImprintModels = global.ImprintModels || {};
  global.ImprintModels.Contact = {
    submit: function (payload) {
      return global.imprintAPI.submitContact(payload);
    },
    loadDraft: function () {
      try {
        return sessionStorage.getItem('shopInquiryDraft');
      } catch (err) {
        return null;
      }
    },
    clearDraft: function () {
      try {
        sessionStorage.removeItem('shopInquiryDraft');
      } catch (err) { /* ignore */ }
    },
  };
})(window);
