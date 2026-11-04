# Admin Notification Bell QA & Manual Verification Checklist

**Feature**: Admin Notification Bell Fix  
**Scope**: `public/js/admin1-shell.js`, `public/js/admin.js`, and `admin1*.html`  
**Automated test**: `tests/test_admin_notify_bell.py`

---

## 1. Automated Test Run Command

Run only the new notification bell test file:
```powershell
$env:PYTHONPATH = "C:\Users\e1253\Documents\imprint-website"
& "C:\Users\e1253\.openmausbot\workspaces\a5ec1047-c158-49e4-bc88-d69e020a417d\.venv-imprint\Scripts\python.exe" -m pytest tests/test_admin_notify_bell.py -v
```

---

## 2. Browser Execution Feasibility Assessment

- **Automated Browser (Playwright / Selenium)**:
  - Playwright python package is present in `.venv-imprint`, but the Chromium browser binaries are not installed on this machine (`playwright install` has not been run; executable missing at `AppData\Local\ms-playwright`).
  - Running end-to-end browser tests via headless Chromium is therefore **not feasible out of the box** without downloading ~150MB of Playwright binaries.
  - Furthermore, real admin session auth requires a valid session token/cookie (`imprint_session`).

- **Manual Browser Run**:
  - Fully feasible via the user's desktop browser (Edge / Chrome) once the local dev server is running (`python -m uvicorn app:app --port 8080`).

---

## 3. Manual Verification Checklist

### Case A: Notification Rows Render as Canonical Links
1. Sign in as Admin and navigate to `/admin`.
2. Inspect the notification bell dropdown list (`#admin1NotifyList`).
3. Verify each notification item is rendered as an `<a>` element (not `<button>`):
   - **Order rows**: `href="/admin/orders?order=<order_number>"` with attribute `data-order="<order_number>"`.
   - **Lead message rows**: `href="/admin/leads?lead=message:<id>"` with attribute `data-lead="message:<id>"`.
   - **Lead quote rows**: `href="/admin/leads?lead=quote:<id>"` with attribute `data-lead="quote:<id>"`.
4. Right-click any row and verify "Open in new tab" opens the expected URL directly.

### Case B: In-Place Click Navigation (When Panel Exists on Same Page)
1. On `/admin` (where both `orders` and `leads` panels exist):
   - Left-click a **Lead notification**:
     - Verify page does not do a full reload (`preventDefault`).
     - Verify it switches to the **諮詢名單 (Leads)** panel.
     - Verify the exact lead's 詳情 modal (`openLeadDetail`) opens immediately.
   - Left-click an **Order notification**:
     - Verify page switches to the **訂單管理 (Orders)** panel.
     - Verify the search input (`searchFor`) is populated with that order number and filters the list.

### Case C: Cross-Page Navigation (e.g. from `/admin/settings`)
1. Navigate to `/admin/settings` (or any secondary page where the leads/orders table panels are not mounted).
2. Open the notification bell and left-click a lead or order item.
3. Verify the browser naturally navigates via the link `href` to `/admin/leads?lead=...` or `/admin/orders?order=...`.
4. Upon arrival at `/admin`, verify the exact lead modal or order search is automatically opened/applied on page load.

### Case D: Deep Links from Address Bar
1. Paste directly into the browser URL bar:
   - `http://127.0.0.1:8080/admin/leads?lead=message:<existing_id>`
   - Verify the leads panel loads and automatically pops the modal for that lead.
   - Verify `?lead=...` is stripped from the URL bar via `history.replaceState` so refreshing doesn't re-trigger unwanted modals.
2. Paste:
   - `http://127.0.0.1:8080/admin/orders?order=<existing_order_number>`
   - Verify the orders panel loads and filters to that order number.

### Case E: Counter Auto-Refresh on Lead Mutations
1. In the **諮詢名單** panel, perform each of the following:
   - Click **標記已處理 (Mark processed/replied)**.
   - Click **標記為垃圾 (Mark spam)**.
   - Click **刪除 (Delete lead)**.
2. Verify that after each action succeeds, the notification bell badge count immediately updates via `Admin1Shell.refreshNotifications()`.

### Case F: Error State and Retry Button
1. Disconnect network or simulate an error response for `/api/admin/notifications` or `/api/admin/leads`.
2. Open the bell dropdown.
3. Verify the list renders: `「通知載入失敗」` alongside a `[重試]` button (`data-notify-retry`).
4. Re-enable network / restore API and click `[重試]`.
5. Verify notifications reload properly without refreshing the whole page.

### Case G: Auto-Polling & Visibility Handling
1. Keep the `/admin` tab open in background or switch to another tab for >60s.
2. In another tab or database, create a new contact message or order.
3. Switch back to the `/admin` tab.
4. Verify the `visibilitychange` listener immediately fetches the latest notifications and updates the bell badge.
