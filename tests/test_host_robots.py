"""Host-gated robots: no-hyphen apex noindex; hyphen shop stays indexable."""

from __future__ import annotations

import os
from pathlib import Path

import pytest
from dotenv import load_dotenv

from app.robots_host import (
    HOST_NOINDEX_ROBOTS,
    html_robots_content,
    is_noindex_host,
    normalize_request_host,
    x_robots_tag_value,
)

load_dotenv(Path(__file__).resolve().parents[1] / ".env")
os.environ.setdefault("STARTUP_SEED_MODE", "off")

_INDEXABLE_META = 'content="index, follow, max-image-preview:large"'
_NOINDEX_META = 'content="noindex, follow"'

_NOINDEX_HOSTS = (
    "imprintdiamond.com",
    "www.imprintdiamond.com",
)
_INDEX_HOSTS = (
    "imprint-diamond.com",
    "www.imprint-diamond.com",
)


@pytest.fixture(scope="module")
def client():
    from fastapi.testclient import TestClient

    from app import create_app

    with TestClient(create_app()) as c:
        yield c


@pytest.mark.parametrize(
    ("raw", "want"),
    [
        ("imprintdiamond.com", "imprintdiamond.com"),
        ("WWW.ImprintDiamond.COM", "www.imprintdiamond.com"),
        ("imprintdiamond.com:443", "imprintdiamond.com"),
        ("www.imprintdiamond.com:8080", "www.imprintdiamond.com"),
        ("Imprint-Diamond.COM:443", "imprint-diamond.com"),
        ("localhost:8000", "localhost"),
        ("[::1]:443", "::1"),
        ("", ""),
        (None, ""),
    ],
)
def test_normalize_request_host_case_and_port(raw, want):
    assert normalize_request_host(raw) == want


@pytest.mark.parametrize("host", _NOINDEX_HOSTS)
def test_is_noindex_host_matches_no_hyphen(host):
    assert is_noindex_host(host) is True
    assert is_noindex_host(host.upper()) is True
    assert is_noindex_host(f"{host}:443") is True


@pytest.mark.parametrize("host", _INDEX_HOSTS)
def test_is_noindex_host_skips_hyphen_shop(host):
    assert is_noindex_host(host) is False
    assert is_noindex_host(f"{host}:443") is False


def test_is_noindex_host_skips_other_hosts():
    assert is_noindex_host("testserver") is False
    assert is_noindex_host("localhost:8000") is False
    assert is_noindex_host("imprint-website.onrender.com") is False


def test_html_and_header_share_one_gate():
    host = "WWW.IMPRINTDIAMOND.COM:443"
    assert html_robots_content(host, None) == HOST_NOINDEX_ROBOTS
    assert x_robots_tag_value(host) == HOST_NOINDEX_ROBOTS
    assert html_robots_content(host, "noindex, nofollow") == "noindex, nofollow"


def test_hyphen_host_does_not_override_indexable_robots():
    host = "www.imprint-diamond.com:443"
    assert html_robots_content(host, None) is None
    assert x_robots_tag_value(host) is None


@pytest.mark.parametrize("host", _NOINDEX_HOSTS)
def test_no_hyphen_host_html_and_header_noindex(client, host):
    resp = client.get("/", headers={"Host": host})
    assert resp.status_code == 200
    assert resp.headers.get("x-robots-tag") == "noindex, follow"
    assert _NOINDEX_META in resp.text
    assert _INDEXABLE_META not in resp.text


@pytest.mark.parametrize("host", _INDEX_HOSTS)
def test_hyphen_shop_host_stays_index_follow(client, host):
    resp = client.get("/", headers={"Host": host})
    assert resp.status_code == 200
    tag = (resp.headers.get("x-robots-tag") or "").lower()
    assert "noindex" not in tag
    assert _INDEXABLE_META in resp.text
    assert _NOINDEX_META not in resp.text


@pytest.mark.parametrize(
    "host",
    [
        "ImprintDiamond.COM",
        "WWW.IMPRINTDIAMOND.COM",
        "imprintdiamond.com:443",
        "www.imprintdiamond.com:8080",
        "WWW.ImprintDiamond.COM:443",
    ],
)
def test_noindex_host_check_is_case_insensitive_and_strips_port(client, host):
    resp = client.get("/", headers={"Host": host})
    assert resp.status_code == 200
    assert resp.headers.get("x-robots-tag") == "noindex, follow"
    assert _NOINDEX_META in resp.text


@pytest.mark.parametrize(
    "host",
    [
        "testserver",
        "localhost:8000",
        "imprint-website.onrender.com",
    ],
)
def test_other_hosts_keep_current_index_follow(client, host):
    resp = client.get("/", headers={"Host": host})
    assert resp.status_code == 200
    tag = (resp.headers.get("x-robots-tag") or "").lower()
    assert "noindex" not in tag
    assert _INDEXABLE_META in resp.text
