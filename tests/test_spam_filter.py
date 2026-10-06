"""Spam filter rules for the public contact form (no DB)."""

from __future__ import annotations

import time

from app.spam_filter import HONEYPOT_FIELD, is_spam_submission, spam_reason


def _stamp(seconds_ago: float) -> str:
    return str(time.time() * 1000 - seconds_ago * 1000)


def _reason(**over):
    args = dict(
        honeypot="",
        form_loaded_at=_stamp(30),
        text_fields=["王小明", "想了解婚戒訂製", "0912345678", "a@example.com"],
    )
    args.update(over)
    return spam_reason(**args)


def test_normal_submission_passes():
    assert _reason() is None


def test_honeypot_name_is_not_a_common_autofill_name():
    assert HONEYPOT_FIELD == "hp_trap_x"


def test_honeypot_filled_is_rejected():
    assert "honeypot" in _reason(honeypot="http://x.com")


def test_too_fast_is_rejected():
    assert "too fast" in _reason(form_loaded_at=_stamp(0.5))


def test_missing_or_bad_timestamp_is_rejected():
    assert "timestamp" in _reason(form_loaded_at="")
    assert "timestamp" in _reason(form_loaded_at="abc")


def test_phone_clock_ahead_of_server_is_not_spam():
    # Visitor clock 30s ahead -> negative elapsed; must not look like a bot.
    assert _reason(form_loaded_at=_stamp(-30)) is None


def test_absurd_future_timestamp_is_rejected():
    assert "future" in _reason(form_loaded_at=_stamp(-10 * 86400))


def test_keywords_and_links_are_rejected_with_reason():
    assert "casino" in _reason(text_fields=["Casino bonus"])
    assert "two or more links" in _reason(text_fields=["http://a.com http://b.com"])
    assert "代購" in _reason(text_fields=["請問可以代購嗎"], extra_keywords=["代購"])


def test_is_spam_submission_matches_reason():
    assert not is_spam_submission(
        honeypot="", form_loaded_at=_stamp(30), text_fields=["hello"]
    )
    assert is_spam_submission(
        honeypot="x", form_loaded_at=_stamp(30), text_fields=["hello"]
    )
