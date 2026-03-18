from app.core.config import config
from app.services.grok.headers import build_headers, build_sso_cookie


def test_build_sso_cookie_includes_sso_rw_and_cf_clearance():
    config._config = {
        "grok": {
            "cf_clearance": "cf-token",
        }
    }

    cookie = build_sso_cookie("sso=abc123")

    assert cookie == "sso=abc123; sso-rw=abc123; cf_clearance=cf-token"


def test_build_sso_cookie_replaces_existing_cf_clearance_in_cf_cookies():
    config._config = {
        "grok": {
            "cf_clearance": "new-clearance",
            "cf_cookies": "foo=bar; cf_clearance=old-clearance; baz=qux",
        }
    }

    cookie = build_sso_cookie("token-xyz")

    assert "sso=token-xyz" in cookie
    assert "sso-rw=token-xyz" in cookie
    assert "foo=bar" in cookie
    assert "baz=qux" in cookie
    assert "cf_clearance=new-clearance" in cookie
    assert "old-clearance" not in cookie


def test_build_headers_uses_dynamic_client_hints_and_cookie():
    config._config = {
        "grok": {
            "browser": "chrome136",
            "user_agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/136.0.0.0 Safari/537.36"
            ),
            "cf_clearance": "cf-123",
            "dynamic_statsig": True,
        }
    }

    headers = build_headers(
        "sso=test-token",
        content_type="application/json",
        origin="https://grok.com",
        referer="https://grok.com/",
    )

    assert headers["Cookie"] == "sso=test-token; sso-rw=test-token; cf_clearance=cf-123"
    assert headers["Sec-Ch-Ua-Platform"] == '"macOS"'
    assert headers["Sec-Fetch-Site"] == "same-origin"
    assert headers["Content-Type"] == "application/json"
    assert headers["x-statsig-id"]
    assert headers["x-xai-request-id"]
