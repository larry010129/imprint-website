"""Lightweight bot heuristics for public lead forms (contact, quote-request).

Layered in front of reCAPTCHA v3 (see app/captcha.py):
- a honeypot field bots fill in but real users never see
- a submit-timing check that flags requests faster than a human can type
- a keyword/link blacklist for obvious ad spam — a static list here, plus
  keywords admins teach it at runtime (see ensure_spam_keywords_schema /
  add_spam_keywords / load_dynamic_keywords, used by the admin "mark as
  spam" action in app/controllers/admin_controller.py).
"""

from __future__ import annotations

import re
import time

HONEYPOT_FIELD = "hp_website"
FORM_LOADED_FIELD = "hp_ts"
MIN_SUBMIT_SECONDS = 2.0

_SPAM_KEYWORDS = (
    # Chinese
    "娛樂城",
    "博彩",
    "百家樂",
    "貸款",
    "信用貸款",
    "seo優化",
    "seo服務",
    "排名優化",
    "代操",
    "加賴",
    "代購",
    "微信代付",
    "刷單",
    "兼職日結",
    # English
    "viagra",
    "cialis",
    "casino",
    "payday loan",
    "bad credit loan",
    "male enhancement",
    "weight loss pills",
    "forex signals",
    "crypto signals",
    "binary options",
    "seo backlinks",
    "buy backlinks",
    "cheap essay",
    "essay writing service",
    "work from home",
    "make money fast",
    "hot singles",
    "adult dating",
    "onlyfans",
    "escort service",
    "replica watches",
    "click here to claim",
    "you have won",
    "free bitcoin",
    # Russian / Cyrillic
    "казино",
    "займ",
    "кредит наличными",
    "ставки на спорт",
    # Spanish / Portuguese
    "préstamo rápido",
    "emprestimo rapido",
    "casino online",
    # Japanese / Korean
    "出会い系",
    "アダルト",
    "대출",
    "카지노",
    # link shorteners / contact-harvesting handles common across all of the above
    "bit.ly",
    "tinyurl.com",
    "t.me/",
    "wa.me/",
    "linktr.ee",
)

_URL_RE = re.compile(r"https?://|www\.", re.IGNORECASE)


def is_spam_submission(
    *,
    honeypot: str | None,
    form_loaded_at: str | None,
    text_fields: list[str],
    extra_keywords: list[str] | None = None,
) -> bool:
    """True if the submission looks bot-generated rather than human.

    honeypot: value of the hidden trap field — any non-empty value is a bot.
    form_loaded_at: epoch-ms the form was rendered (set by client JS on
      load); missing, malformed, or submitted within MIN_SUBMIT_SECONDS
      means it wasn't a human filling out the visible form.
    text_fields: user-supplied strings to scan for blacklisted spam markers.
    extra_keywords: additional words to check beyond the static list —
      pass load_dynamic_keywords(cur) here to include admin-taught ones.
    """
    if (honeypot or "").strip():
        return True

    try:
        elapsed = (time.time() * 1000 - float(form_loaded_at)) / 1000
    except (TypeError, ValueError):
        return True
    if elapsed < MIN_SUBMIT_SECONDS:
        return True

    combined = " ".join(text_fields).lower()
    keywords = _SPAM_KEYWORDS + tuple(extra_keywords or ())
    if any(word and word in combined for word in keywords):
        return True
    if len(_URL_RE.findall(combined)) >= 2:
        return True

    return False


# ---------------------------------------------------------------------------
# Admin-taught keywords — "mark as spam" in the leads table extracts a few
# distinguishing words from the flagged lead and remembers them here, so the
# next submission carrying the same words is rejected automatically.
# ---------------------------------------------------------------------------

_DOMAIN_RE = re.compile(
    r"\b(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,}\b", re.IGNORECASE
)
_TOKEN_RE = re.compile(
    r"[A-Za-z0-9]{4,}"  # latin words / numbers (natural word breaks on spaces)
    # CJK/Japanese/Korean have no spaces, so cap the run length to keep
    # tokens phrase-sized instead of swallowing an entire sentence.
    r"|[一-鿿]{2,8}"  # Chinese
    r"|[぀-ヿ]{2,8}"  # hiragana / katakana
    r"|[가-힣]{2,8}"  # hangul
    r"|[Ѐ-ӿ]{4,}"  # cyrillic (space-delimited, like Latin)
)

# Common site/jewelry vocabulary and function words we never want to
# blacklist, so marking one odd lead as spam can't start rejecting normal
# inquiries that happen to share ordinary words.
_STOPWORDS = frozenset(
    {
        # Chinese function words + this site's own vocabulary
        "的", "了", "是", "我", "你", "在", "有", "和", "就", "都", "而", "及", "與",
        "或", "一", "也", "很", "到", "說", "要", "去", "會", "著", "沒有", "看",
        "好", "自己", "這", "那", "您", "您好", "謝謝", "請問", "麻煩", "姓名",
        "電話", "需求", "訊息", "留言", "諮詢", "預約", "時間", "價格", "克拉",
        "鑽石", "婚戒", "系列", "訂製", "官網", "表單", "門市", "聯絡", "想",
        "了解", "可以", "請",
        # English stopwords
        "the", "and", "is", "in", "at", "of", "to", "for", "this", "that",
        "with", "you", "your", "please", "phone", "email", "name", "message",
        "hello", "hi", "thanks", "thank", "gmail", "com",
    }
)

# Public webmail domains are used by huge numbers of real customers, so they
# must never become a blacklisted "keyword" even when they show up in a
# flagged lead's email address.
_COMMON_EMAIL_DOMAINS = frozenset(
    {
        "gmail.com", "yahoo.com", "yahoo.com.tw", "hotmail.com", "outlook.com",
        "icloud.com", "msn.com", "live.com", "qq.com", "163.com", "126.com",
        "protonmail.com", "naver.com", "daum.net", "hanmail.net", "me.com",
        "pchome.com.tw", "seed.net.tw",
    }
)


def ensure_spam_keywords_schema(cur) -> None:
    cur.execute(
        """
        create table if not exists spam_keywords (
          id uuid primary key default gen_random_uuid(),
          keyword text not null unique,
          created_by text,
          created_at timestamptz not null default now()
        )
        """
    )


def load_dynamic_keywords(cur) -> list[str]:
    cur.execute("select keyword from spam_keywords")
    return [row["keyword"] for row in cur.fetchall()]


def add_spam_keywords(cur, keywords: list[str], created_by: str | None = None) -> list[str]:
    """Insert new keywords (deduped, case-insensitive). Returns the ones actually added."""
    added: list[str] = []
    for raw in keywords:
        word = raw.strip().lower()
        if not word:
            continue
        cur.execute(
            """
            insert into spam_keywords (keyword, created_by)
            values (%s, %s)
            on conflict (keyword) do nothing
            returning keyword
            """,
            (word, created_by),
        )
        row = cur.fetchone()
        if row:
            added.append(row["keyword"])
    return added


def extract_candidate_keywords(*texts: str, limit: int = 6) -> list[str]:
    """Pull a handful of distinguishing words/domains out of flagged lead text.

    Skips common site vocabulary and function words (see _STOPWORDS) so a
    single mistaken "mark as spam" click can't start blocking ordinary
    inquiries. Domains (from any URL in the text) are preferred first since
    they're the least likely to collide with a genuine customer message.
    """
    combined = " ".join(t for t in texts if t)
    found: list[str] = []
    seen: set[str] = set()

    for domain in _DOMAIN_RE.findall(combined):
        low = domain.lower()
        if low in seen or low in _COMMON_EMAIL_DOMAINS:
            continue
        seen.add(low)
        found.append(low)
        if len(found) >= limit:
            return found

    for match in _TOKEN_RE.findall(combined):
        low = match.strip().lower()
        if not low or low in _STOPWORDS or low in seen:
            continue
        seen.add(low)
        found.append(low)
        if len(found) >= limit:
            break

    return found
