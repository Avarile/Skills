"""Zero-dependency HTTP client for the self-hosted Twenty CRM REST API.

Stdlib only (urllib) -- no pip install required. Config is read from the
environment first, falling back to a hand-parsed twenty-crm/.env (never
printed or logged by this module).
"""
from __future__ import annotations

import json
import os
import re
import ssl
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

DEFAULT_BASE_URL = "https://crm.avarile.com"
DATA_DIR = Path(__file__).resolve().parent.parent
ENV_PATH = DATA_DIR / ".env"

# Some Homebrew Python builds on macOS don't bundle a CA file at the path
# their default SSL context expects, so `ssl.create_default_context()`
# fails with CERTIFICATE_VERIFY_FAILED even for validly-signed hosts. Fall
# back to a system bundle if one exists; otherwise use the normal default.
_SYSTEM_CA_BUNDLE_CANDIDATES = [
    "/etc/ssl/cert.pem",
    "/opt/homebrew/etc/ca-certificates/cert.pem",
    "/opt/homebrew/etc/openssl@3/cert.pem",
]


def _ssl_context() -> ssl.SSLContext:
    for candidate in _SYSTEM_CA_BUNDLE_CANDIDATES:
        if os.path.isfile(candidate):
            return ssl.create_default_context(cafile=candidate)
    return ssl.create_default_context()

# Checked in order; the .env in this folder may use any one of these names.
BASE_URL_ENV_CANDIDATES = ["TWENTY_CRM_URL", "TWENTY_CRM_BASE_URL", "CRM_URL", "TWENTY_BASE_URL"]
TOKEN_ENV_CANDIDATES = [
    "TWENTY_CRM_APITOKEN", "TWENTY_CRM_API_TOKEN", "TWENTY_API_KEY", "CRM_API_TOKEN", "API_TOKEN",
]


class TwentyCrmError(RuntimeError):
    """Raised when the Twenty CRM API returns an error or is misconfigured."""


_DOTENV_LINE = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*)\s*[:=]\s*(.*)$")


def parse_dotenv(text: str) -> dict:
    """Parses KEY=value and KEY: value lines alike. The delimiter is matched
    only at its first occurrence after the key, so an '=' or ':' appearing
    later inside the value (e.g. a JWT's base64 padding) can't be mistaken
    for it."""
    out = {}
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        match = _DOTENV_LINE.match(line)
        if not match:
            continue
        key, value = match.group(1), match.group(2).strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        out[key] = value
    return out


def _load_dotenv() -> dict:
    if not ENV_PATH.is_file():
        return {}
    return parse_dotenv(ENV_PATH.read_text())


def _first(candidates: list[str], *sources: dict) -> str | None:
    for name in candidates:
        for source in sources:
            value = source.get(name)
            if value:
                return value
    return None


def get_config() -> dict:
    dotenv = _load_dotenv()
    base_url = _first(BASE_URL_ENV_CANDIDATES, os.environ, dotenv) or DEFAULT_BASE_URL
    token = _first(TOKEN_ENV_CANDIDATES, os.environ, dotenv)
    if not token:
        raise TwentyCrmError(
            "No API token found. Set one of "
            f"{', '.join(TOKEN_ENV_CANDIDATES)} in the environment or in {ENV_PATH}."
        )
    return {"base_url": base_url.rstrip("/"), "token": token}


def request(method: str, path: str, *, params: dict | None = None, body=None) -> dict:
    config = get_config()
    url = f"{config['base_url']}{path}"
    if params:
        query = urllib.parse.urlencode(
            {k: v for k, v in params.items() if v is not None}, doseq=True
        )
        if query:
            url = f"{url}?{query}"
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Authorization", f"Bearer {config['token']}")
    # Cloudflare (or an equivalent WAF) in front of this instance blocks the
    # default "Python-urllib/x.y" signature with a 403 -- a plain
    # browser-like UA clears it. Verified against the live instance.
    req.add_header(
        "User-Agent",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36",
    )
    req.add_header("Accept", "application/json")
    if data is not None:
        req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, context=_ssl_context()) as resp:
            payload = resp.read()
            return json.loads(payload) if payload else {}
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise TwentyCrmError(f"{method} {path} failed: {exc.code} {detail}") from exc


def list_people(
    *,
    filter: str | None = None,
    order_by: str | None = None,
    limit: int = 60,
    starting_after: str | None = None,
) -> dict:
    """One page of the raw `/rest/people` response (`data.people`,
    `totalCount`, `pageInfo`). `filter` uses Twenty's own syntax, e.g.
    `"emails.primaryEmail[eq]:ada@example.com"` -- see SKILL.md."""
    params = {"filter": filter, "order_by": order_by, "limit": limit, "starting_after": starting_after}
    return request("GET", "/rest/people", params=params)


def iter_people(*, filter: str | None = None, order_by: str | None = None, page_size: int = 60):
    """Yield every person across all pages via cursor-based pagination."""
    cursor = None
    while True:
        page = list_people(filter=filter, order_by=order_by, limit=page_size, starting_after=cursor)
        records = page.get("data", {}).get("people", [])
        yield from records
        page_info = page.get("pageInfo", {})
        if not page_info.get("hasNextPage") or not records:
            return
        cursor = page_info.get("endCursor")


def get_person(person_id: str) -> dict:
    return request("GET", f"/rest/people/{person_id}")


def create_person(fields: dict) -> dict:
    return request("POST", "/rest/people", body=fields)


def batch_create_people(people: list, *, upsert: bool = False) -> dict:
    params = {"upsert": "true"} if upsert else None
    return request("POST", "/rest/batch/people", params=params, body=people)


def update_person(person_id: str, fields: dict) -> dict:
    return request("PATCH", f"/rest/people/{person_id}", body=fields)


def delete_person(person_id: str) -> dict:
    return request("DELETE", f"/rest/people/{person_id}")
