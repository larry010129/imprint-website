/** Checkbox multi-select dropdowns for shop catalog filters (OR within each dimension). */
(function (global) {
  'use strict';

  const instances = new Map();
  let openId = null;

  function tr(key, fallback) {
    if (key && global.t) return global.t(key);
    return fallback || '';
  }

  function closePanel(id) {
    const inst = instances.get(id);
    if (!inst) return;
    inst.panel.hidden = true;
    inst.trigger.setAttribute('aria-expanded', 'false');
    if (openId === id) openId = null;
  }

  function closeAllPanels() {
    instances.forEach((_, id) => closePanel(id));
  }

  function defaultLabel(inst) {
    return tr(inst.defaultLabelKey, inst.defaultLabelFallback);
  }

  function formatTriggerLabel(inst) {
    const selected = [...inst.selected];
    if (!selected.length) return defaultLabel(inst);
    const labels = selected.map((v) => inst.optionLabels.get(v) || v);
    if (labels.length <= 2) return labels.join(', ');
    return labels.slice(0, 2).join(', ') + ' +' + (labels.length - 2);
  }

  function syncTriggerLabel(inst) {
    inst.labelEl.textContent = formatTriggerLabel(inst);
    inst.root.classList.toggle('catalog-ms-filter--active', inst.selected.size > 0);
  }

  function emitChange(inst) {
    syncTriggerLabel(inst);
    if (typeof inst.onChange === 'function') inst.onChange();
  }

  function buildOptionRow(inst, opt) {
    const row = document.createElement('label');
    row.className = 'catalog-ms-option';
    row.setAttribute('role', 'option');

    const input = document.createElement('input');
    input.type = 'checkbox';
    input.value = opt.value;
    input.checked = inst.selected.has(opt.value);
    input.addEventListener('change', () => {
      if (input.checked) inst.selected.add(opt.value);
      else inst.selected.delete(opt.value);
      emitChange(inst);
    });

    const text = document.createElement('span');
    text.className = 'catalog-ms-option-text';
    text.textContent = opt.label;
    if (opt.i18n) text.dataset.i18n = opt.i18n;

    row.appendChild(input);
    row.appendChild(text);
    return row;
  }

  function renderOptions(inst) {
    inst.panel.innerHTML = '';
    inst.options.forEach((opt) => {
      inst.optionLabels.set(opt.value, opt.label);
      inst.panel.appendChild(buildOptionRow(inst, opt));
    });
  }

  function upgradeSelect(selectEl, config) {
    if (!selectEl || selectEl.tagName !== 'SELECT') return null;
    const id = selectEl.id;
    if (!id || instances.has(id)) return instances.get(id);

    const allOpt = selectEl.querySelector('option[value=""]');
    const inst = {
      id,
      selected: new Set(),
      optionLabels: new Map(),
      options: [],
      defaultLabelKey: allOpt?.dataset.i18n || config.defaultLabelKey || '',
      defaultLabelFallback: allOpt?.textContent?.trim() || config.defaultLabel || '',
      ariaLabelKey: selectEl.dataset.i18nAria || config.ariaLabelKey || '',
      ariaLabelFallback: selectEl.getAttribute('aria-label') || '',
      onChange: config.onChange || null,
      root: null,
      trigger: null,
      labelEl: null,
      panel: null,
    };

    const root = document.createElement('div');
    root.className = 'catalog-ms-filter';
    root.id = id;
    if (selectEl.className) root.className += ' ' + selectEl.className.replace(/\bcatalog-ms-filter\b/g, '').trim();
    root.hidden = selectEl.hidden;

    const trigger = document.createElement('button');
    trigger.type = 'button';
    trigger.className = 'catalog-ms-trigger';
    trigger.setAttribute('aria-haspopup', 'listbox');
    trigger.setAttribute('aria-expanded', 'false');

    const labelEl = document.createElement('span');
    labelEl.className = 'catalog-ms-label';
    if (inst.defaultLabelKey) labelEl.dataset.i18n = inst.defaultLabelKey;
    labelEl.textContent = defaultLabel(inst);

    const panel = document.createElement('div');
    panel.className = 'catalog-ms-panel';
    panel.setAttribute('role', 'listbox');
    panel.setAttribute('aria-multiselectable', 'true');
    panel.hidden = true;

    trigger.appendChild(labelEl);
    root.appendChild(trigger);
    root.appendChild(panel);

    inst.root = root;
    inst.trigger = trigger;
    inst.labelEl = labelEl;
    inst.panel = panel;

    inst.options = [...selectEl.options]
      .filter((o) => o.value !== '')
      .map((o) => ({
        value: o.value,
        label: o.textContent.trim(),
        i18n: o.dataset.i18n || '',
      }));

    renderOptions(inst);
    syncTriggerLabel(inst);
    applyAria(inst);

    trigger.addEventListener('click', (e) => {
      e.stopPropagation();
      const willOpen = panel.hidden;
      closeAllPanels();
      if (willOpen) {
        panel.hidden = false;
        trigger.setAttribute('aria-expanded', 'true');
        openId = id;
      }
    });

    selectEl.replaceWith(root);
    instances.set(id, inst);
    return inst;
  }

  function applyAria(inst) {
    const label = tr(inst.ariaLabelKey, inst.ariaLabelFallback);
    if (label) {
      inst.root.setAttribute('aria-label', label);
      inst.trigger.setAttribute('aria-label', label);
    }
  }

  function getValues(id) {
    const inst = instances.get(id);
    return inst ? [...inst.selected] : [];
  }

  function clearValues(id) {
    const inst = instances.get(id);
    if (!inst) return;
    inst.selected.clear();
    inst.panel.querySelectorAll('input[type="checkbox"]').forEach((cb) => {
      cb.checked = false;
    });
    emitChange(inst);
  }

  function clearAll() {
    instances.forEach((inst) => {
      inst.selected.clear();
      inst.panel.querySelectorAll('input[type="checkbox"]').forEach((cb) => {
        cb.checked = false;
      });
      syncTriggerLabel(inst);
    });
  }

  function setOptions(id, optionList, config) {
    const inst = instances.get(id);
    if (!inst) return;
    const cfg = config || {};
    const prev = cfg.keepSelection ? new Set(inst.selected) : new Set();

    if (cfg.defaultLabelKey) inst.defaultLabelKey = cfg.defaultLabelKey;
    if (cfg.defaultLabelFallback) inst.defaultLabelFallback = cfg.defaultLabelFallback;
    if (cfg.ariaLabelKey) {
      inst.ariaLabelKey = cfg.ariaLabelKey;
      applyAria(inst);
    }

    inst.options = (optionList || []).map((o) => ({
      value: String(o.value),
      label: o.label,
      i18n: o.i18n || '',
    }));

    inst.selected.clear();
    inst.options.forEach((o) => {
      if (prev.has(o.value)) inst.selected.add(o.value);
    });

    renderOptions(inst);
    syncTriggerLabel(inst);

    if (typeof cfg.hidden === 'boolean') inst.root.hidden = cfg.hidden;
  }

  function refreshAll() {
    instances.forEach((inst) => {
      if (inst.defaultLabelKey) {
        inst.defaultLabelFallback = tr(inst.defaultLabelKey, inst.defaultLabelFallback);
      }
      inst.options.forEach((opt) => {
        if (opt.i18n) opt.label = tr(opt.i18n, opt.label);
      });
      inst.panel.querySelectorAll('.catalog-ms-option').forEach((row, idx) => {
        const opt = inst.options[idx];
        if (!opt) return;
        inst.optionLabels.set(opt.value, opt.label);
        const text = row.querySelector('.catalog-ms-option-text');
        if (text) text.textContent = opt.label;
      });
      applyAria(inst);
      syncTriggerLabel(inst);
    });
  }

  function setHidden(id, hidden) {
    const inst = instances.get(id);
    if (inst) inst.root.hidden = hidden;
  }

  document.addEventListener('click', (e) => {
    if (!openId) return;
    const inst = instances.get(openId);
    if (inst && !inst.root.contains(e.target)) closePanel(openId);
  });

  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') closeAllPanels();
  });

  global.CatalogMultiFilter = {
    upgradeSelect,
    getValues,
    clearValues,
    clearAll,
    setOptions,
    refreshAll,
    setHidden,
    closeAllPanels,
  };
}(window));
