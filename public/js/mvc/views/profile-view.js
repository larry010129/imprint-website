(function (global) {
  'use strict';
  global.ImprintViews = global.ImprintViews || {};
  global.ImprintViews.Profile = {
    render: function (session, orders) {
      var user = session.user || {};
      var profile = session.profile || {};
      var set = function (id, val) { var el = document.getElementById(id); if (el) el.textContent = val; };
      set('profile-store', profile.store_name || user.store_name || '—');
      set('profile-username', user.username || user.email || '—');
      set('profile-role', user.role === 'admin' ? '管理員' : '店家');
      var pending = (orders || []).filter(function (o) {
        var s = (o.status || '').toLowerCase();
        return s !== 'completed' && s !== 'shipped' && s !== 'cancelled' && s !== 'canceled';
      });
      set('profile-stat-total', String(orders.length));
      set('profile-stat-pending', String(pending.length));
    },
  };
})(window);
