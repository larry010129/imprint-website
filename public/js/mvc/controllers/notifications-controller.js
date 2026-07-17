(function (global) {
  'use strict';
  var M = global.ImprintMVC;
  var Model = global.ImprintModels.Notifications;
  var View = global.ImprintViews.Notifications;

  M.createController({
    run: function () {
      if (!M.isPage('notifications')) return;
      M.requireSession('notifications.html').then(function (s) {
        if (!s) return;
        return Model.load();
      }).then(function (data) {
        if (!data) return;
        var groups = data.groups || data.notification_groups || [];
        View.render(groups, data.unread_count || data.unreadCount || 0);
        document.getElementById('notifications-feed')?.addEventListener('click', function (ev) {
          var btn = ev.target.closest('.notification-delete-btn');
          if (!btn || !confirm('確定要刪除此通知嗎？')) return;
          Model.remove(btn.dataset.id).then(function (r) {
            if (r.success) document.getElementById('notification-' + btn.dataset.id)?.remove();
          });
        });
      });
    },
  });
})(window);
