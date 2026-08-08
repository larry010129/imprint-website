# Google Sign-In & People API Setup

Member login uses **Google Identity Services (GIS)** with ID tokens (no OAuth redirect for the button). Optional phone/address import uses **Google People API** via a second token-client consent step.

Policy reference: [Google OAuth 2.0 Policies](https://developers.google.com/identity/protocols/oauth2/policies).

## Root cause of `Error 400: origin_mismatch`

Google rejects the GIS request when the browser **Origin** (scheme + host + port) is **not** listed on that OAuth client's **Authorized JavaScript origins**.

This app does **not** hardcode origins. Production canonical host is `https://www.imprintdiamond.com` (`PUBLIC_SITE_URL`). If that OAuth client only has local origins (`127.0.0.1` / `localhost`), live Sign-In fails with `origin_mismatch`.

**www vs apex:** Google treats `https://www.imprintdiamond.com` and `https://imprintdiamond.com` as different origins. Add **both** if users can land on either host (redirect alone does not help GIS — the origin checked is whatever is in the address bar when the button runs). Match the bar string exactly.

Local note: `dev.bat` binds `http://127.0.0.1:8080`. `localhost` and `127.0.0.1` are also different origins — add both if you use both.

## Console checklist (fix `origin_mismatch`)

1. Open [Google Cloud Console → APIs & Services → Credentials](https://console.cloud.google.com/apis/credentials).
2. Open the **OAuth 2.0 Client ID** of type **Web application** whose ID matches `GOOGLE_CLIENT_ID` in `.env` / Render (ends with `.apps.googleusercontent.com`).
3. Under **Authorized JavaScript origins**, add exact origins (**HTTPS for production**, scheme + host only — **no path, no trailing slash, no `/login`**):

| Environment | Origin to add |
|-------------|---------------|
| Production (canonical / `PUBLIC_SITE_URL`) | `https://www.imprintdiamond.com` |
| Production apex (if used or redirected-from) | `https://imprintdiamond.com` |
| Local (`dev.bat`) | `http://127.0.0.1:8080` |
| Local alt (if you type localhost) | `http://localhost:8080` |

4. **Authorized redirect URIs** — main Sign-In uses GIS **credential callback** (`google.accounts.id` → POST `/api/auth/google`), **not** a redirect URI. Adding redirect URIs does **not** fix `origin_mismatch` for this flow. Leave redirect URIs empty unless you later switch to redirect / `ux_mode: 'redirect'`.
5. Save. Wait 1–5 minutes for propagation. Hard-refresh `/login` and retry.
6. Confirm the address bar origin matches a listed origin (copy scheme/host/port from the bar — login page console also logs `[imprint] Google Sign-In page origin:`).

## Env & policy alignment (what we control in code)

| Rule | This repo |
|------|-----------|
| Client ID only in frontend | Yes — `GOOGLE_CLIENT_ID` → template → `google-signin.js` / People import. **No** `GOOGLE_CLIENT_SECRET` anywhere. |
| Separate clients for local vs prod | Recommended: same env var name, different values — Render client lists production HTTPS origins (`www` + apex); local `.env` client lists `127.0.0.1`/`localhost`. |
| HTTPS production JS origins | Use `https://www.imprintdiamond.com` (+ apex if needed). Matches `PUBLIC_SITE_URL`. GIS checks JS origins, not redirect URIs. |
| Minimal scopes | Sign-In: ID token (email/profile via GIS). People import (opt-in only): `user.phonenumbers.read` + `user.addresses.read`. |

Set `GOOGLE_CLIENT_ID` in `.env` (local) and on Render (prod). Never commit `.env` or invent placeholder client IDs.

## 1. OAuth client (Web application)

Create/configure a **Web application** client as in the checklist above.

## 2. Enable People API

[Enable Google People API](https://console.cloud.google.com/apis/library/people.googleapis.com) in the same project (only needed for optional phone/address import).

## 3. OAuth consent screen scopes

Under **OAuth consent screen → Scopes**, add:

- `.../auth/userinfo.email` (usually included with Sign-In)
- `.../auth/userinfo.profile`
- `.../auth/user.phonenumbers.read` (sensitive — import only)
- `.../auth/user.addresses.read` (sensitive — import only)

Phone/address scopes are **sensitive**. While the app is in **Testing**, only listed test users can grant them. Public use requires [Google OAuth verification](https://support.google.com/cloud/answer/9110914).

## 4. What the site collects

| Step | Data | Stored |
|------|------|--------|
| Google Sign-In (ID token) | Email, name, Google account ID | `users`, `profiles.full_name` |
| Optional import (People API) | Phone, address (if user clicks import and grants consent) | `profiles.phone`, `profiles.shipping_*` |
| Session | JWT in `imprint_session` cookie | Browser only |

## 5. Local test (`dev.bat`)

```bat
dev.bat
```

- Server: `http://127.0.0.1:8080` (see `HOST`/`PORT` in `dev.bat`)
- Login: `http://127.0.0.1:8080/login`
- Browser console logs `[imprint] Google Sign-In page origin: …` — that string must appear under Authorized JavaScript origins.

Prefer the `127.0.0.1` URL that `dev.bat` opens. If you switch to `localhost`, add that origin too.

## Code map

| Piece | Location |
|-------|----------|
| Env | `GOOGLE_CLIENT_ID` → `config/settings.py` → Jinja `google_client_id` |
| Login UI | `content/site/templates/pages/login.html` + `public/js/google-signin.js` |
| Verify ID token | `POST /api/auth/google` → `app.auth.verify_google_id_token` |
| People import (optional) | `public/js/google-profile-import.js` → `POST /api/auth/google-enrich` |
