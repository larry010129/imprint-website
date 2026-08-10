/**
 * Toggle expandable order detail rows (history + admin tables).
 */
(function () {
  function labelFor(expanded) {
    if (typeof window.t === 'function') {
      return window.t(expanded ? 'btn_hide_detail' : 'btn_see_detail');
    }
    return expanded ? '收起' : '查看詳情';
  }

  function setButtonState(btn, expanded) {
    btn.setAttribute('aria-expanded', expanded ? 'true' : 'false');
    const span = btn.querySelector('[data-i18n]');
    if (span) {
      span.setAttribute('data-i18n', expanded ? 'btn_hide_detail' : 'btn_see_detail');
      span.textContent = labelFor(expanded);
    } else {
      btn.textContent = labelFor(expanded);
    }
  }

  function toggleDetail(btn) {
    const targetId = btn.dataset.target;
    if (!targetId) return;
    const detailRow = document.getElementById(targetId);
    if (!detailRow) return;

    const willExpand = detailRow.hidden;
    detailRow.hidden = !willExpand;
    setButtonState(btn, willExpand);

    const mainRow = btn.closest('tr.order-row-main');
    if (mainRow) {
      mainRow.classList.toggle('is-detail-open', willExpand);
    }

    if (willExpand) {
      detailRow.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
    }
  }

  function initDetailGalleries() {
    document.querySelectorAll('.order-detail-gallery').forEach(gallery => {
      const mainImg = gallery.querySelector('.order-detail-main-img');
      const thumbBtns = [...gallery.querySelectorAll('.order-detail-thumb-btn')];

      thumbBtns.forEach(btn => {
        btn.addEventListener('click', () => {
          thumbBtns.forEach(b => b.classList.remove('is-active'));
          btn.classList.add('is-active');
          if (mainImg && btn.dataset.image) mainImg.src = btn.dataset.image;
        });
      });
    });
  }

  const ROW_CLICK_IGNORE = 'button, a, input, select, textarea, label';

  document.addEventListener('click', e => {
    const btn = e.target.closest('.order-detail-btn');
    if (btn) {
      e.preventDefault();
      toggleDetail(btn);
      return;
    }

    const row = e.target.closest('tr.order-row-main');
    if (!row || e.target.closest(ROW_CLICK_IGNORE)) return;

    const detailBtn = row.querySelector('.order-detail-btn');
    if (detailBtn) toggleDetail(detailBtn);
  });

  document.addEventListener('keydown', e => {
    if (e.key !== 'Enter' && e.key !== ' ') return;
    const row = e.target.closest('tr.order-row-main');
    if (!row) return;
    e.preventDefault();
    const detailBtn = row.querySelector('.order-detail-btn');
    if (detailBtn) toggleDetail(detailBtn);
  });

  document.addEventListener('langchange', () => {
    document.querySelectorAll('.order-detail-btn').forEach(btn => {
      const expanded = btn.getAttribute('aria-expanded') === 'true';
      setButtonState(btn, expanded);
    });
  });

  // Image fallback for order thumbnails/previews (replaces inline onerror
  // attributes, which a nonce-based CSP blocks). Error events don't bubble,
  // so listen in the capture phase.
  document.addEventListener('error', e => {
    const img = e.target;
    if (!(img instanceof HTMLImageElement)) return;
    const fallback = img.dataset.fallback;
    if (fallback && img.src !== new URL(fallback, location.href).href) {
      img.src = fallback;
    }
  }, true);

  initDetailGalleries();

  // History tabs: prefer HTMX reload (SQL-paged active tab). Client toggle only when no hx-get.
  document.addEventListener('click', e => {
    const btn = e.target.closest('.member-tab');
    if (!btn) return;
    if (btn.hasAttribute('hx-get') || btn.getAttribute('hx-get') != null) return;
    const root = btn.closest('#htmx-history') || btn.closest('.member-app');
    if (!root) return;
    const tab = btn.dataset.tab;
    if (!tab) return;
    root.querySelectorAll('.member-tab').forEach(b => {
      const on = b === btn;
      b.classList.toggle('is-active', on);
      b.setAttribute('aria-selected', on ? 'true' : 'false');
    });
    root.querySelectorAll('.member-tab-panel').forEach(panel => {
      const show = panel.dataset.tabPanel === tab;
      panel.hidden = !show;
    });
  });

  // Pickup schedule: rebuild slots for selected date; sync hidden ISO field.
  // Do NOT toggle option.hidden — Chromium often won't show options again after
  // hiding (e.g. today-at-night → all past → switch to future date still empty).
  // Hardcoded fallback matches app.orders.PICKUP_SLOT_STARTS (skip lunch 12:00).
  const PICKUP_SLOT_FALLBACK = [
    ['09:00', '09:00–10:00'],
    ['10:00', '10:00–11:00'],
    ['11:00', '11:00–12:00'],
    ['13:00', '13:00–14:00'],
    ['14:00', '14:00–15:00'],
    ['15:00', '15:00–16:00'],
    ['16:00', '16:00–17:00'],
    ['17:00', '17:00–18:00'],
    ['18:00', '18:00–19:00'],
    ['19:00', '19:00–20:00'],
  ].map(([value, label]) => ({ value, label }));

  function taipeiNowParts() {
    const parts = new Intl.DateTimeFormat('en-CA', {
      timeZone: 'Asia/Taipei',
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
      hourCycle: 'h23',
    }).formatToParts(new Date());
    const get = type => (parts.find(p => p.type === type) || {}).value || '';
    let hour = Number(get('hour'));
    if (hour === 24) hour = 0;
    return {
      date: `${get('year')}-${get('month')}-${get('day')}`,
      minutes: (hour || 0) * 60 + (Number(get('minute')) || 0),
    };
  }

  function slotStartMinutes(value) {
    const [hh, mm] = String(value || '').split(':').map(Number);
    return (hh || 0) * 60 + (mm || 0);
  }

  function parseSlotList(raw) {
    if (!raw) return [];
    try {
      const parsed = typeof raw === 'string' ? JSON.parse(raw) : raw;
      if (!Array.isArray(parsed)) return [];
      return parsed
        .filter(s => s && s.value)
        .map(s => ({ value: String(s.value), label: String(s.label || s.value) }));
    } catch (err) {
      return [];
    }
  }

  function pickupSlotCatalog(form, select) {
    if (select._pickupSlotCatalog && select._pickupSlotCatalog.length) {
      return select._pickupSlotCatalog;
    }
    let catalog = [];

    const tmpl = form && form.querySelector('[data-pickup-slot-catalog]');
    if (tmpl) {
      const raw = (tmpl.textContent || tmpl.innerHTML || '').trim();
      catalog = parseSlotList(raw);
    }
    if (!catalog.length) {
      catalog = parseSlotList(select.getAttribute('data-pickup-slot-options'));
    }
    if (!catalog.length) {
      catalog = [...select.options]
        .filter(opt => opt.value)
        .map(opt => ({ value: opt.value, label: (opt.textContent || '').trim() }));
    }
    if (!catalog.length) {
      catalog = PICKUP_SLOT_FALLBACK.slice();
    }
    // Never cache an empty list — empty [] is truthy and would stick forever.
    if (catalog.length) select._pickupSlotCatalog = catalog;
    return catalog;
  }

  function syncPickupForm(form) {
    if (!form) return;
    const dateInput = form.querySelector('[data-pickup-date]');
    const slotSelect = form.querySelector('[data-pickup-slot]');
    const hidden = form.querySelector('[data-pickup-preferred-at]');
    if (!dateInput || !slotSelect) return;

    const selectedDate = dateInput.value || '';
    const now = taipeiNowParts();
    const isToday = Boolean(selectedDate && selectedDate === now.date);
    const prev = slotSelect.value;
    const catalog = pickupSlotCatalog(form, slotSelect);
    const placeholderOpt = [...slotSelect.options].find(opt => !opt.value);
    const placeholderLabel =
      (placeholderOpt && (placeholderOpt.textContent || '').trim()) || '請選擇時段';

    slotSelect.innerHTML = '';
    const placeholder = document.createElement('option');
    placeholder.value = '';
    placeholder.setAttribute('data-i18n', 'history_pickup_slot_placeholder');
    placeholder.textContent = placeholderLabel;
    slotSelect.appendChild(placeholder);

    let selectedStillValid = false;
    catalog.forEach(slot => {
      if (isToday && slotStartMinutes(slot.value) <= now.minutes) return;
      const opt = document.createElement('option');
      opt.value = slot.value;
      opt.textContent = slot.label;
      if (slot.value === prev) {
        opt.selected = true;
        selectedStillValid = true;
      }
      slotSelect.appendChild(opt);
    });

    if (!selectedStillValid) slotSelect.value = '';

    if (hidden) {
      hidden.value =
        selectedDate && slotSelect.value
          ? `${selectedDate}T${slotSelect.value}`
          : '';
    }
  }

  function htmxSwapRoot(e) {
    const d = e && e.detail;
    return (d && (d.target || d.elt)) || (e && e.target) || document;
  }

  function refreshPickupForms(root) {
    const scope = root && root.querySelectorAll ? root : document;
    scope.querySelectorAll('[data-pickup-schedule-form]').forEach(syncPickupForm);
  }

  function onPickupFieldEvent(e) {
    const form = e.target.closest('[data-pickup-schedule-form]');
    if (!form) return;
    if (
      e.target.matches('[data-pickup-date]') ||
      e.target.matches('[data-pickup-slot]')
    ) {
      syncPickupForm(form);
    }
  }

  document.addEventListener('change', onPickupFieldEvent);
  document.addEventListener('input', onPickupFieldEvent);

  document.addEventListener('submit', e => {
    const form = e.target.closest('[data-pickup-schedule-form]');
    if (!form) return;
    syncPickupForm(form);
  }, true);

  document.body.addEventListener('htmx:afterSwap', e => {
    refreshPickupForms(htmxSwapRoot(e));
  });
  document.body.addEventListener('htmx:afterSettle', e => {
    refreshPickupForms(htmxSwapRoot(e));
  });

  refreshPickupForms(document);

  // Member order cancel dialog (outside #htmx-history so swaps keep it).
  // Dropdown fills always-visible「取消原因說明」; submit trimmed textarea.
  const cancelDialog = document.getElementById('member-order-cancel-dialog');
  const cancelForm = document.getElementById('member-order-cancel-form');
  const cancelOrderId = document.getElementById('member-cancel-order-id');
  const cancelPreset = document.getElementById('member-cancel-preset');
  const cancelReason = document.getElementById('member-cancel-reason');
  const cancelOrderLabel = document.getElementById('member-cancel-order-label');

  function applyCancelPreset() {
    if (!cancelPreset || !cancelReason) return;
    const v = cancelPreset.value;
    cancelReason.value = !v || v === '其他' ? '' : v;
  }

  function openMemberCancelDialog(orderId, orderNumber) {
    if (!cancelDialog || !cancelOrderId || !orderId) return;
    cancelOrderId.value = orderId;
    if (cancelPreset) cancelPreset.selectedIndex = 0;
    if (cancelReason) cancelReason.value = '';
    if (cancelOrderLabel) {
      if (orderNumber) {
        cancelOrderLabel.hidden = false;
        cancelOrderLabel.textContent = '訂單編號：' + orderNumber;
      } else {
        cancelOrderLabel.hidden = true;
        cancelOrderLabel.textContent = '';
      }
    }
    if (typeof cancelDialog.showModal === 'function') {
      cancelDialog.showModal();
    }
  }

  function closeMemberCancelDialog() {
    if (!cancelDialog) return;
    if (typeof cancelDialog.close === 'function') cancelDialog.close();
  }

  document.addEventListener('click', e => {
    const openBtn = e.target.closest('.member-order-cancel-btn');
    if (openBtn) {
      e.preventDefault();
      e.stopPropagation();
      openMemberCancelDialog(
        openBtn.getAttribute('data-order-id'),
        openBtn.getAttribute('data-order-number') || ''
      );
      return;
    }
    if (e.target.closest('[data-member-cancel-close]')) {
      e.preventDefault();
      closeMemberCancelDialog();
    }
  });

  cancelPreset?.addEventListener('change', applyCancelPreset);

  cancelForm?.addEventListener('submit', e => {
    if (!cancelOrderId?.value || !cancelPreset?.value) {
      e.preventDefault();
      return;
    }
    const text = (cancelReason?.value || '').trim();
    if (!text) {
      e.preventDefault();
      cancelReason?.focus();
      return;
    }
    if (cancelReason) cancelReason.value = text;
  });

  document.body.addEventListener('htmx:afterSwap', e => {
    const target = htmxSwapRoot(e);
    if (target && target.id === 'htmx-history') {
      closeMemberCancelDialog();
    }
  });
})();
