/**
 * Checkout TW city/district selects +「同收集瓶寄送地址」sync.
 * Reuses ImprintTaiwanAdminDivisions (same as account buyer address).
 */
(function (global) {
  'use strict';

  function tw() {
    return global.ImprintTaiwanAdminDivisions;
  }

  function districtForPostal(city, postal) {
    var div = tw();
    if (!div || !city || !postal) return '';
    var zip = String(postal).replace(/\D/g, '').slice(0, 3);
    if (!zip) return '';
    var list = div.districtsFor(city);
    var i;
    for (i = 0; i < list.length; i++) {
      if (div.postalFor(city, list[i]) === zip) return list[i];
    }
    return '';
  }

  function resolveCityDistrict(rawCity, postal) {
    var div = tw();
    var normalized = String(rawCity || '').replace(/臺/g, '台').trim();
    var parsed = div
      ? div.parseCityDistrict(normalized)
      : { city: normalized, district: '' };
    var city = parsed.city || normalized;
    var district = parsed.district || districtForPostal(city, postal);
    return { city: city, district: district };
  }

  function fillDistrictOptions(districtEl, city, selectedDistrict) {
    var div = tw();
    if (!districtEl) return;
    var districts = (div && city) ? div.districtsFor(city) : [];
    var html = districts.length
      ? '<option value="">請選擇區／鄉／鎮</option>'
      : '<option value="">請先選縣市</option>';
    var i;
    for (i = 0; i < districts.length; i++) {
      var name = districts[i];
      var zip = div ? div.postalFor(city, name) : '';
      var label = zip ? (zip + ' ' + name) : name;
      html += '<option value="' + name + '">' + label + '</option>';
    }
    districtEl.innerHTML = html;
    districtEl.disabled = !districts.length;
    if (selectedDistrict && districts.indexOf(selectedDistrict) !== -1) {
      districtEl.value = selectedDistrict;
    } else {
      districtEl.value = '';
    }
  }

  function syncPostal(block) {
    var div = tw();
    var cityEl = block.querySelector('[data-tw-city]');
    var districtEl = block.querySelector('[data-tw-district]');
    var postalEl = block.querySelector('[data-tw-postal]');
    if (!div || !cityEl || !districtEl || !postalEl) return;
    var zip = div.postalFor(cityEl.value, districtEl.value);
    if (zip) postalEl.value = zip;
  }

  function bindAddressBlock(block) {
    if (!block || block.getAttribute('data-tw-bound') === '1') return;
    block.setAttribute('data-tw-bound', '1');

    var cityEl = block.querySelector('[data-tw-city]');
    var districtEl = block.querySelector('[data-tw-district]');
    var postalEl = block.querySelector('[data-tw-postal]');
    if (!cityEl || !districtEl) return;

    var initial = resolveCityDistrict(
      cityEl.getAttribute('data-initial-city') || cityEl.value,
      (postalEl && postalEl.value) || districtEl.getAttribute('data-initial-postal') || ''
    );
    if (initial.city && cityEl.querySelector('option[value="' + initial.city + '"]')) {
      cityEl.value = initial.city;
    }
    fillDistrictOptions(districtEl, cityEl.value, initial.district);
    syncPostal(block);

    cityEl.addEventListener('change', function () {
      fillDistrictOptions(districtEl, cityEl.value, '');
      if (postalEl) postalEl.value = '';
      block.dispatchEvent(new CustomEvent('tw-address-change', { bubbles: true }));
    });
    districtEl.addEventListener('change', function () {
      syncPostal(block);
      block.dispatchEvent(new CustomEvent('tw-address-change', { bubbles: true }));
    });
    var streetEl = block.querySelector('[data-tw-street]');
    if (streetEl) {
      streetEl.addEventListener('input', function () {
        block.dispatchEvent(new CustomEvent('tw-address-change', { bubbles: true }));
      });
    }
  }

  function readBlock(block) {
    if (!block) return { city: '', district: '', postal: '', street: '' };
    var cityEl = block.querySelector('[data-tw-city]');
    var districtEl = block.querySelector('[data-tw-district]');
    var postalEl = block.querySelector('[data-tw-postal]');
    var streetEl = block.querySelector('[data-tw-street]');
    return {
      city: cityEl ? cityEl.value.trim() : '',
      district: districtEl ? districtEl.value.trim() : '',
      postal: postalEl ? postalEl.value.trim() : '',
      street: streetEl ? streetEl.value.trim() : '',
    };
  }

  function writeBlock(block, data) {
    if (!block || !data) return;
    var cityEl = block.querySelector('[data-tw-city]');
    var districtEl = block.querySelector('[data-tw-district]');
    var postalEl = block.querySelector('[data-tw-postal]');
    var streetEl = block.querySelector('[data-tw-street]');
    if (cityEl) cityEl.value = data.city || '';
    fillDistrictOptions(districtEl, data.city || '', data.district || '');
    if (postalEl) postalEl.value = data.postal || '';
    if (streetEl) streetEl.value = data.street || '';
    syncPostal(block);
  }

  function setShippingRequired(fields, required) {
    if (!fields) return;
    var controls = fields.querySelectorAll('[data-tw-city], [data-tw-district], [data-tw-street]');
    var i;
    for (i = 0; i < controls.length; i++) {
      controls[i].required = !!required;
    }
  }

  function setSameAsBottleMode(fields, same) {
    if (!fields) return;
    fields.classList.toggle('is-same-as-bottle', !!same);
    fields.setAttribute('aria-hidden', same ? 'true' : 'false');
  }

  function syncBottleToShipping(root) {
    var bottle = root.querySelector('[data-tw-address-block="bottle"]');
    var shipping = root.querySelector('[data-tw-address-block="shipping"]');
    if (!bottle || !shipping) return;
    writeBlock(shipping, readBlock(bottle));
  }

  function updateSameBottleUi(root) {
    var wrap = root.querySelector('[data-same-bottle-wrap]');
    var box = root.querySelector('[data-same-as-bottle]');
    var fields = root.querySelector('[data-delivery-fields]')
      || root.querySelector('[data-tw-address-block="shipping"]');
    var deliveryOn = !!root.querySelector(
      'input[name="fulfillmentMethod"][value="delivery"]:checked'
    );

    if (wrap) wrap.hidden = !deliveryOn;
    if (!fields) return;

    if (!deliveryOn) {
      setSameAsBottleMode(fields, false);
      setShippingRequired(fields, false);
      return;
    }

    if (box && box.checked) {
      syncBottleToShipping(root);
      setSameAsBottleMode(fields, true);
      setShippingRequired(fields, false);
    } else {
      setSameAsBottleMode(fields, false);
      setShippingRequired(fields, true);
    }
  }

  function bindCheckoutRoot(root) {
    if (!root || root.getAttribute('data-checkout-address-bound') === '1') return;
    root.setAttribute('data-checkout-address-bound', '1');

    var blocks = root.querySelectorAll('[data-tw-address-block]');
    var i;
    for (i = 0; i < blocks.length; i++) bindAddressBlock(blocks[i]);

    var box = root.querySelector('[data-same-as-bottle]');
    if (box && !box.hasAttribute('data-user-touched') && !box.checked) {
      var shipping = readBlock(root.querySelector('[data-tw-address-block="shipping"]'));
      var bottle = readBlock(root.querySelector('[data-tw-address-block="bottle"]'));
      var shippingEmpty = !shipping.street && !shipping.city;
      var sameAlready = shipping.city === bottle.city
        && shipping.postal === bottle.postal
        && shipping.street === bottle.street
        && !!bottle.city;
      if (shippingEmpty || sameAlready) box.checked = true;
    }

    updateSameBottleUi(root);

    root.addEventListener('change', function (e) {
      var t = e.target;
      if (!t) return;
      if (t.name === 'fulfillmentMethod' || t.hasAttribute('data-same-as-bottle')) {
        if (t.hasAttribute('data-same-as-bottle')) {
          t.setAttribute('data-user-touched', '1');
        }
        updateSameBottleUi(root);
      }
    });

    root.addEventListener('tw-address-change', function (e) {
      var block = e.target.closest
        ? e.target.closest('[data-tw-address-block]')
        : null;
      if (!block || block.getAttribute('data-tw-address-block') !== 'bottle') return;
      var boxEl = root.querySelector('[data-same-as-bottle]');
      if (boxEl && boxEl.checked) syncBottleToShipping(root);
    });

    var form = root.querySelector('form.checkout-layout');
    if (form) {
      form.addEventListener('submit', function () {
        var boxEl = root.querySelector('[data-same-as-bottle]');
        var deliveryOn = !!root.querySelector(
          'input[name="fulfillmentMethod"][value="delivery"]:checked'
        );
        if (deliveryOn && boxEl && boxEl.checked) syncBottleToShipping(root);
        root.querySelectorAll('[data-tw-address-block]').forEach(syncPostal);
      }, true);
    }
  }

  function init(scope) {
    var root = (scope || document).querySelector
      ? (scope.querySelector
        ? scope.querySelector('[data-checkout-root]') || scope
        : null)
      : null;
    if (scope && scope.hasAttribute && scope.hasAttribute('data-checkout-root')) {
      root = scope;
    }
    if (!root || !root.querySelector) {
      root = document.querySelector('[data-checkout-root]');
    }
    if (!root) return;
    // HTMX re-swap replaces root — always rebind fresh node
    root.removeAttribute('data-checkout-address-bound');
    root.querySelectorAll('[data-tw-address-block]').forEach(function (b) {
      b.removeAttribute('data-tw-bound');
    });
    bindCheckoutRoot(root);
  }

  function onReady() {
    init(document);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', onReady);
  } else {
    onReady();
  }

  document.body.addEventListener('htmx:afterSwap', function (e) {
    var target = e && e.detail && e.detail.target;
    if (!target) return;
    if (target.id === 'htmx-checkout' || target.querySelector('[data-checkout-root]')) {
      init(target);
    }
  });

  global.ImprintCheckoutAddress = { init: init };
})(window);
