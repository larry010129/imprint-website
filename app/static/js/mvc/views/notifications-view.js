(function (global) {
  'use strict';
  var M = global.ImprintMVC;
  global.ImprintViews = global.ImprintViews || {};
  global.ImprintViews.Notifications = {
    render: function (groups, unread) {
      var feed = document.getElementById('notifications-feed');
      var empty = document.getElementById('notifications-empty');
      var loading = document.getElementById('notifications-loading');
      var pill = document.getElementById('notifications-unread-pill');
      if (loading) loading.classList.add('hidden');
      if (pill && unread > 0) { pill.textContent = unread + ' 則未讀'; pill.classList.remove('hidden'); }
      if (!groups.length) { M.show(empty, true); return; }
      feed.innerHTML = groups.map(function (pair) {
        var group = pair[0] || pair.group;
        var notes = pair[1] || pair.notes || [];
        var label = group === 'today' ? '今天' : group === 'yesterday' ? '昨天' : group;
        return '<div class="member-notify-group"><h2>' + M.escapeHtml(label) + '</h2><ul class="member-notify-list">' +
          notes.map(function (n) {
            return '<li class="member-notify-item' + ((n.show_unread || n.unread) ? ' member-notify-item--unread' : '') + '" id="notification-' + n.id + '">' +
              '<span aria-hidden="true">🔔</span><div><div class="member-notify-item__title">' + M.escapeHtml(n.order_summary || '系統通知') + '</div>' +
              '<p class="member-notify-item__msg">' + M.escapeHtml(n.message || '') + '</p>' +
              '<time class="member-notify-item__time">' + M.escapeHtml(n.created_at_display || n.created_at || '') + '</time></div>' +
              '<button type="button" class="btn-text notification-delete-btn" data-id="' + n.id + '">刪除</button></li>';
          }).join('') + '</ul></div>';
      }).join('');
      M.show(feed, true);
    },
  };
})(window);
