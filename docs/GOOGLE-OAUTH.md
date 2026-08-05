# Google Sign-In & People API Setup

Member login uses **Google Identity Services (GIS)** with ID tokens. Optional phone/address import uses **Google People API** with a second OAuth consent step.

## 1. OAuth client (Web application)

In [Google Cloud Console → Credentials](https://console.cloud.google.com/apis/credentials):

**Authorized JavaScript origins** (no path, no trailing slash):

| Environment | Origin |
|-------------|--------|
| Local | `http://127.0.0.1:8080` |
| Local alt | `http://localhost:8080` |
| Production | `https://www.imprintdiamond.com` |
| Bare domain (if used) | `https://imprintdiamond.com` |

Set `GOOGLE_CLIENT_ID` in `.env` and on Render to the Web client ID.

## 2. Enable People API

[Enable Google People API](https://console.cloud.google.com/apis/library/people.googleapis.com) in the same project.

## 3. OAuth consent screen scopes

Under **OAuth consent screen → Scopes**, add:

- `.../auth/userinfo.email` (usually included with Sign-In)
- `.../auth/userinfo.profile`
- `.../auth/user.phonenumbers.read` (sensitive)
- `.../auth/user.addresses.read` (sensitive)

Phone/address scopes are **sensitive**. While the app is in **Testing**, only users listed as test users can grant them. Public use requires [Google OAuth verification](https://support.google.com/cloud/answer/9110914).

## 4. What the site collects

| Step | Data | Stored |
|------|------|--------|
| Google Sign-In (ID token) | Email, name, Google account ID | `users`, `profiles.full_name` |
| Optional import (People API) | Phone, address (if user clicks import and grants consent) | `profiles.phone`, `profiles.shipping_*` |
| Session | JWT in `imprint_session` cookie | Browser only |

Email alone does not contain phone or address. Many Google accounts have empty phone/address fields — users can still enter details manually on the account page.

## 5. Local test

```bash
npm run dev
# Open http://127.0.0.1:8080/login.html
```

After Google login, if phone is missing you are redirected to `/account.html?complete=1`. Click **從 Google 帳戶匯入電話與地址** to trigger the People API consent.
