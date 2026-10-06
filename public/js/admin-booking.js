/* 銘印鑽石｜預約諮詢日曆（月曆 + 當日時段，一時段一位） */
(function () {
  'use strict';

  var api = window.imprintAPI;
  if (!api || !api.admin) return;
  var root = document.getElementById('bookingRoot');
  if (!root) return;

  var WEEKDAYS = ['日', '一', '二', '三', '四', '五', '六'];
  /* settings.closedWeekdays uses Python weekday (0=Mon … 6=Sun). */
  var PY_WEEKDAY_LABELS = ['週一', '週二', '週三', '週四', '週五', '週六', '週日'];

  var state = {
    month: '',
    today: '',
    data: null,
    selected: '',
    form: null,
    showSettings: false,
    message: ''
  };
  var ready = false;

  function esc(value) {
    return String(value == null ? '' : value).replace(/[&<>"']/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
    });
  }

  function pad(n) { return n < 10 ? '0' + n : String(n); }
  function monthOf(dateStr) { return dateStr.slice(0, 7); }
  function pyWeekday(dateStr) {
    var p = dateStr.split('-').map(Number);
    return (new Date(p[0], p[1] - 1, p[2]).getDay() + 6) % 7;
  }
  function shiftMonth(month, delta) {
    var p = month.split('-').map(Number);
    var d = new Date(p[0], p[1] - 1 + delta, 1);
    return d.getFullYear() + '-' + pad(d.getMonth() + 1);
  }
  function slotLabel(hhmm, minutes) {
    var p = hhmm.split(':').map(Number);
    var end = p[0] * 60 + p[1] + (minutes || 60);
    return hhmm + '–' + pad(Math.floor(end / 60)) + ':' + pad(end % 60);
  }
  function slotKey(iso) { return iso.slice(0, 10) + ' ' + iso.slice(11, 16); }
  function isoFor(date, hhmm) { return date + 'T' + hhmm + ':00+08:00'; }

  function dayIsOpen(dateStr) {
    var s = state.data.settings;
    return s.closedWeekdays.indexOf(pyWeekday(dateStr)) === -1 && s.blackoutDates.indexOf(dateStr) === -1;
  }

  function bookingsOn(date) {
    return state.data.bookings.filter(function (b) { return b.date === date; });
  }
  function requestedOn(date) {
    return state.data.requested.filter(function (r) { return r.date === date; });
  }

  /* ---------- render ---------- */

  function renderGrid() {
    var p = state.month.split('-').map(Number);
    var first = new Date(p[0], p[1] - 1, 1);
    var days = new Date(p[0], p[1], 0).getDate();
    var cells = '';
    for (var i = 0; i < first.getDay(); i++) cells += '<div class="bk-cell bk-cell--blank"></div>';
    for (var d = 1; d <= days; d++) {
      var date = state.month + '-' + pad(d);
      var booked = bookingsOn(date).length;
      var requested = requestedOn(date).length;
      var open = dayIsOpen(date);
      var cls = 'bk-cell' + (open ? '' : ' is-closed') + (date === state.today ? ' is-today' : '') +
        (date === state.selected ? ' is-selected' : '');
      cells +=
        '<button type="button" class="' + cls + '" data-date="' + date + '">' +
          '<span class="bk-day">' + d + '</span>' +
          (open ? '' : '<span class="bk-tag bk-tag--off">休</span>') +
          (booked ? '<span class="bk-tag bk-tag--booked">已約 ' + booked + '</span>' : '') +
          (requested ? '<span class="bk-tag bk-tag--req">待確認 ' + requested + '</span>' : '') +
        '</button>';
    }
    return (
      '<div class="bk-grid" role="grid">' +
        WEEKDAYS.map(function (w) { return '<div class="bk-head">' + w + '</div>'; }).join('') +
        cells +
      '</div>'
    );
  }

  function bookingCard(b) {
    return (
      '<div class="bk-booking">' +
        '<div><strong>' + esc(b.name) + '</strong>' +
          (b.phone ? ' · ' + esc(b.phone) : '') + (b.email ? ' · ' + esc(b.email) : '') +
          (b.note ? '<div class="bk-note">' + esc(b.note) + '</div>' : '') + '</div>' +
        '<div class="bk-actions">' +
          '<button type="button" class="btn-sm" data-edit="' + esc(b.id) + '">編輯</button>' +
          '<button type="button" class="btn-sm" data-done="' + esc(b.id) + '">' +
            (b.status === 'done' ? '已完成' : '標示完成') + '</button>' +
          '<button type="button" class="btn-sm" data-cancel="' + esc(b.id) + '">取消預約</button>' +
        '</div>' +
      '</div>'
    );
  }

  function renderDay() {
    var date = state.selected;
    if (!date) return '<p class="adx-panel-note">點選月曆上的日期，查看與安排時段。</p>';
    var s = state.data.settings;
    var minutes = state.data.slotMinutes;
    var title = '<h3 class="bk-day-title">' + esc(date) + '（' + PY_WEEKDAY_LABELS[pyWeekday(date)] + '）</h3>';
    if (!dayIsOpen(date)) return title + '<p class="adx-panel-note">這天為公休或未開放。</p>';

    var booked = bookingsOn(date);
    var requested = requestedOn(date);
    var rows = s.slots.map(function (hhmm) {
      var key = date + ' ' + hhmm;
      var b = booked.filter(function (x) { return slotKey(x.slot) === key; })[0];
      var reqs = requested.filter(function (x) { return slotKey(x.slot) === key; });
      var body;
      if (b) {
        body = bookingCard(b);
      } else {
        body =
          reqs.map(function (r) {
            return '<div class="bk-request"><span>待確認：' + esc(r.name) + ' · ' + esc(r.phone) + '</span>' +
              '<button type="button" class="btn-sm btn-primary" data-schedule-request="' +
              esc(r.leadId) + '" data-slot="' + esc(r.slot) + '">安排預約</button></div>';
          }).join('') +
          '<button type="button" class="btn-sm" data-new="' + hhmm + '">＋ 新增預約</button>';
      }
      return '<div class="bk-slot' + (b ? ' is-booked' : '') + '"><div class="bk-slot-time">' +
        slotLabel(hhmm, minutes) + '</div><div class="bk-slot-body">' + body + '</div></div>';
    }).join('');

    var offSlot = requested.filter(function (r) {
      return s.slots.indexOf(r.slot.slice(11, 16)) === -1;
    });
    var offHtml = offSlot.length
      ? '<p class="adx-panel-note">另有不在開放時段內的客人建議：' +
        offSlot.map(function (r) { return esc(r.label) + ' ' + esc(r.name); }).join('、') + '</p>'
      : '';
    return title + rows + offHtml;
  }

  function renderForm() {
    var f = state.form;
    if (!f) return '';
    var s = state.data.settings;
    var opts = s.slots.map(function (hhmm) {
      return '<option value="' + hhmm + '"' + (hhmm === f.time ? ' selected' : '') + '>' +
        slotLabel(hhmm, state.data.slotMinutes) + '</option>';
    }).join('');
    return (
      '<form class="bk-form card" id="bkForm" novalidate>' +
        '<h3>' + (f.id ? '編輯預約' : '新增預約') + '</h3>' +
        '<div class="bk-form-grid">' +
          '<label>日期<input type="date" name="date" value="' + esc(f.date) + '" required></label>' +
          '<label>時段<select name="time">' + opts + '</select></label>' +
          '<label>姓名 *<input type="text" name="name" value="' + esc(f.name) + '" maxlength="80" required></label>' +
          '<label>電話<input type="tel" name="phone" value="' + esc(f.phone) + '" maxlength="40"></label>' +
          '<label class="bk-wide">Email<input type="email" name="email" value="' + esc(f.email) + '" maxlength="120"></label>' +
          '<label class="bk-wide">備註<textarea name="note" rows="2" maxlength="500">' + esc(f.note) + '</textarea></label>' +
        '</div>' +
        '<p class="bk-error" id="bkError" role="alert" hidden></p>' +
        '<div class="ap-form-actions">' +
          '<button type="submit" class="btn-sm btn-primary" id="bkSave">儲存預約</button>' +
          '<button type="button" class="btn-sm" data-form-cancel>取消</button>' +
        '</div>' +
      '</form>'
    );
  }

  function renderSettings() {
    if (!state.showSettings) return '';
    var s = state.data.settings;
    var days = PY_WEEKDAY_LABELS.map(function (label, i) {
      return '<label class="bk-check"><input type="checkbox" name="closed" value="' + i + '"' +
        (s.closedWeekdays.indexOf(i) !== -1 ? ' checked' : '') + '> ' + label + '</label>';
    }).join('');
    return (
      '<form class="bk-form card" id="bkSettings" novalidate>' +
        '<h3>開放時間設定</h3>' +
        '<p class="adx-panel-note">每個時段長 ' + state.data.slotMinutes + ' 分鐘，一個時段只能一位客人預約。</p>' +
        '<div class="bk-form-grid">' +
          '<div class="bk-wide"><span class="bk-label">公休日</span>' + days + '</div>' +
          '<label class="bk-wide">時段開始時間（用逗號分隔，24 小時制）' +
            '<input type="text" name="slots" value="' + esc(s.slots.join(', ')) + '"></label>' +
          '<label class="bk-wide">特別公休日期（每行一個，格式 2026-10-10）' +
            '<textarea name="blackout" rows="3">' + esc(s.blackoutDates.join('\n')) + '</textarea></label>' +
        '</div>' +
        '<p class="bk-error" id="bkSettingsError" role="alert" hidden></p>' +
        '<div class="ap-form-actions">' +
          '<button type="submit" class="btn-sm btn-primary">儲存設定</button>' +
          '<button type="button" class="btn-sm" data-settings-cancel>取消</button>' +
        '</div>' +
      '</form>'
    );
  }

  function render() {
    var d = state.data;
    root.removeAttribute('aria-busy');
    root.classList.remove('skel-panel');
    root.innerHTML =
      '<div class="bk-toolbar">' +
        '<div class="bk-nav">' +
          '<button type="button" class="btn-sm" data-month-prev aria-label="上個月">‹</button>' +
          '<strong class="bk-month">' + esc(state.month) + '</strong>' +
          '<button type="button" class="btn-sm" data-month-next aria-label="下個月">›</button>' +
          '<button type="button" class="btn-sm" data-month-today>今天</button>' +
        '</div>' +
        '<div class="bk-nav">' +
          '<span class="bk-legend"><i class="bk-dot bk-dot--booked"></i>已約 <i class="bk-dot bk-dot--req"></i>待確認（客人建議）</span>' +
          '<button type="button" class="btn-sm" data-settings-open>開放時間設定</button>' +
        '</div>' +
      '</div>' +
      (state.message ? '<p class="bk-flash" role="status">' + esc(state.message) + '</p>' : '') +
      (d ? renderGrid() : '') +
      renderSettings() + renderForm() +
      '<div class="bk-day-panel card">' + (d ? renderDay() : '') + '</div>';
  }

  /* ---------- data ---------- */

  function load(month, keepSelection) {
    state.month = month;
    root.setAttribute('aria-busy', 'true');
    return api.admin.getBookings(month).then(function (res) {
      if (res && res.error) {
        root.innerHTML = '<p class="adx-panel-note">' + esc(res.error) + '</p>';
        return;
      }
      state.data = res;
      state.today = res.today;
      state.month = res.month;
      if (!keepSelection || monthOf(state.selected || '') !== state.month) {
        state.selected = monthOf(res.today) === state.month ? res.today : '';
      }
      render();
    });
  }

  function reload() { return load(state.month, true); }

  function flash(text) {
    state.message = text;
    render();
    setTimeout(function () {
      if (state.message === text) { state.message = ''; render(); }
    }, 3500);
  }

  function showError(id, text) {
    var el = document.getElementById(id);
    if (!el) return;
    el.textContent = text;
    el.hidden = !text;
  }

  /* ---------- actions ---------- */

  function openForm(values) {
    state.showSettings = false;
    state.form = Object.assign(
      { id: '', leadId: '', date: state.selected, time: state.data.settings.slots[0] || '',
        name: '', phone: '', email: '', note: '' },
      values || {}
    );
    render();
    var form = document.getElementById('bkForm');
    if (form && form.scrollIntoView) form.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
  }

  function submitForm(form) {
    var data = new FormData(form);
    var f = state.form;
    var body = {
      slot: isoFor(data.get('date'), data.get('time')),
      name: data.get('name'),
      phone: data.get('phone'),
      email: data.get('email'),
      note: data.get('note')
    };
    if (!data.get('date')) { showError('bkError', '請選擇日期'); return; }
    if (!String(body.name || '').trim()) { showError('bkError', '請填寫姓名'); return; }
    var save = document.getElementById('bkSave');
    if (save) save.disabled = true;
    var request = f.id
      ? api.admin.updateBooking(f.id, body)
      : api.admin.createBooking(Object.assign({ leadId: f.leadId || undefined }, body));
    request.then(function (res) {
      if (res && res.error) {
        showError('bkError', res.error);
        if (save) save.disabled = false;
        return;
      }
      state.form = null;
      state.selected = data.get('date');
      var month = monthOf(state.selected);
      load(month, true).then(function () { flash(f.id ? '已更新預約' : '已新增預約'); });
    });
  }

  function submitSettings(form) {
    var data = new FormData(form);
    var closed = data.getAll('closed').map(Number);
    var slots = String(data.get('slots') || '').split(/[,，\s]+/).filter(Boolean);
    var blackout = String(data.get('blackout') || '').split(/[\s,，]+/).filter(Boolean);
    api.admin.saveBookingSettings({ closedWeekdays: closed, slots: slots, blackoutDates: blackout })
      .then(function (res) {
        if (res && res.error) { showError('bkSettingsError', res.error); return; }
        state.showSettings = false;
        reload().then(function () { flash('已儲存開放時間設定'); });
      });
  }

  function findBooking(id) {
    return state.data.bookings.filter(function (b) { return b.id === id; })[0];
  }

  root.addEventListener('click', function (e) {
    var t = e.target.closest('button');
    if (!t || !root.contains(t)) return;

    if (t.hasAttribute('data-month-prev')) return load(shiftMonth(state.month, -1));
    if (t.hasAttribute('data-month-next')) return load(shiftMonth(state.month, 1));
    if (t.hasAttribute('data-month-today')) { state.selected = ''; return load(''); }
    if (t.hasAttribute('data-settings-open')) { state.form = null; state.showSettings = true; return render(); }
    if (t.hasAttribute('data-settings-cancel')) { state.showSettings = false; return render(); }
    if (t.hasAttribute('data-form-cancel')) { state.form = null; return render(); }

    var date = t.getAttribute('data-date');
    if (date) { state.selected = date; return render(); }

    var time = t.getAttribute('data-new');
    if (time) return openForm({ time: time });

    var leadId = t.getAttribute('data-schedule-request');
    if (leadId) {
      var req = state.data.requested.filter(function (r) {
        return r.leadId === leadId && r.slot === t.getAttribute('data-slot');
      })[0];
      if (req) {
        return openForm({
          leadId: req.leadId, date: req.date, time: req.slot.slice(11, 16),
          name: req.name, phone: req.phone, email: req.email
        });
      }
    }

    var editId = t.getAttribute('data-edit');
    if (editId) {
      var b = findBooking(editId);
      if (b) {
        return openForm({
          id: b.id, date: b.date, time: b.slot.slice(11, 16),
          name: b.name, phone: b.phone, email: b.email, note: b.note
        });
      }
    }

    var doneId = t.getAttribute('data-done');
    if (doneId) {
      var cur = findBooking(doneId);
      var next = cur && cur.status === 'done' ? 'confirmed' : 'done';
      return api.admin.updateBooking(doneId, { status: next }).then(function (res) {
        if (res && res.error) return flash(res.error);
        reload();
      });
    }

    var cancelId = t.getAttribute('data-cancel');
    if (cancelId) {
      if (!window.confirm('確定要取消這筆預約嗎？時段會重新開放。')) return;
      return api.admin.cancelBooking(cancelId).then(function (res) {
        if (res && res.error) return flash(res.error);
        reload().then(function () { flash('已取消預約'); });
      });
    }
  });

  root.addEventListener('submit', function (e) {
    e.preventDefault();
    if (e.target.id === 'bkForm') submitForm(e.target);
    if (e.target.id === 'bkSettings') submitSettings(e.target);
  });

  window.AdminBookingPanel = {
    ensureLoaded: function () {
      if (ready) return;
      ready = true;
      load('');
    },
    /* From the 諮詢名單 lead detail: open the calendar on this customer's first
       requested slot (or today) with the form pre-filled. */
    startFromLead: function (lead) {
      ready = true;
      load('').then(function () {
        var mine = state.data.requested.filter(function (r) { return r.leadId === lead.id; })[0];
        if (mine) {
          state.selected = mine.date;
          if (monthOf(mine.date) !== state.month) {
            return load(monthOf(mine.date), true).then(function () { openLead(mine); });
          }
          return openLead(mine);
        }
        state.selected = state.today;
        openForm({ leadId: lead.id, date: state.today, name: lead.name || '', phone: lead.phone || '', email: lead.email || '' });
      });
      function openLead(mine) {
        openForm({
          leadId: mine.leadId, date: mine.date, time: mine.slot.slice(11, 16),
          name: mine.name, phone: mine.phone, email: mine.email
        });
      }
    }
  };
})();
