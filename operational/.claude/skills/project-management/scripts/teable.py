"""Shared helpers for the cybernetics-data Teable REST scripts. Never prints the token."""
import datetime as dt, json, os, re, sys, urllib.error, urllib.parse, urllib.request
from zoneinfo import ZoneInfo
from pathlib import Path

BASE = os.environ.get("CYBERNETICS_DATA_URL", "https://cybernetics.avarile.com").rstrip("/")
TZ = "Australia/Melbourne"
NO_VALUE = {"isEmpty", "isNotEmpty"}
MULTI = {"isAnyOf", "isNoneOf", "hasAnyOf", "hasAllOf", "hasNoneOf", "isExactly"}


def token():
    tok = os.environ.get("CYBERNETICS_DATA_API_TOKEN")
    if tok:
        return tok
    here = Path(__file__).resolve()  # a symlinked global install still finds the repo's .env
    for d in dict.fromkeys([Path.cwd(), *Path.cwd().parents, *here.parents]):
        env = d / ".env"
        if env.is_file():
            for line in env.read_text().splitlines():
                if line.startswith("CYBERNETICS_DATA_API_TOKEN="):
                    return line.split("=", 1)[1].strip().strip("'\"")
    sys.exit("CYBERNETICS_DATA_API_TOKEN not set (env or .env); use the MCP tools instead")


def call(method, path, params=None, body=None):
    url = BASE + path
    if params:
        url += "?" + urllib.parse.urlencode(params, doseq=True)
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method, headers={
        "Authorization": "Bearer " + token(),
        "User-Agent": "curl/8.4.0",  # the default Python-urllib UA is rejected with 403
        "Accept": "application/json",
        "Content-Type": "application/json",
    })
    try:
        raw = urllib.request.urlopen(req, timeout=60).read()
    except urllib.error.HTTPError as e:
        sys.exit("HTTP %s %s %s: %s" % (e.code, method, path, e.read()[:300].decode("utf8", "replace")))
    return json.loads(raw) if raw else None


def parse_filter(spec):
    """'FIELD_ID OPERATOR [VALUE]'; VALUE date:YYYY-MM-DD -> exactDate; multi-value ops are comma-separated."""
    parts = spec.split(" ", 2)
    if len(parts) < 2:
        sys.exit("bad filter %r: need 'FIELD_ID OPERATOR [VALUE]'" % spec)
    field, op = parts[0], parts[1]
    raw = parts[2] if len(parts) == 3 else None
    if op in NO_VALUE:
        value = None
    elif op in MULTI:
        value = raw.split(",")
    elif raw and raw.startswith("date:"):
        value = {"mode": "exactDate", "exactDate": raw[5:] + "T00:00:00.000Z", "timeZone": TZ}
    else:
        value = raw
    return {"fieldId": field, "operator": op, "value": value}


def and_filter(specs):
    return {"conjunction": "and", "filterSet": [parse_filter(s) for s in specs]} if specs else None


def get_records(table, filt=None, projection=(), take=1000):
    out, skip = [], 0
    while True:
        params = [("fieldKeyType", "id"), ("take", min(take, 1000)), ("skip", skip)]
        params += [("projection[]", f) for f in projection]
        if filt:
            params.append(("filter", json.dumps(filt)))
        page = call("GET", "/api/table/%s/record" % table, params)["records"]
        out += page
        if len(page) < min(take, 1000) or len(out) >= take:
            return out
        skip += len(page)


def get_record(table, rec_id, projection=()):
    params = [("fieldKeyType", "id")] + [("projection[]", f) for f in projection]
    return call("GET", "/api/table/%s/record/%s" % (table, rec_id), params)


def parse_value(raw):
    try:
        return json.loads(raw)
    except ValueError:
        return raw


def local_date(iso):
    """API returns UTC timestamps; dates are meant in Australia/Melbourne. None-safe."""
    if not iso:
        return None
    return dt.datetime.fromisoformat(iso.replace("Z", "+00:00")).astimezone(ZoneInfo(TZ)).date()


def today():
    return dt.datetime.now(ZoneInfo(TZ)).date()


def delete_records(table, ids):
    """Hard delete (goes to the table trash). Tries repeated `recordIds`, then `recordIds[]`."""
    for key in ("recordIds", "recordIds[]"):
        try:
            return call("DELETE", "/api/table/%s/record" % table, [(key, i) for i in ids])
        except SystemExit as e:
            last = e
    raise last


def delete_view(table, view_id):
    return call("DELETE", "/api/table/%s/view/%s" % (table, view_id))


CONTACTS, CONTACT_TITLE = "tbl6730ZOe0zToNrcIr", "fldlcgf8tb0mWkzv3Rd"


def contact_names():
    """{record id: name} for every contact (small table)."""
    return {r["id"]: r["fields"].get(CONTACT_TITLE) or "" for r in get_records(CONTACTS, projection=[CONTACT_TITLE])}


def resolve_contact(ref):
    """Name or record id -> (id, name); 'none'/'unassign' -> (None, None). Exits on no match or ambiguity (never guesses)."""
    if ref is None or ref.strip().lower() in ("none", "unassign", "unassigned", "-"):
        return None, None
    ref = ref.strip()
    if re.fullmatch(r"rec[A-Za-z0-9]{16}", ref):
        r = get_record(CONTACTS, ref, [CONTACT_TITLE])
        return r["id"], r["fields"].get(CONTACT_TITLE)
    recs = get_records(CONTACTS, and_filter(["%s contains %s" % (CONTACT_TITLE, ref)]), [CONTACT_TITLE])
    exact = [r for r in recs if (r["fields"].get(CONTACT_TITLE) or "").strip().lower() == ref.lower()]
    pick = exact if len(exact) == 1 else recs
    if not pick:
        sys.exit("no contact matches %r (contacts: %s)" % (ref, ", ".join(sorted(contact_names().values()))))
    if len(pick) > 1:
        sys.exit("ambiguous contact %r: %s -- use the full name or the record id" % (ref, "; ".join("%s (%s)" % (r["fields"].get(CONTACT_TITLE), r["id"]) for r in pick)))
    return pick[0]["id"], pick[0]["fields"].get(CONTACT_TITLE)


_CN = None


def contact_name(cid):
    """Contact display name by record id (cached; refreshed once on a miss). Needed because the link label of
    projects.lead_by is the contact's EMAIL, not the name."""
    global _CN
    if _CN is None or cid not in _CN:
        _CN = contact_names()
    return _CN.get(cid)


# --- day planning tables (daily_plans, day_blocks, routines) ---------------------------------------------------------
TASKS_ID, PROJECTS_ID = "tblOMgDiajqa1moRRjE", "tbliD8gcOTRk9RZ9SmR"
PLANS, BLOCKS, ROUTINES = "tblwUxgw2YgU0Zm67e6", "tbl8nr9z2dZEJHcEiUn", "tblwb4WWe9Hw7r3BIzn"
PLAN = dict(date="fldJ7lDiVIaMgpEJmDj", goal="fldSHFsOcQRq1YXGfqM", focus="fldWtTWlVudAAaQwhuy", status="fld2abfT6ehoPtdWTa4",
            capacity="fldiby5lp2qT2IU3IVs", ctx="fldXmne6mW8Xpkmq7EA", review="fld1nag746vMJc3UvEE", notes="fldeKU7bUxELTBcagmt",
            active="fldTAzKHlDaUvRsh53T", deleted="fldIr1WNg6g45K8UrUc", blocks="fldnz1MisFxXbFISvSf")
BLOCK = dict(title="fldtRZW60moxChIA1mb", day="fldKasFde0zQQLEb4qi", task="fldOQcUAwEzRbhCy0vV", kind="fldK1gAFmolw5ZNHTWM",
             status="fldStji12ZpAomeQhPz", order="fldA9KGAERqhstiX1H1", start="fld5BHdbS7RVL2qQILK", minutes="fldrGrVgBmWXDShODOt",
             actual_start="fldnxj4thkYKgMyJvcK", actual_minutes="fldf7pKThqQLnJ6G7uX", reason="flde9uVADhsWsQlJ7ey", notes="fldV7saC9Pn6QXMn02A",
             active="fldEjEBUiVdmbkjTiAK", deleted="fldRDTx4aBvdoVmajhH", source="fldreE16ZFdJ1rcc1MV", routine="fld15qEPrgEoKSqAJkQ",
             replaces="fldiuowC8CC70d5IRrN")
ROUTINE = dict(title="fldw3FxsebE1ztrGIgP", kind="fldRJZXQYHKHM5Dp2Px", freq="fldFxLJaPuTXVx2pehW", weekdays="fldGZj2x13i1OSGULT2",
               month_day="fld9zqW2uL3heMqnfFL", start="fldMDbrc8V3wBUZJm7L", minutes="fldGCx4sZKzr7pX1Rj2", valid_from="fldh4UPUsDzSORZRBaK",
               valid_until="fldQltwtwKYFjTulBof", active="fldByDXoUfOy1H4Z6I0", notes="fldiyNJpR9T5DdxqVZf", task="fldr9Purk0NhK1qwciM")
TASK_X = dict(notes="fldfsST2ZFpRjmPeqmk", collab="fld8kFQbfW9VIv6V1AB", gen="fldzaFydh9DtnOPvZA7", blocks="fldJvbs2pOhdg5xcq4I",
              know="fldJzsKyzBaDFt7bHIu", started="fldj3Xb1g9nUX4iFqE0", finished="fldn95wbkTqefn18WdO")
PROJECT_X = dict(notes="fld3QM0WdioiHSb7GVe", collab="fldgB1KhSop61Qpyssn", gen="fldxNdiG9qUupVLW0iF", know="fldCw3cnpw8EWs09C1v")
CONTACT_TYPE = "fldDFnZypupBS2dbhqG"


def now():
    return dt.datetime.now(ZoneInfo(TZ))


def local_dt(iso):
    """UTC timestamp from the API -> aware Melbourne datetime. None-safe."""
    if not iso:
        return None
    return dt.datetime.fromisoformat(iso.replace("Z", "+00:00")).astimezone(ZoneInfo(TZ))


def utc_iso(day, minute):
    """Local date + minutes since local midnight -> the UTC timestamp the API stores. zoneinfo handles daylight saving."""
    local = dt.datetime(day.year, day.month, day.day, minute // 60, minute % 60, tzinfo=ZoneInfo(TZ))
    return local.astimezone(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")


def create(table, rows):
    """Create records (list of {fieldId: value}); returns the created records. Batches of 100."""
    out = []
    for i in range(0, len(rows), 100):
        res = call("POST", "/api/table/%s/record" % table, body={"fieldKeyType": "id", "records": [{"fields": r} for r in rows[i:i + 100]]})
        out += res["records"]
    return out


def update(table, rec_id, fields):
    return call("PATCH", "/api/table/%s/record/%s" % (table, rec_id), body={"fieldKeyType": "id", "record": {"fields": fields}})
