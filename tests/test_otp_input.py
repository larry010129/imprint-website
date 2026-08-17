"""OTP input helper — page wiring and digit sync semantics."""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import pytest
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / ".env")
os.environ.setdefault("STARTUP_SEED_MODE", "off")

ROOT = Path(__file__).resolve().parents[1]
OTP_JS = ROOT / "public" / "js" / "otp-input.js"
FP_JS = ROOT / "public" / "js" / "forgot-password.js"


@pytest.fixture(scope="module")
def client():
    from fastapi.testclient import TestClient

    from app import create_app

    with TestClient(create_app()) as c:
        yield c


def test_otp_input_js_caches_group_api_and_read_digits():
    text = OTP_JS.read_text(encoding="utf-8")
    assert "_imprintOtpApi" in text
    assert "readDigitsFromGroup" in text
    assert "readDigits: readDigitsFromGroup" in text
    assert "data-otp-target" in text or "syncHiddenTarget" in text


def test_forgot_password_page_wires_otp_hidden_target(client):
    resp = client.get("/forgot-password")
    assert resp.status_code == 200
    assert 'data-otp-target="fpCodeHidden"' in resp.text
    assert 'id="fpCodeHidden"' in resp.text
    assert "otp-input.js?v=3" in resp.text
    assert "forgot-password.js?v=5" in resp.text


@pytest.mark.skipif(shutil.which("node") is None, reason="node not installed")
def test_read_digits_from_group_node():
    script = """
const fs = require('fs');
const vm = require('vm');
const code = fs.readFileSync(process.argv[1], 'utf8');
const sandbox = {
  window: {},
  document: {
    readyState: 'complete',
    addEventListener() {},
    querySelectorAll() { return []; },
  },
};
sandbox.window = sandbox;
vm.runInNewContext(code, sandbox);
const ImprintOtpInput = sandbox.window.ImprintOtpInput;
const digits = ['1', '2', '3', '4', '5', '6'].map((value) => ({ value }));
const group = {
  querySelectorAll() { return digits; },
};
const value = ImprintOtpInput.readDigits(group);
if (value !== '123456') {
  console.error('expected 123456 got ' + value);
  process.exit(1);
}
const hidden = { value: '' };
const boundGroup = {
  dataset: { otpBound: '1' },
  _imprintOtpApi: { getValue() { return 'cached'; } },
};
const cached = ImprintOtpInput.initGroup(boundGroup);
if (cached.getValue() !== 'cached') {
  console.error('expected cached api instance');
  process.exit(1);
}
"""
    result = subprocess.run(
        ["node", "-e", script, str(OTP_JS)],
        capture_output=True,
        text=True,
        cwd=ROOT,
        check=False,
    )
    assert result.returncode == 0, result.stderr or result.stdout


def test_forgot_password_js_declares_wizard_state():
    text = FP_JS.read_text(encoding="utf-8")
    assert "var currentStep = 1;" in text
    assert "var backupMode = false;" in text
    assert "function ensureOtpInit()" in text
    assert "fp-email-form" in text
    assert "data-fp-use-totp" in text
    assert "setStep('inbox', true)" in text
    assert "請輸入 Email。" in text
    assert "改用 6 位數驗證碼" in text


@pytest.mark.skipif(shutil.which("node") is None, reason="node not installed")
def test_forgot_password_email_then_totp_node():
    """Email success shows inbox; Authenticator control opens TOTP step."""
    script = """
const fs = require('fs');
const vm = require('vm');
const code = fs.readFileSync(process.argv[1], 'utf8');
const steps = {};
const indicators = {};
let totpBtn = null;
let emailForm = null;
function el(attrs) {
  return {
    hidden: false,
    classList: { toggle() {} },
    getAttribute(name) { return attrs[name]; },
    setAttribute() {},
    querySelector() { return null; },
    querySelectorAll(sel) {
      if (sel === '[data-fp-step]') return Object.values(steps);
      if (sel === '[data-fp-indicator]') return Object.values(indicators);
      return [];
    },
    addEventListener(type, fn) {
      this['_' + type] = fn;
    },
  };
}
steps[1] = el({ 'data-fp-step': '1' });
steps.inbox = el({ 'data-fp-step': 'inbox' });
steps[2] = el({ 'data-fp-step': '2' });
steps[3] = el({ 'data-fp-step': '3' });
indicators[1] = el({ 'data-fp-indicator': '1' });
indicators[2] = el({ 'data-fp-indicator': '2' });
indicators[3] = el({ 'data-fp-indicator': '3' });
const wizard = el({ 'data-fp-wizard': '1' });
wizard.querySelector = function(sel) {
  return null;
};
wizard.querySelectorAll = function(sel) {
  if (sel === '[data-fp-use-totp]') {
    if (!totpBtn) totpBtn = el({ 'data-fp-use-totp': '' });
    return [totpBtn];
  }
  if (sel === '[data-fp-back]') return [];
  if (sel === '[data-fp-step]') return Object.values(steps);
  if (sel === '[data-fp-indicator]') return Object.values(indicators);
  return [];
};
const emailHidden = { value: '' };
const emailInput = { value: 'user@example.com', focus() {} };
emailForm = el({});
const sandbox = {
  document: {
    readyState: 'complete',
    getElementById(id) {
      if (id === 'fpEmail') return emailInput;
      if (id === 'fpEmailHidden') return emailHidden;
      if (id === 'fpCodeHidden') return { value: '' };
      if (id === 'fp-email-form') return emailForm;
      if (id === 'auth-form-msg') return { innerHTML: '' };
      return null;
    },
    querySelector(sel) {
      if (sel === '[data-fp-wizard]') return wizard;
      if (sel === '[data-fp-step-desc]') return { textContent: '' };
      return null;
    },
    addEventListener() {},
  },
  window: { ImprintOtpInput: { initGroup() { return null; }, readDigits() { return ''; } } },
};
vm.runInNewContext(code, sandbox);
try {
  emailForm['_htmx:afterRequest']({ detail: { successful: true } });
} catch (err) {
  console.error('email success threw: ' + err.message);
  process.exit(1);
}
if (steps.inbox.hidden !== false) {
  console.error('inbox should be visible after email success');
  process.exit(1);
}
if (steps[2].hidden !== true) {
  console.error('step 2 should stay hidden after email success');
  process.exit(1);
}
try {
  totpBtn._click({ preventDefault() {} });
} catch (err) {
  console.error('totp control threw: ' + err.message);
  process.exit(1);
}
if (steps[2].hidden !== false) {
  console.error('step 2 should be visible after Authenticator control');
  process.exit(1);
}
if (emailHidden.value !== 'user@example.com') {
  console.error('email hidden not synced');
  process.exit(1);
}
"""
    result = subprocess.run(
        ["node", "-e", script, str(FP_JS)],
        capture_output=True,
        text=True,
        cwd=ROOT,
        check=False,
    )
    assert result.returncode == 0, result.stderr or result.stdout
