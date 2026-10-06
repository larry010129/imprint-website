(function () {
  var rows = document.getElementById('cSlotRows');
  var addBtn = document.getElementById('cSlotAdd');
  if (!rows || !addBtn) return;
  var MAX = 3;
  var today = new Date().toISOString().slice(0, 10); /* native-input fallback only */
  var WEEKDAYS = ['日', '一', '二', '三', '四', '五', '六'];
  /* Pristine row used by 「新增時段選項」 (captured before any upgrade). */
  var template = rows.children[0].cloneNode(true);
  /* Opening rules + taken slots from the admin 預約諮詢日曆; null = use the static form. */
  var avail = null;
  var openCal = null;

  function pad(n) { return n < 10 ? '0' + n : String(n); }
  function parseDate(s) { var p = s.split('-').map(Number); return new Date(p[0], p[1] - 1, p[2]); }
  function fmtDate(d) { return d.getFullYear() + '-' + pad(d.getMonth() + 1) + '-' + pad(d.getDate()); }
  function addDays(s, n) { var d = parseDate(s); d.setDate(d.getDate() + n); return fmtDate(d); }
  /* Python-style weekday: 0 = Monday … 6 = Sunday (matches the admin settings). */
  function pyWeekday(s) { return (parseDate(s).getDay() + 6) % 7; }

  function syncRow(row) {
    var sel = row.querySelector('.contact-slot-row__select');
    var otherOpt = row.querySelector('.contact-slot-row__other-opt');
    var other = row.querySelector('.contact-slot-row__other-input');
    var isOther = sel.options[sel.selectedIndex] === otherOpt;
    other.style.display = isOther ? '' : 'none';
    otherOpt.value = isOther && other.value.trim() ? ('其他：' + other.value.trim()) : '其他';
  }

  function refreshAddBtn() {
    addBtn.style.display = rows.children.length >= MAX ? 'none' : '';
  }

  /* ---------- availability ---------- */

  function slotLabel(hhmm) {
    var p = hhmm.split(':').map(Number);
    var end = p[0] * 60 + p[1] + avail.slotMinutes;
    var h2 = Math.floor(end / 60) % 24;
    return (p[0] < 12 ? '上午 ' : '下午 ') + (p[0] % 12 || 12) + ':' + pad(p[1]) +
      '～' + (h2 % 12 || 12) + ':' + pad(end % 60);
  }
  function isBooked(date, hhmm) { return avail.booked.indexOf(date + ' ' + hhmm) !== -1; }
  function isPast(date, hhmm) { return date === avail.today && hhmm <= avail.nowTime; }
  function hasOpenSlot(date) {
    return avail.slots.some(function (s) { return !isBooked(date, s) && !isPast(date, s); });
  }
  /* 'open' | 'closed' (公休) | 'full' (已額滿) | 'off' (past / too far) */
  function dayState(date) {
    if (date < avail.today || date > addDays(avail.today, avail.windowDays)) return 'off';
    if (avail.closedWeekdays.indexOf(pyWeekday(date)) !== -1 ||
        avail.blackoutDates.indexOf(date) !== -1) return 'closed';
    return hasOpenSlot(date) ? 'open' : 'full';
  }

  function rebuildTimes(row) {
    var sel = row.querySelector('.contact-slot-row__select');
    var date = row.querySelector('input[name=preferred_date]').value;
    var keep = sel.value;
    var html = '<option value="">尚未決定／稍後再約</option>';
    if (date && dayState(date) !== 'closed' && dayState(date) !== 'off') {
      avail.slots.forEach(function (s) {
        if (isPast(date, s)) return;
        var label = slotLabel(s);
        var booked = isBooked(date, s);
        html += '<option value="' + label + '"' + (booked ? ' disabled' : '') + '>' +
          label + (booked ? '（已額滿）' : '') + '</option>';
      });
    }
    html += '<option value="其他" class="contact-slot-row__other-opt">其他</option>';
    sel.innerHTML = html;
    var chosen = null;
    Array.prototype.forEach.call(sel.options, function (o) {
      if (!chosen && !o.disabled && o.value === keep) chosen = o;
    });
    if (!chosen && keep.indexOf('其他') === 0) chosen = sel.querySelector('.contact-slot-row__other-opt');
    sel.selectedIndex = chosen ? chosen.index : 0;
    syncRow(row);
  }

  /* ---------- date picker ---------- */

  function closeCal() {
    if (!openCal) return;
    openCal.el.remove();
    openCal.btn.setAttribute('aria-expanded', 'false');
    openCal = null;
  }

  function toggleCal(row, btn, dateInput) {
    if (openCal && openCal.btn === btn) { closeCal(); return; }
    closeCal();
    var view = (dateInput.value || avail.today).slice(0, 7);
    var minMonth = avail.today.slice(0, 7);
    var maxMonth = addDays(avail.today, avail.windowDays).slice(0, 7);
    var el = document.createElement('div');
    el.className = 'cs-cal';
    el.setAttribute('role', 'dialog');
    el.setAttribute('aria-label', '選擇預約日期');
    row.appendChild(el);
    openCal = { el: el, btn: btn };
    btn.setAttribute('aria-expanded', 'true');

    function draw() {
      var p = view.split('-').map(Number);
      var first = new Date(p[0], p[1] - 1, 1);
      var days = new Date(p[0], p[1], 0).getDate();
      var html =
        '<div class="cs-cal-head">' +
          '<button type="button" class="cs-cal-nav" data-nav="-1" aria-label="上個月"' + (view <= minMonth ? ' disabled' : '') + '>‹</button>' +
          '<span>' + p[0] + ' 年 ' + p[1] + ' 月</span>' +
          '<button type="button" class="cs-cal-nav" data-nav="1" aria-label="下個月"' + (view >= maxMonth ? ' disabled' : '') + '>›</button>' +
        '</div><div class="cs-cal-grid">';
      WEEKDAYS.forEach(function (w, i) {
        html += '<div class="cs-cal-wd' + (i === 0 || i === 6 ? ' is-weekend' : '') + '">' + w + '</div>';
      });
      for (var b = 0; b < first.getDay(); b++) html += '<div></div>';
      for (var d = 1; d <= days; d++) {
        var date = view + '-' + pad(d);
        var state = dayState(date);
        var wd = parseDate(date).getDay();
        var cls = 'cs-day' + (wd === 0 || wd === 6 ? ' is-weekend' : '') +
          (date === avail.today ? ' is-today' : '') +
          (date === dateInput.value ? ' is-selected' : '');
        var title = state === 'closed' ? '公休' : state === 'full' ? '已額滿' : '';
        html += '<button type="button" class="' + cls + '" data-date="' + date + '"' +
          (state === 'open' ? '' : ' disabled') + (title ? ' title="' + title + '"' : '') + '>' + d + '</button>';
      }
      html += '</div><p class="cs-cal-legend">灰色斜線＝公休或已額滿，無法選擇</p>';
      el.innerHTML = html;
    }

    el.addEventListener('click', function (e) {
      e.stopPropagation();
      var nav = e.target.closest('[data-nav]');
      if (nav && !nav.disabled) {
        var q = view.split('-').map(Number);
        var next = new Date(q[0], q[1] - 1 + Number(nav.getAttribute('data-nav')), 1);
        view = next.getFullYear() + '-' + pad(next.getMonth() + 1);
        draw();
        return;
      }
      var day = e.target.closest('[data-date]');
      if (!day || day.disabled) return;
      var picked = day.getAttribute('data-date');
      dateInput.value = picked;
      btn.querySelector('.cs-date-text').textContent =
        picked + '（週' + WEEKDAYS[parseDate(picked).getDay()] + '）';
      btn.classList.remove('is-empty');
      rebuildTimes(row);
      closeCal();
      btn.focus();
    });
    draw();
  }

  document.addEventListener('click', function (e) {
    if (openCal && !openCal.el.contains(e.target) && e.target !== openCal.btn) closeCal();
  });
  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape' && openCal) { var b = openCal.btn; closeCal(); b.focus(); }
  });

  /* Swap the native date input for the picker once availability is known. */
  function upgradeRow(row) {
    if (!avail || row.getAttribute('data-cs')) return;
    row.setAttribute('data-cs', '1');
    var dateInput = row.querySelector('input[name=preferred_date]');
    dateInput.type = 'hidden';
    dateInput.value = '';
    var btn = document.createElement('button');
    btn.type = 'button';
    btn.className = 'cs-date-btn is-empty';
    btn.setAttribute('aria-haspopup', 'dialog');
    btn.setAttribute('aria-expanded', 'false');
    btn.innerHTML = '<span class="cs-date-text">選擇日期</span><span aria-hidden="true">▾</span>';
    dateInput.parentNode.insertBefore(btn, dateInput);
    btn.addEventListener('click', function (e) {
      e.stopPropagation();
      toggleCal(row, btn, dateInput);
    });
    rebuildTimes(row);
  }

  Array.prototype.forEach.call(rows.querySelectorAll('input[type=date]'), function (d) { d.min = today; });
  Array.prototype.forEach.call(rows.querySelectorAll('.contact-slot-row'), syncRow);

  rows.addEventListener('change', function (e) {
    if (e.target.classList.contains('contact-slot-row__select')) syncRow(e.target.closest('.contact-slot-row'));
  });
  rows.addEventListener('input', function (e) {
    if (e.target.classList.contains('contact-slot-row__other-input')) syncRow(e.target.closest('.contact-slot-row'));
  });

  addBtn.addEventListener('click', function () {
    if (rows.children.length >= MAX) return;
    var clone = template.cloneNode(true);
    var nativeDate = clone.querySelector('input[type=date]');
    if (nativeDate) nativeDate.min = today;
    var remove = document.createElement('button');
    remove.type = 'button';
    remove.className = 'contact-slot-row__remove';
    remove.textContent = '－ 移除';
    remove.addEventListener('click', function () {
      if (openCal && clone.contains(openCal.el)) closeCal();
      clone.remove();
      refreshAddBtn();
    });
    clone.appendChild(remove);
    rows.appendChild(clone);
    upgradeRow(clone);
    syncRow(clone);
    refreshAddBtn();
  });

  /* form.reset() (after a successful send) does not clear the picker's hidden value. */
  var formEl = document.getElementById('contactForm');
  if (formEl) {
    formEl.addEventListener('reset', function () {
      setTimeout(function () {
        closeCal();
        Array.prototype.forEach.call(rows.children, function (row) {
          if (row.getAttribute('data-cs')) {
            row.querySelector('input[name=preferred_date]').value = '';
            row.querySelector('.cs-date-text').textContent = '選擇日期';
            row.querySelector('.cs-date-btn').classList.add('is-empty');
            rebuildTimes(row);
          }
          syncRow(row);
        });
      }, 0);
    });
  }

  refreshAddBtn();

  /* Load the admin's opening rules; on any failure the static form keeps working. */
  fetch('/api/booking-availability', { credentials: 'same-origin', cache: 'no-store' })
    .then(function (r) { return r.ok ? r.json() : Promise.reject(new Error('availability ' + r.status)); })
    .then(function (data) {
      if (!data || !Array.isArray(data.slots) || !data.slots.length) return;
      avail = data;
      Array.prototype.forEach.call(rows.children, upgradeRow);
    })
    .catch(function () { /* keep native date input + static time list */ });
})();
