"""Zero-dependency HTTP client for the Cybernetics knowledge tables.

Stdlib only (urllib) -- no pip install. Config comes from the environment
first, then from the .env this skill owns. The token is never printed or
logged.

Every behaviour encoded here was verified live against
https://cybernetics.avarile.com on 2026-09-19; see
references/api-behavior.md for the probe results, including the places
where the published API docs are wrong.
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
SKILL_DIR = Path(__file__).resolve().parent.parent

# This skill owns the token: `<skill>/.env` is its one canonical home, so the
# skill directory is self-contained and can be moved or copied anywhere without
# depending on a sibling folder. It is covered by the repo's bare `.env`
# gitignore rule, which matches at any depth. An environment variable still
# takes precedence -- see get_config.
ENV_PATHS = [SKILL_DIR / ".env"]

TABLES = {
    "knowledges": "tblVTWb1kxXSFPBq4Fq",
    "knowledge_type": "tblWcq6Kof1AFHvbC5e",
}

# Field IDs are recorded only because DELETE responses key `fields` by ID
# regardless of fieldKeyType, so decoding a delete result needs them.
# `filter`/`orderBy` accept field NAMES on this instance (docs claim
# otherwise -- verified wrong), so nothing else here needs an ID.
FIELD_IDS = {
    "knowledges": {
        "title": "fldROFj15OlD8COVxX0", "context": "fld5tr2rH8oJXLrjUo9",
        "created_at": "fldRs8i67CkuzpDyubP", "updated_at": "fldCpv0ts2jxxgQPg7n",
        "deleted_at": "fldNS9SNNWG07NnBZhE", "is_active": "fldZKMuaBBPd6tIzSG3",
        "id": "fldNxPGGDuchpHCvz0U", "knowledge_type": "fldAEK8ULw9urxE0qiF",
        "knowledge_parent": "fldzUUVy3q1vSWURhZD", "knowledges": "fldKzPJEFtElf4liepG",
        "related_knowledge": "fldz7U2RsCfm0j1RZOs",
    },
    "knowledge_type": {
        "title": "fldvL1LqKmEAfNKVBCO", "context": "fldsnpIqBqoYZJxZwI5",
        "created_at": "fldAPzS5RXnhHUrVlmu", "updated_at": "fld1TMYMRUBblTyTIuU",
        "deleted_at": "fldMcIaV4FSsuV9OG9J", "is_active": "fldte086UL30roxKKAl",
        "id": "fldD6MxhSrpatAbHd0k", "knowledges": "fldtBWHVokGwcAywjtc",
        "credentials": "fld1s2dEom17aZIu4nx", "child_types": "fldehPY6CjjdpeK3H6j",
        "parent_type": "fld924GlXY0tL5um2wk",
    },
}

WRITABLE = {
    "knowledges": ["title", "context", "deleted_at", "is_active",
                   "knowledge_type", "knowledge_parent", "knowledges",
                   "related_knowledge"],
    "knowledge_type": ["title", "context", "deleted_at", "is_active",
                       "knowledges", "credentials", "child_types", "parent_type"],
}

BASE_URL_ENV = ["CYBERNETICS_DATA_URL", "CYBERNETICS_DATA_BASE_URL",
                "CYBERNETICS_BASE_URL", "TEABLE_BASE_URL"]
TOKEN_ENV = ["CYBERNETICS_DATA_APITOKEN", "CYBERNETICS_DATA_API_TOKEN",
             "CYBERNETICS_API_TOKEN", "TEABLE_API_TOKEN", "TEABLE_TOKEN", "API_TOKEN"]

# Some Homebrew Python builds on macOS ship no CA file at the path their
# default SSL context expects, so create_default_context() raises
# CERTIFICATE_VERIFY_FAILED even for a validly-signed host.
_CA_CANDIDATES = ["/etc/ssl/cert.pem",
                  "/opt/homebrew/etc/ca-certificates/cert.pem",
                  "/opt/homebrew/etc/openssl@3/cert.pem"]


class KnowledgeError(RuntimeError):
    """Raised on an API error or a misconfiguration."""


def _ssl_context() -> ssl.SSLContext:
    for candidate in _CA_CANDIDATES:
        if os.path.isfile(candidate):
            return ssl.create_default_context(cafile=candidate)
    return ssl.create_default_context()


_DOTENV_LINE = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*)\s*[:=]\s*(.*)$")


def parse_dotenv(text: str) -> dict:
    """Parses `KEY=value` and `KEY: value` alike. The delimiter is matched only
    at its first occurrence after the key, so an '=' or ':' later in the value
    (base64 padding, a URL) is kept verbatim."""
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


def _dotenv() -> dict:
    merged = {}
    for path in ENV_PATHS:
        if path.is_file():
            for key, value in parse_dotenv(path.read_text()).items():
                merged.setdefault(key, value)
    return merged


def _first(names: list, *sources: dict):
    for name in names:
        for source in sources:
            if source.get(name):
                return source[name]
    return None


def get_config() -> dict:
    dotenv = _dotenv()
    token = _first(TOKEN_ENV, os.environ, dotenv)
    if not token:
        raise KnowledgeError(
            "No API token found. Set one of " + ", ".join(TOKEN_ENV) +
            " in the environment or in " + " or ".join(str(p) for p in ENV_PATHS))
    base = _first(BASE_URL_ENV, os.environ, dotenv) or DEFAULT_BASE_URL
    return {"base_url": base.rstrip("/"), "token": token}


def request(method: str, path: str, *, query: str | None = None,
            body: dict | None = None):
    config = get_config()
    url = f"{config['base_url']}{path}"
    if query:
        url = f"{url}?{query}"
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Authorization", f"Bearer {config['token']}")
    # Cloudflare fronts this instance and WAF-blocks the default
    # "Python-urllib/x.y" UA with 403 / error 1010; a browser-like UA clears it.
    req.add_header("User-Agent",
                   "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                   "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36")
    req.add_header("Accept", "application/json")
    if data is not None:
        req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, context=_ssl_context()) as resp:
            payload = resp.read()
            return json.loads(payload) if payload else {}
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise KnowledgeError(f"{method} {path} -> {exc.code}: {_terse(detail)}") from exc
    except urllib.error.URLError as exc:
        raise KnowledgeError(f"{method} {path} failed: {exc.reason}") from exc


def _terse(detail: str) -> str:
    """Pull the human message out of a Teable error envelope."""
    try:
        parsed = json.loads(detail)
    except ValueError:
        return detail[:400]
    message = parsed.get("message", detail)
    available = (parsed.get("data", {}).get("details", {}) or {}).get("availableFieldKeys")
    if available:
        message = f"{message} (available fields: {', '.join(available)})"
    return message


def contains_filter(field: str, value: str) -> dict:
    """A real server-side substring filter. Use this instead of `search`:
    the `search` param does NOT filter on this instance (verified -- it
    returns every record even for a nonsense query, and only reorders)."""
    return {"conjunction": "and",
            "filterSet": [{"fieldId": field, "operator": "contains", "value": value}]}


def or_contains_filter(fields: list, value: str) -> dict:
    """Substring match across several fields in one request (OR).

    Verified: `{"conjunction": "or"}` works, and a nonsense query returns 0
    records -- unlike `search`, which returns the whole table.

    An unknown field name in a filterSet does not raise, it just matches
    nothing, so take names from SEARCHABLE rather than hand-writing them.
    """
    if not fields:
        raise KnowledgeError("or_contains_filter needs at least one field.")
    return {"conjunction": "or",
            "filterSet": [{"fieldId": f, "operator": "contains", "value": value}
                          for f in fields]}


# Fields that accept the `contains` operator, verified live. Single-selects and
# checkboxes reject it with 400 "Invalid record condition operator for field".
# `knowledge_type.credentials` is excluded on purpose: it holds real secrets and
# is not returned by the normalizers, so a hit there would be unexplainable.
SEARCHABLE = {
    "knowledges": ["title", "context", "knowledge_type"],
    "knowledge_type": ["title", "context"],
}


def and_filter(*conditions: dict) -> dict | None:
    """Combine {fieldId, operator, value} conditions; None when empty."""
    conditions = [c for c in conditions if c]
    if not conditions:
        return None
    return {"conjunction": "and", "filterSet": list(conditions)}


def list_records(table: str, *, filter: dict | None = None,
                 order_by: list | None = None, projection: list | None = None,
                 take: int = 100, skip: int = 0) -> dict:
    """One page of records. `filter` and `order_by` accept field NAMES on this
    instance as well as field IDs. `take` is capped at 1000 by the server."""
    pairs = [("fieldKeyType", "name"), ("take", take), ("skip", skip)]
    if filter is not None:
        pairs.append(("filter", json.dumps(filter)))
    if order_by is not None:
        pairs.append(("orderBy", json.dumps(order_by)))
    for field in projection or []:
        pairs.append(("projection", field))
    table_id = TABLES.get(table, table)
    return request("GET", f"/api/table/{table_id}/record",
                   query=urllib.parse.urlencode(pairs))


def iter_records(table: str, *, take: int = 1000, **kwargs):
    """Yield every record across all pages. 1000 is the server's max page."""
    skip = 0
    while True:
        page = list_records(table, take=take, skip=skip, **kwargs)
        records = page.get("records", [])
        if not records:
            return
        yield from records
        if len(records) < take:
            return
        skip += take


def get_record(table: str, record_id: str) -> dict:
    table_id = TABLES.get(table, table)
    return request("GET", f"/api/table/{table_id}/record/{record_id}",
                   query="fieldKeyType=name")


def create_records(table: str, records: list) -> list:
    """Create one or many records in a single call. Returns the new records."""
    table_id = TABLES.get(table, table)
    body = {"fieldKeyType": "name", "records": [{"fields": f} for f in records]}
    out = request("POST", f"/api/table/{table_id}/record", body=body)
    return out.get("records", [])


def update_record(table: str, record_id: str, fields: dict) -> dict:
    """Partial update -- omitted fields keep their values."""
    table_id = TABLES.get(table, table)
    body = {"fieldKeyType": "name", "record": {"fields": fields}}
    return request("PATCH", f"/api/table/{table_id}/record/{record_id}", body=body)


def update_records(table: str, updates: list) -> list:
    """Batch update from [{"id": rec, "fields": {...}}, ...]. Undocumented but
    verified working, and one round trip instead of N."""
    table_id = TABLES.get(table, table)
    body = {"fieldKeyType": "name", "records": updates}
    out = request("PATCH", f"/api/table/{table_id}/record", body=body)
    return out if isinstance(out, list) else out.get("records", [])


def delete_record(table: str, record_id: str) -> dict:
    table_id = TABLES.get(table, table)
    return request("DELETE", f"/api/table/{table_id}/record/{record_id}")


def delete_records(table: str, record_ids: list) -> list:
    """Batch delete. Undocumented but verified working. Deleting an
    already-deleted id returns 500, so never retry a partial failure blindly."""
    table_id = TABLES.get(table, table)
    query = "&".join(f"recordIds[]={urllib.parse.quote(i)}" for i in record_ids)
    out = request("DELETE", f"/api/table/{table_id}/record", query=query)
    return out.get("records", []) if isinstance(out, dict) else out


def decode_deleted(table: str, record: dict) -> dict:
    """DELETE responses key `fields` by field ID no matter what fieldKeyType
    was sent. Map them back to names."""
    by_id = {v: k for k, v in FIELD_IDS[table].items()}
    fields = {by_id.get(k, k): v for k, v in (record.get("fields") or {}).items()}
    return {"id": record.get("id"), "fields": fields}
