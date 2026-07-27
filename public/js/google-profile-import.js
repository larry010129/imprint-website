/* 銘印鑽石｜Google People API — optional profile import on account page */
(function (global) {
  'use strict';

  var clientId = global.IMPRINT_GOOGLE_CLIENT_ID || '';
  if (!clientId) return;

  function waitForGoogle(cb) {
    var tries = 0;
    (function tick() {
      if (global.google && global.google.accounts && global.google.accounts.oauth2) {
        cb();
        return;
      }
      tries += 1;
      if (tries > 80) return;
      setTimeout(tick, 250);
    })();
  }

  global.imprintGoogleProfileImport = {
    requestImport: function (onDone) {
      waitForGoogle(function () {
        var client = global.google.accounts.oauth2.initTokenClient({
          client_id: clientId,
          scope: [
            'https://www.googleapis.com/auth/user.phonenumbers.read',
            'https://www.googleapis.com/auth/user.addresses.read',
          ].join(' '),
          callback: function (res) {
            if (!res || !res.access_token) {
              onDone({ error: '未取得 Google 授權' });
              return;
            }
            global.imprintAPI.googleEnrichProfile(res.access_token).then(onDone);
          },
        });
        client.requestAccessToken();
      });
    },
  };
})(window);
