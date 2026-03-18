"""
Shared Grok upstream header builders.
"""

from __future__ import annotations

import re
import uuid
from urllib.parse import urlparse
from typing import Dict, Optional

from app.core.config import get_config
from app.core.logger import logger
from app.services.grok.statsig import StatsigService

_HEADER_CHAR_REPLACEMENTS = str.maketrans(
    {
        "\u2010": "-",
        "\u2011": "-",
        "\u2012": "-",
        "\u2013": "-",
        "\u2014": "-",
        "\u2212": "-",
        "\u2018": "'",
        "\u2019": "'",
        "\u201c": '"',
        "\u201d": '"',
        "\u00a0": " ",
        "\u2007": " ",
        "\u202f": " ",
        "\u200b": "",
        "\u200c": "",
        "\u200d": "",
        "\ufeff": "",
    }
)

DEFAULT_BROWSER = "chrome136"
DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/136.0.0.0 Safari/537.36"
)


def _sanitize_header_value(
    value: Optional[str],
    *,
    field_name: str,
    remove_all_spaces: bool = False,
) -> str:
    raw = "" if value is None else str(value)
    normalized = raw.translate(_HEADER_CHAR_REPLACEMENTS)
    if remove_all_spaces:
        normalized = re.sub(r"\s+", "", normalized)
    else:
        normalized = normalized.strip()

    normalized = normalized.encode("latin-1", errors="ignore").decode("latin-1")

    if normalized != raw:
        logger.warning(
            f"Sanitized header field '{field_name}' (len {len(raw)} -> {len(normalized)})"
        )
    return normalized


def get_impersonate_browser() -> str:
    return str(
        get_config("grok.browser")
        or get_config("proxy.browser")
        or DEFAULT_BROWSER
    ).strip() or DEFAULT_BROWSER


def get_user_agent() -> str:
    return _sanitize_header_value(
        get_config("grok.user_agent")
        or get_config("proxy.user_agent")
        or DEFAULT_USER_AGENT,
        field_name="user_agent",
    )


def build_sso_cookie(sso_token: str) -> str:
    token = sso_token[4:] if str(sso_token).startswith("sso=") else str(sso_token or "")
    token = _sanitize_header_value(
        token,
        field_name="sso_token",
        remove_all_spaces=True,
    )

    cookie = f"sso={token}; sso-rw={token}"

    cf_cookies = _sanitize_header_value(
        get_config("grok.cf_cookies") or get_config("proxy.cf_cookies") or "",
        field_name="cf_cookies",
    )
    cf_clearance = _sanitize_header_value(
        get_config("grok.cf_clearance") or get_config("proxy.cf_clearance") or "",
        field_name="cf_clearance",
        remove_all_spaces=True,
    )

    if cf_clearance:
        if cf_cookies:
            if re.search(r"(?:^|;\s*)cf_clearance=", cf_cookies):
                cf_cookies = re.sub(
                    r"(^|;\s*)cf_clearance=[^;]*",
                    r"\1cf_clearance=" + cf_clearance,
                    cf_cookies,
                    count=1,
                )
            else:
                cf_cookies = cf_cookies.rstrip("; ")
                cf_cookies = f"{cf_cookies}; cf_clearance={cf_clearance}"
        else:
            cf_cookies = f"cf_clearance={cf_clearance}"

    if cf_cookies:
        cookie = f"{cookie}; {cf_cookies}"

    return cookie


def _extract_major_version(browser: Optional[str], user_agent: Optional[str]) -> Optional[str]:
    if browser:
        match = re.search(r"(\d{2,3})", browser)
        if match:
            return match.group(1)
    if user_agent:
        for pattern in (r"Edg/(\d+)", r"Chrome/(\d+)", r"Chromium/(\d+)"):
            match = re.search(pattern, user_agent)
            if match:
                return match.group(1)
    return None


def _detect_platform(user_agent: str) -> Optional[str]:
    ua = user_agent.lower()
    if "windows" in ua:
        return "Windows"
    if "mac os x" in ua or "macintosh" in ua:
        return "macOS"
    if "android" in ua:
        return "Android"
    if "iphone" in ua or "ipad" in ua:
        return "iOS"
    if "linux" in ua:
        return "Linux"
    return None


def _detect_arch(user_agent: str) -> Optional[str]:
    ua = user_agent.lower()
    if "aarch64" in ua or " arm" in ua:
        return "arm"
    if "x86_64" in ua or "x64" in ua or "win64" in ua or "intel" in ua:
        return "x86"
    return None


def _build_client_hints(browser: Optional[str], user_agent: Optional[str]) -> Dict[str, str]:
    browser = (browser or "").strip().lower()
    user_agent = user_agent or ""
    ua = user_agent.lower()

    is_edge = "edge" in browser or "edg" in ua
    is_brave = "brave" in browser
    is_chromium = any(key in browser for key in ("chrome", "chromium", "edge", "brave")) or (
        "chrome" in ua or "chromium" in ua or "edg" in ua
    )
    is_firefox = "firefox" in browser or "firefox" in ua
    is_safari = (
        ("safari" in ua and "chrome" not in ua and "chromium" not in ua and "edg" not in ua)
        or "safari" in browser
    )

    if not is_chromium or is_firefox or is_safari:
        return {}

    version = _extract_major_version(browser, user_agent)
    if not version:
        return {}

    if is_edge:
        brand = "Microsoft Edge"
    elif "chromium" in browser:
        brand = "Chromium"
    elif is_brave:
        brand = "Brave"
    else:
        brand = "Google Chrome"

    sec_ch_ua = (
        f"\"{brand}\";v=\"{version}\", "
        f"\"Chromium\";v=\"{version}\", "
        "\"Not(A:Brand\";v=\"24\""
    )

    platform = _detect_platform(user_agent)
    arch = _detect_arch(user_agent)
    mobile = "?1" if ("mobile" in ua or platform in ("Android", "iOS")) else "?0"

    hints = {
        "Sec-Ch-Ua": sec_ch_ua,
        "Sec-Ch-Ua-Mobile": mobile,
    }
    if platform:
        hints["Sec-Ch-Ua-Platform"] = f"\"{platform}\""
    if arch:
        hints["Sec-Ch-Ua-Arch"] = arch
        hints["Sec-Ch-Ua-Bitness"] = "64"
    hints["Sec-Ch-Ua-Model"] = ""
    return hints


def build_headers(
    token: str,
    *,
    content_type: Optional[str] = "application/json",
    origin: Optional[str] = None,
    referer: Optional[str] = None,
) -> Dict[str, str]:
    user_agent = get_user_agent()
    safe_origin = _sanitize_header_value(origin or "https://grok.com", field_name="origin")
    safe_referer = _sanitize_header_value(
        referer or "https://grok.com/",
        field_name="referer",
    )

    headers = {
        "Accept-Encoding": "gzip, deflate, br, zstd",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        "Baggage": "sentry-environment=production,sentry-release=d6add6fb0460641fd482d767a335ef72b9b6abb8,sentry-public_key=b311e0f2690c81f25e2c4cf6d4f7ce1c",
        "Origin": safe_origin,
        "Priority": "u=1, i",
        "Referer": safe_referer,
        "Sec-Fetch-Mode": "cors",
        "User-Agent": user_agent,
        "Cookie": build_sso_cookie(token),
        "x-statsig-id": StatsigService.gen_id(),
        "x-xai-request-id": str(uuid.uuid4()),
    }

    client_hints = _build_client_hints(get_impersonate_browser(), user_agent)
    if client_hints:
        headers.update(client_hints)

    if content_type and content_type == "application/json":
        headers["Content-Type"] = "application/json"
        headers["Accept"] = "*/*"
        headers["Sec-Fetch-Dest"] = "empty"
    elif content_type in {"image/jpeg", "image/png", "video/mp4", "video/webm"}:
        headers["Content-Type"] = content_type
        headers["Accept"] = (
            "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,"
            "image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7"
        )
        headers["Sec-Fetch-Dest"] = "document"
    else:
        headers["Content-Type"] = content_type or "application/json"
        headers["Accept"] = "*/*"
        headers["Sec-Fetch-Dest"] = "empty"

    origin_domain = urlparse(headers.get("Origin", "")).hostname
    referer_domain = urlparse(headers.get("Referer", "")).hostname
    headers["Sec-Fetch-Site"] = (
        "same-origin" if origin_domain and referer_domain and origin_domain == referer_domain else "same-site"
    )

    return headers


__all__ = [
    "build_headers",
    "build_sso_cookie",
    "get_impersonate_browser",
    "get_user_agent",
]
