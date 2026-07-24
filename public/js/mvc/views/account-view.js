(function (global) {
  'use strict';
  var M = global.ImprintMVC;

  function tw() {
    return global.ImprintTaiwanAdminDivisions;
  }

  global.ImprintViews = global.ImprintViews || {};
  global.ImprintViews.Account = {
    els: function () {
      return {
        form: document.getElementById('accountProfileForm'),
        name: document.getElementById('accName'),
        phone: document.getElementById('accPhone'),
        email: document.getElementById('accEmail'),
        postal: document.getElementById('accPostal'),
        city: document.getElementById('accCity'),
        district: document.getElementById('accDistrict'),
        address: document.getElementById('accAddress'),
        msg: document.getElementById('accountProfileMsg'),
        saveBtn: document.getElementById('accountSaveBtn'),
        ordersList: document.getElementById('ordersList'),
        logoutBtn: document.getElementById('logoutBtn'),
      };
    },
    fillCityOptions: function (selectedCity) {
      var e = this.els();
      var div = tw();
      if (!e.city || !div) return;
      div.fillCitySelect(e.city, selectedCity || '');
    },
    fillDistrictOptions: function (city, selectedDistrict) {
      var e = this.els();
      if (!e.district) return;
      var div = tw();
      var districts = (div && city) ? div.districtsFor(city) : [];
      var html = districts.length
        ? '<option value="">請選擇區／鄉／鎮</option>'
        : '<option value="">請先選縣市</option>';
      districts.forEach(function (name) {
        var zip = div && div.postalFor ? div.postalFor(city, name) : '';
        var label = zip ? (zip + ' ' + name) : name;
        html += '<option value="' + name + '">' + label + '</option>';
      });
      e.district.innerHTML = html;
      e.district.disabled = !districts.length;
      if (selectedDistrict && districts.indexOf(selectedDistrict) !== -1) {
        e.district.value = selectedDistrict;
      } else {
        e.district.value = '';
      }
    },
    syncPostalFromDistrict: function () {
      var e = this.els();
      var div = tw();
      if (!e.postal || !e.city || !e.district || !div) return;
      var zip = div.postalFor(e.city.value, e.district.value);
      if (zip) e.postal.value = zip;
    },
    bindCityDistrict: function () {
      var self = this;
      var e = this.els();
      if (!e.city || e.city.getAttribute('data-district-bound') === '1') return;
      e.city.setAttribute('data-district-bound', '1');
      if (!e.city.options || e.city.options.length <= 1) {
        this.fillCityOptions('');
      }
      e.city.addEventListener('change', function () {
        self.fillDistrictOptions(e.city.value, '');
      });
      if (e.district) {
        e.district.addEventListener('change', function () {
          self.syncPostalFromDistrict();
        });
      }
    },
    renderProfile: function (session) {
      var e = this.els();
      this.bindCityDistrict();
      if (e.email) e.email.textContent = (session.user && session.user.email) || '-';
      var profile = session.profile || {};
      if (e.name) e.name.value = profile.full_name || '';
      if (e.phone) e.phone.value = profile.phone || '';
      if (e.postal) e.postal.value = profile.shipping_postal || '';
      if (e.address) e.address.value = profile.shipping_address || '';

      var parsed = tw()
        ? tw().parseCityDistrict(profile.shipping_city || '')
        : { city: '', district: '' };
      this.fillCityOptions(parsed.city);
      this.fillDistrictOptions(parsed.city, parsed.district);
    },
    setMsg: function (text, type) {
      var e = this.els();
      if (!e.msg) return;
      if (!text) {
        e.msg.hidden = true;
        e.msg.textContent = '';
        e.msg.className = 'account-profile-msg';
        return;
      }
      e.msg.hidden = false;
      e.msg.textContent = text;
      e.msg.className = 'account-profile-msg is-' + (type || 'info');
    },
    setSaving: function (saving) {
      var e = this.els();
      if (!e.saveBtn) return;
      e.saveBtn.disabled = !!saving;
      e.saveBtn.textContent = saving ? '儲存中…' : '儲存帳戶資料';
    },
    collectProfile: function () {
      var e = this.els();
      var city = e.city ? e.city.value.trim() : '';
      var district = e.district ? e.district.value.trim() : '';
      var shippingCity = tw()
        ? tw().joinCityDistrict(city, district)
        : (city + district);
      return {
        fullName: e.name ? e.name.value.trim() : '',
        phone: e.phone ? e.phone.value.trim() : '',
        shippingPostal: e.postal ? e.postal.value.trim() : '',
        shippingCity: shippingCity,
        shippingAddress: e.address ? e.address.value.trim() : '',
      };
    },
    renderOrders: function (orders, statusLabel) {
      var e = this.els();
      if (!e.ordersList) return;
      if (!orders.length) {
        e.ordersList.innerHTML = '<p style="color:var(--ink-faint);font-size:13px;">目前沒有訂單紀錄。若您已下單，會由顧問為您建立訂單，建立後即可在此查詢進度。</p>';
        return;
      }
      e.ordersList.innerHTML = orders.map(function (o) {
        return (
          '<div class="order-row">' +
            '<div class="num">' + M.escapeHtml(o.order_number) + '</div>' +
            '<div class="status">目前狀態：' + M.escapeHtml(statusLabel(o.status)) + '</div>' +
            (o.product_name || o.product_type ? '<div style="font-size:13px;color:var(--ink-soft);margin-top:6px;">' + M.escapeHtml((o.series ? o.series + '・' : '') + (o.product_name || o.product_type)) + '</div>' : '') +
            (o.status_note ? '<div style="font-size:12.5px;color:var(--ink-faint);margin-top:6px;">' + M.escapeHtml(o.status_note) + '</div>' : '') +
          '</div>'
        );
      }).join('');
    },
    renderOrdersError: function () {
      var e = this.els();
      if (e.ordersList) {
        e.ordersList.innerHTML = '<p style="color:var(--ink-faint);font-size:13px;">載入訂單失敗，請稍後重新整理頁面。</p>';
      }
    },
  };
})(window);
