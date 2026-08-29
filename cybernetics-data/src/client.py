"""Zero-dependency HTTP client for the cybernetics-data Teable instance.

Stdlib only (urllib) -- no pip install required. Config is read from the
environment first, falling back to a hand-parsed cybernetics-data/.env
(never printed or logged by this module).
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

DEFAULT_BASE_URL = "https://cybernetics.avarile.com"
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
BASE_URL_ENV_CANDIDATES = [
    "CYBERNETICS_DATA_URL", "CYBERNETICS_DATA_BASE_URL", "CYBERNETICS_BASE_URL", "TEABLE_BASE_URL",
]
TOKEN_ENV_CANDIDATES = [
    "CYBERNETICS_DATA_APITOKEN", "CYBERNETICS_DATA_API_TOKEN", "CYBERNETICS_API_TOKEN",
    "TEABLE_API_TOKEN", "TEABLE_TOKEN", "API_TOKEN",
]


class CyberneticsDataError(RuntimeError):
    """Raised when the Teable API returns an error or is misconfigured."""


_DOTENV_LINE = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*)\s*[:=]\s*(.*)$")


def parse_dotenv(text: str) -> dict:
    """Parses KEY=value and KEY: value lines alike. The delimiter is matched
    only at its first occurrence after the key, so an '=' or ':' appearing
    later inside the value (e.g. base64 padding) can't be mistaken for it."""
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
        raise CyberneticsDataError(
            "No API token found. Set one of "
            f"{', '.join(TOKEN_ENV_CANDIDATES)} in the environment or in {ENV_PATH}."
        )
    return {"base_url": base_url.rstrip("/"), "token": token}


def request(method: str, path: str, *, params: dict | None = None, body: dict | None = None) -> dict:
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
    # Cloudflare in front of this instance WAF-blocks the default
    # "Python-urllib/x.y" signature (403, Cloudflare error 1010) -- a plain
    # browser-like UA clears it.
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
        raise CyberneticsDataError(f"{method} {path} failed: {exc.code} {detail}") from exc


def list_records(
    table_id: str,
    *,
    filter: dict | None = None,
    order_by: list | None = None,
    projection: list | None = None,
    search: str | None = None,
    take: int = 100,
    skip: int = 0,
) -> dict:
    """One page of records. `filter`/`order_by` need Teable field IDs (not names) --
    prefer fetching everything with `iter_records` and filtering by field name
    in Python, which every function in finance.py/knowledge.py does."""
    params = {"fieldKeyType": "name", "take": take, "skip": skip}
    if filter is not None:
        params["filter"] = json.dumps(filter)
    if order_by is not None:
        params["orderBy"] = json.dumps(order_by)
    if projection is not None:
        params["projection"] = projection
    if search is not None:
        params["search"] = search
    return request("GET", f"/api/table/{table_id}/record", params=params)


def iter_records(table_id: str, *, take: int = 1000, **kwargs):
    """Yield every record across all pages (take capped at 1000 by the API)."""
    skip = 0
    while True:
        page = list_records(table_id, take=take, skip=skip, **kwargs)
        records = page.get("records", [])
        if not records:
            return
        yield from records
        if len(records) < take:
            return
        skip += take


def get_record(table_id: str, record_id: str) -> dict:
    return request("GET", f"/api/table/{table_id}/record/{record_id}")


def create_records(table_id: str, records: list) -> dict:
    body = {"fieldKeyType": "name", "records": [{"fields": fields} for fields in records]}
    return request("POST", f"/api/table/{table_id}/record", body=body)


def update_record(table_id: str, record_id: str, fields: dict) -> dict:
    body = {"fieldKeyType": "name", "record": {"fields": fields}}
    return request("PATCH", f"/api/table/{table_id}/record/{record_id}", body=body)


def delete_record(table_id: str, record_id: str) -> dict:
    return request("DELETE", f"/api/table/{table_id}/record/{record_id}")
