"""Tests for the Admin notification bell fix (Round 2).

Covers:
- notifyItemsFromSummary builds items from GET /api/admin/notify-summary response:
    * Orders: /admin/orders?order=<num>, validated with ORDER_NO regex
    * Leads messages: /admin/leads?lead=message:<id>, validated with LEAD_ID regex
    * Leads quotes:   /admin/leads?lead=quote:<id>, validated with LEAD_ID regex
    * Invalid or unrecognized types/IDs are rejected
- Rendered notification rows render as <a> links with data-lead and data-order.
- In-place click handler intercepts clicks when the target panel exists on the page.
- Deep links (?lead=, ?order=) parse, validate via regex, route to openNotifyTarget, and clean query params.
- Notification polling (60s) stops permanently (stopNotifyPolling) on 401 or 403 HTTP status.
- api-client sends X-Admin-Background: 1 header so polling does not slide the admin session.
- Error state renders 「通知載入失敗」 with a [重試] button wired to data-notify-retry.
- Counter auto-refresh wired to lead actions (mark-done, delete, mark-spam).
- Asset versions bumped across admin HTML entrypoints.
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SHELL_JS = ROOT / "public" / "js" / "admin1-shell.js"
ADMIN_JS = ROOT / "public" / "js" / "admin.js"
API_CLIENT_JS = ROOT / "public" / "js" / "api-client.js"


def test_notification_bell_rows_render_as_links_with_target_hrefs():
    src = SHELL_JS.read_text(encoding="utf-8")

    # Order rows built from summary.items with ORDER_NO validation
    assert "function notifyItemsFromSummary(summary)" in src
    assert "it.type === 'order'" in src
    assert "if (!ORDER_NO.test(num)) return;" in src
    assert "href: '/admin/orders?order=' + encodeURIComponent(num)" in src
    assert "order: num," in src

    # Lead message & quote rows with LEAD_ID validation
    assert "if (it.type !== 'message' && it.type !== 'quote') return;" in src
    assert "if (!LEAD_ID.test(id)) return;" in src
    assert "var key = it.type + ':' + id;" in src
    assert "href: '/admin/leads?lead=' + encodeURIComponent(key)" in src
    assert "lead: key," in src

    # Rendered element tag is <a> with data-lead and data-order
    assert '<a class="admin1-notify-row" href="' in src
    assert 'data-lead="' in src
    assert 'data-order="' in src


def test_lead_id_and_order_no_validation_regexes():
    src = SHELL_JS.read_text(encoding="utf-8")

    # Verify the regex definitions in admin1-shell.js
    assert "var LEAD_ID = /^[0-9a-f-]{1,64}$/i;" in src
    assert "var ORDER_NO = /^[A-Za-z0-9_-]{1,40}$/;" in src

    lead_re = re.compile(r"^[0-9a-f-]{1,64}$", re.IGNORECASE)
    order_re = re.compile(r"^[A-Za-z0-9_-]{1,40}$")

    # Valid lead IDs
    assert lead_re.match("1")
    assert lead_re.match("c814e7f1-20d6-4896-9e27-b888ed164a03")
    # Invalid lead IDs (SQL injection / XSS payloads)
    assert not lead_re.match("1; drop table contact_messages")
    assert not lead_re.match("<script>")

    # Valid order numbers
    assert order_re.match("ORD-101")
    assert order_re.match("20261104-001")
    # Invalid order numbers
    assert not order_re.match("ORD 101")
    assert not order_re.match("ORD' OR '1'='1")


def test_notification_bell_click_opens_in_place_when_panel_present():
    src = SHELL_JS.read_text(encoding="utf-8")

    # Click delegation on admin1NotifyList
    assert "function bindNotifyList()" in src
    assert "document.getElementById('admin1NotifyList')" in src
    assert "row.getAttribute('data-lead')" in src
    assert "row.getAttribute('data-order')" in src

    # Checks whether this page contains the panel before intercepting
    assert '.side-nav button[data-panel="' in src
    assert "e.preventDefault();" in src
    assert "openNotifyTarget(" in src

    # Handler routing
    assert "function openNotifyTarget(lead, order)" in src
    assert "openPanelWithSearch('orders', 'searchFor', order)" in src
    assert "switchPanel('leads')" in src
    assert "window.AdminLeadsPanel.focus(lead)" in src


def test_deep_link_opens_lead_or_order_from_url_params():
    src = SHELL_JS.read_text(encoding="utf-8")

    assert "function openDeepLink()" in src
    assert "new URLSearchParams(location.search)" in src
    assert "params.get('lead')" in src
    assert "params.get('order')" in src

    # Lead and Order parameter validation
    assert "(leadParts[0] !== 'message' && leadParts[0] !== 'quote') || !LEAD_ID.test(leadParts[1])" in src
    assert "!ORDER_NO.test(order)" in src
    assert "openNotifyTarget(lead, order);" in src

    # URL query parameter cleanup via replaceState so refreshing doesn't reopen
    assert "params.delete('lead');" in src
    assert "params.delete('order');" in src
    assert "history.replaceState" in src

    # Wired to window load
    assert "window.addEventListener('load', openDeepLink);" in src


def test_admin_leads_panel_exposes_focus_and_refreshes_bell_on_actions():
    src = ADMIN_JS.read_text(encoding="utf-8")

    # Window global hook for opening pending or loaded leads
    assert "window.AdminLeadsPanel = {" in src
    assert "openLeadDetail(key)" in src
    assert "consumePendingLead()" in src

    # Refresh bell counter after lead mutation actions
    # 1. deleteLead
    # 2. markSpam
    # 3. markReplied / markProcessed
    count = src.count("window.Admin1Shell.refreshNotifications()")
    assert count >= 3, f"Expected at least 3 refreshNotifications calls in admin.js, got {count}"


def test_notification_error_state_shows_message_and_retry_button():
    src = SHELL_JS.read_text(encoding="utf-8")

    assert "function renderNotifyError()" in src
    assert "通知載入失敗" in src
    assert "admin1-notify-retry" in src
    assert "data-notify-retry" in src

    # Retry click handler triggers loadNotifications
    assert "loadNotifications();" in src


def test_notification_polling_stops_on_auth_failure():
    src = SHELL_JS.read_text(encoding="utf-8")

    assert "function stopNotifyPolling()" in src
    assert "notifyStopped = true;" in src
    assert "clearInterval(notifyTimer);" in src
    assert "res._httpStatus === 401 || res._httpStatus === 403" in src
    assert "stopNotifyPolling();" in src

    # Polling starts only if not stopped
    assert "function startNotifyPolling()" in src
    assert "if (notifyTimer || notifyStopped) return;" in src
    assert "NOTIFY_POLL_MS = 60000" in src
    assert "visibilitychange" in src
    assert "document.visibilityState === 'visible'" in src


def test_api_client_sends_background_header():
    src = API_CLIENT_JS.read_text(encoding="utf-8")

    assert "getNotifySummary: function ()" in src
    assert "request('/api/admin/notify-summary', { headers: { 'X-Admin-Background': '1' } });" in src


def test_admin_html_asset_versions_bumped():
    # admin1.html has the shell and main admin table scripts
    a1 = (ROOT / "admin1.html").read_text(encoding="utf-8")
    assert "api-client.js?v=35" in a1
    assert "admin1-shell.js?v=11" in a1
    assert "admin.js?v=34" in a1
    assert "admin1-shell.css?v=15" in a1

    # admin1-settings.html also mounts the shell
    a1_settings = (ROOT / "admin1-settings.html").read_text(encoding="utf-8")
    assert "api-client.js?v=19" in a1_settings
    assert "admin1-shell.js?v=5" in a1_settings
    assert "admin1-shell.css?v=9" in a1_settings
