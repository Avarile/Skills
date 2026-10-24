"""Finance data layer for cybernetics-data: periods, filtered fetch, lookups, name resolution, coverage.

Importable (no network on import). Pure helpers (`resolve_period`, `Period`) need no token.

    import findata as D
    p = D.resolve_period("3m")                       # trailing 3 complete calendar months (D-3)
    txns = D.load_txns(p, types=["Expense"], categories=["Food"])
    D.coverage()                                     # first/last transaction date
    D.server_sum(p, types=["Expense"])               # independent server-side total (cross-check)

Dates: every Date is read as an Australia/Melbourne local date (`teable.local_date`); filters send
Melbourne-midnight instants, which is the only form the server matches by local day (verified 2026-10-05).
Names (category, payee, account, tag) resolve by id, exact name, full path or unique partial; ambiguity
or no match raises `Ambiguous` / `NotFound` with candidates (never guesses).
"""
import calendar, dataclasses, datetime as dt, difflib, json, os, re, sys, time, urllib.error
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parent))
import teable as T

TX, ACC, CAT, PAY, TAG, BUD = ("tblylfLkXFkYH2qB0ZQ", "tblJLklwpGwbrfDlwIz", "tblp2Jvb2g90PN3fX4d",
                               "tblpyC3PfoG0DN8dQ2t", "tblhOQKXpSzr0Ezh8rR", "tblDk3iXFz5YiYUkwz6")
FX = dict(desc="fldRZcBYKr6w2GWw5lm", date="fldZIgdLJ79xoDQK5u4", type="fldIqRcX7gZ1zn9Kmz0",
          amount="flde1ox2n7Q30UUP938", recurring="fldAiqG7oB0DCPeDL7K", freq="fldTMF1faN48Lrd3vS4",
          notes="fldW2RsBfTxd362FjfO", account="fldcg0wB2iVE8DZCVHm", transfer_account="fldIeT7aNuRjEAVlyqL",
          category="fldlU2BpJBZFcNcFhom", payee="fld8WNu5jDIr55RNkSu", tags="fldXRiV3NxrspHNLQFO",
          budget="fldVYJYqgs9p2GQSf9a", scope="fldV9EFPhFI8W0OOMbF")
FA = dict(name="fldSzvd0NAglB9qhsp1", scope="fldZFxk5O8qT6AF6QV2", type="fldaZgFxywk8cZT9l8V",
          institution="fldEHOdmX1nYcAaaybH", opening="fldiOOafvV1UPDJtV1f", opening_date="fldBjBPMxjYpGxs0yJ5",
          active="fldRyzp4jLRtGqUd6gu", balance="fldSTUAw8v0UMcTivzf")
FC = dict(name="flddvHdoGLLLyFYTXlM", type="fldBazKuxdsorHnlCmZ", scope="flddiHU2kAnTeZG49P4",
          parent="fldmknXtvhmpIUmjTcP", path="fldZZlGOiOHRb84DjDV")
FP = dict(name="fldnbT296ypPXkiJkkF", type="fldJ8YwtDNxCKZvPNVO", scope="fldf7p7Ub27gXLzi7nP",
          default="fld6XnWnCCu7GsWfJzh")
FG = dict(name="fldie2h6YM3fA6WPH0Z", color="fldZQDvslg2GJfBTE9K")
FB = dict(month="fldzRSk36rF2iLqoc1A", planned="fldJXYFV5eXNnALW40c", category="fldfCZXAsjS3nEM0MGW")
TYPES = ("Income", "Expense", "Transfer")
MEL = ZoneInfo(T.TZ)
ALL = 10 ** 9  # teable.get_records stops at `take` rows (default 1000): always pass ALL for full reads

CALLS = [0]
_call = T.call


def _counted(*a, **k):
    """Counts requests; retries a GET twice on a dropped connection (teable.call only handles HTTP errors).
    Writes are never retried: the server may have applied them before the connection dropped."""
    method = a[0] if a else k.get("method")
    for attempt in range(3 if method == "GET" else 1):
        CALLS[0] += 1
        try:
            return _call(*a, **k)
        except (urllib.error.URLError, ConnectionError, TimeoutError, OSError) as e:
            if isinstance(e, urllib.error.HTTPError) or method != "GET" or attempt == 2:
                raise
            time.sleep(1 + 2 * attempt)


T.call = _counted  # teable.get_records resolves `call` from its module globals, so this counts every request


class NotFound(LookupError):
    def __init__(self, kind, ref, candidates=()):
        self.kind, self.ref, self.candidates = kind, ref, list(candidates)
        super().__init__("no %s matches %r%s" % (kind, ref, "; did you mean: " + ", ".join(self.candidates) if self.candidates else ""))


class Ambiguous(LookupError):
    def __init__(self, kind, ref, candidates):
        self.kind, self.ref, self.candidates = kind, ref, list(candidates)
        super().__init__("%r matches several %s: %s" % (ref, kind, ", ".join(self.candidates)))


# ---------- periods ----------

@dataclasses.dataclass(frozen=True)
class Period:
    start: dt.date  # inclusive
    end: dt.date    # exclusive
    label: str

    @property
    def days(self):
        return (self.end - self.start).days

    @property
    def last(self):
        return self.end - dt.timedelta(days=1)

    @property
    def months(self):
        """Whole calendar months when month-aligned, else days / average month length."""
        if self.start.day == 1 and self.end.day == 1:
            return (self.end.year - self.start.year) * 12 + self.end.month - self.start.month
        return self.days / 30.4375

    def to_dict(self):
        return dict(label=self.label, start=self.start.isoformat(), end=self.last.isoformat(),
                    days=self.days, months=round(self.months, 2))


def add_months(d, n):
    y, m = divmod(d.month - 1 + n, 12)
    return dt.date(d.year + y, m + 1, min(d.day, calendar.monthrange(d.year + y, m + 1)[1]))


def month_start(d):
    return d.replace(day=1)


def fy_start(fy):
    """Australian financial year: FY2026 = 2025-07-01 .. 2026-06-30."""
    return dt.date(fy - 1, 7, 1)


def fy_of(d):
    return d.year + 1 if d.month >= 7 else d.year


def _date(s):
    return dt.date.fromisoformat(s)


PERIOD_HELP = ("mtd | last-month (= month, 1m) | Nm (3m, 6m, 12m = year: trailing complete months) | Nd (last N days) | "
               "YYYY-MM | qtd | ytd | YYYY | last-year | fy | fy2026 | fytd | last-fy | all | "
               "YYYY-MM-DD..YYYY-MM-DD | YYYY-MM..YYYY-MM")


def resolve_period(spec="last-month", today=None, anchor=None):
    """Period spec -> Period. `anchor` (YYYY-MM) is the last complete month for Nm / last-month (default: the
    month before today's). Raises ValueError on an unknown spec."""
    today = today or T.today()
    s = (spec or "last-month").strip().lower().replace("_", "-").replace(" ", "")
    s = {"month": "last-month", "1m": "last-month", "year": "12m", "this-month": "mtd", "this-year": "ytd",
         "last-12m": "12m", "last-3m": "3m", "last-6m": "6m"}.get(s, s)
    cur = month_start(today)
    last_full_end = add_months(_date(anchor + "-01"), 1) if anchor else cur  # exclusive end of the last complete month
    m = re.fullmatch(r"(?:last-)?(\d+)m", s)
    if s == "last-month" or m:
        n = int(m.group(1)) if m else 1
        start = add_months(last_full_end, -n)
        lab = start.strftime("%Y-%m") if n == 1 else "%d months %s..%s" % (n, start.strftime("%Y-%m"), add_months(last_full_end, -1).strftime("%Y-%m"))
        return Period(start, last_full_end, lab)
    if s == "mtd":
        return Period(cur, today + dt.timedelta(days=1), "%s MTD (to %s)" % (cur.strftime("%Y-%m"), today))
    m = re.fullmatch(r"(?:last-)?(\d+)d(?:ays)?", s) or re.fullmatch(r"last-(\d+)-days", s)
    if m:
        n = int(m.group(1))
        return Period(today - dt.timedelta(days=n - 1), today + dt.timedelta(days=1), "last %d days" % n)
    m = re.fullmatch(r"(?:month:)?(\d{4})-(\d{2})", s)
    if m:
        start = dt.date(int(m.group(1)), int(m.group(2)), 1)
        return Period(start, add_months(start, 1), start.strftime("%Y-%m"))
    if s == "qtd":
        q = dt.date(today.year, 3 * ((today.month - 1) // 3) + 1, 1)
        return Period(q, today + dt.timedelta(days=1), "Q%d %d to date" % ((q.month + 2) // 3, q.year))
    if s == "ytd":
        return Period(dt.date(today.year, 1, 1), today + dt.timedelta(days=1), "%d YTD" % today.year)
    m = re.fullmatch(r"(?:year:)?(\d{4})", s)
    if m or s == "last-year":
        y = int(m.group(1)) if m else today.year - 1
        return Period(dt.date(y, 1, 1), dt.date(y + 1, 1, 1), str(y))
    m = re.fullmatch(r"fy:?(\d{4})", s)
    if m or s in ("fy", "last-fy", "fytd"):
        fy = int(m.group(1)) if m else fy_of(today) - (s == "last-fy")
        if s == "fytd":
            return Period(fy_start(fy), today + dt.timedelta(days=1), "FY%d to date" % fy)
        return Period(fy_start(fy), fy_start(fy + 1), "FY%d (Jul %d-Jun %d)" % (fy, fy - 1, fy))
    if s == "all":
        return Period(dt.date(1900, 1, 1), today + dt.timedelta(days=1), "all time")
    m = re.fullmatch(r"(\d{4}-\d{2}(?:-\d{2})?)\.\.(\d{4}-\d{2}(?:-\d{2})?)", s)
    if m:
        a, b = m.groups()
        start = _date(a if len(a) == 10 else a + "-01")
        end = _date(b) + dt.timedelta(days=1) if len(b) == 10 else add_months(_date(b + "-01"), 1)
        if end <= start:
            raise ValueError("empty period %r: end is before start" % spec)
        return Period(start, end, "%s..%s" % (start, end - dt.timedelta(days=1)))
    raise ValueError("unknown period %r; use one of: %s" % (spec, PERIOD_HELP))


def instant(day):
    """Melbourne midnight of `day` as a UTC ISO instant (DST-aware). Used for filters (the server compares
    instants) and for date writes: a plain YYYY-MM-DD on a DST-change day is stored with the wrong offset
    (2026-10-04 -> 2026-10-03T13:00Z, which is 3 Oct 23:00 local; verified 2026-10-05)."""
    return dt.datetime(day.year, day.month, day.day, tzinfo=MEL).astimezone(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")


def _exact(day):
    return {"mode": "exactDate", "exactDate": instant(day), "timeZone": T.TZ}


# ---------- lookups and resolution ----------

_LOOKUPS = {}


def _title(v):
    return v.get("title") if isinstance(v, dict) else None


def _id(v):
    return v.get("id") if isinstance(v, dict) else None


def categories():
    if "cat" not in _LOOKUPS:
        out = {}
        for r in T.get_records(CAT, projection=list(FC.values()), take=ALL):
            f = r["fields"]
            out[r["id"]] = dict(id=r["id"], name=f.get(FC["name"]) or "", type=f.get(FC["type"]),
                                scope=f.get(FC["scope"]), parent=_id(f.get(FC["parent"])),
                                path=f.get(FC["path"]) or f.get(FC["name"]) or "")
        _LOOKUPS["cat"] = out
    return _LOOKUPS["cat"]


def payees():
    if "pay" not in _LOOKUPS:
        _LOOKUPS["pay"] = {r["id"]: dict(id=r["id"], name=r["fields"].get(FP["name"]) or "", type=r["fields"].get(FP["type"]),
                                         scope=r["fields"].get(FP["scope"]), default=_id(r["fields"].get(FP["default"])))
                           for r in T.get_records(PAY, projection=list(FP.values()), take=ALL)}
    return _LOOKUPS["pay"]


def accounts():
    if "acc" not in _LOOKUPS:
        out = {}
        for r in T.get_records(ACC, projection=list(FA.values()), take=ALL):
            f = r["fields"]
            out[r["id"]] = dict(id=r["id"], name=f.get(FA["name"]) or "", scope=f.get(FA["scope"]), type=f.get(FA["type"]),
                                institution=f.get(FA["institution"]), opening=f.get(FA["opening"]) or 0.0,
                                opening_date=T.local_date(f.get(FA["opening_date"])), active=f.get(FA["active"]) is True,
                                balance=f.get(FA["balance"]))
        _LOOKUPS["acc"] = out
    return _LOOKUPS["acc"]


def tags():
    if "tag" not in _LOOKUPS:
        _LOOKUPS["tag"] = {r["id"]: dict(id=r["id"], name=r["fields"].get(FG["name"]) or "", color=r["fields"].get(FG["color"]))
                           for r in T.get_records(TAG, projection=list(FG.values()), take=ALL)}
    return _LOOKUPS["tag"]


def budgets():
    """Budget rows: {id: {month (date, 1st), category id, planned}}."""
    if "bud" not in _LOOKUPS:
        out = {}
        for r in T.get_records(BUD, projection=list(FB.values()), take=ALL):
            f = r["fields"]
            m = T.local_date(f.get(FB["month"]))
            out[r["id"]] = dict(id=r["id"], month=m.replace(day=1) if m else None, category=_id(f.get(FB["category"])),
                                planned=f.get(FB["planned"]) or 0.0)
        _LOOKUPS["bud"] = out
    return _LOOKUPS["bud"]


def forget_lookups(*keys):
    """Drop cached lookups (after a write). No keys = all."""
    for k in keys or list(_LOOKUPS):
        _LOOKUPS.pop(k, None)


KINDS = {"category": categories, "payee": payees, "account": accounts, "tag": tags}


def resolve(kind, ref):
    """One name/id -> record dict. Order: record id, exact name (case-insensitive), exact full path, unique partial."""
    table = KINDS[kind]()
    ref = (ref or "").strip()
    if ref in table:
        return table[ref]
    low = ref.lower()
    for key in ("name", "path"):
        hit = [r for r in table.values() if (r.get(key) or "").lower() == low]
        if len(hit) == 1:
            return hit[0]
        if len(hit) > 1:
            raise Ambiguous(kind, ref, sorted(r.get("path") or r["name"] for r in hit))
    hit = [r for r in table.values() if low and low in (r.get("path") or r["name"]).lower()]
    if len(hit) == 1:
        return hit[0]
    if len(hit) > 1:
        raise Ambiguous(kind, ref, sorted(r.get("path") or r["name"] for r in hit))
    names = [r["name"] for r in table.values()]
    raise NotFound(kind, ref, difflib.get_close_matches(ref, names, n=5, cutoff=0.5))


def resolve_many(kind, refs, with_children=True):
    """List (or comma string) of refs -> list of ids. Categories include their sub-categories."""
    if isinstance(refs, str):
        refs = [x for x in refs.split(",")]
    ids = []
    for ref in refs or []:
        if not ref.strip():
            continue
        rid = resolve(kind, ref)["id"]
        ids.append(rid)
        if kind == "category" and with_children:
            cats, todo = categories(), [rid]
            while todo:
                cur = todo.pop()
                kids = [c["id"] for c in cats.values() if c["parent"] == cur]
                ids += kids
                todo += kids
    return list(dict.fromkeys(ids))


# ---------- transactions ----------

@dataclasses.dataclass
class Txn:
    id: str
    date: dt.date
    type: str
    amount: float
    description: str = ""
    notes: str = ""
    account: str = None
    account_id: str = None
    account_scope: str = None
    transfer_account: str = None
    category: str = None
    category_id: str = None
    payee: str = None
    payee_id: str = None
    tags: tuple = ()
    recurring: bool = False
    frequency: str = None
    budget_id: str = None
    category_type: str = None   # filled by enrich()
    category_scope: str = None  # filled by enrich()

    @property
    def signed(self):
        return self.amount if self.type == "Income" else -self.amount

    @property
    def scope(self):
        """D-4: category scope (Personal / Business / Shared); falls back to the account's scope."""
        return self.category_scope or self.account_scope or "Personal"

    def to_dict(self):
        d = dataclasses.asdict(self)
        d["date"] = self.date.isoformat()
        d["tags"] = list(self.tags)
        d["scope"] = self.scope
        return d


TX_PROJECTION = [FX[k] for k in ("desc", "date", "type", "amount", "recurring", "freq", "notes", "account",
                                 "transfer_account", "category", "payee", "tags", "budget", "scope")]


def to_txn(r):
    f = r["fields"]
    return Txn(id=r["id"], date=T.local_date(f.get(FX["date"])), type=f.get(FX["type"]), amount=float(f.get(FX["amount"]) or 0),
               description=f.get(FX["desc"]) or "", notes=f.get(FX["notes"]) or "",
               account=_title(f.get(FX["account"])), account_id=_id(f.get(FX["account"])), account_scope=f.get(FX["scope"]),
               transfer_account=_title(f.get(FX["transfer_account"])),
               category=_title(f.get(FX["category"])), category_id=_id(f.get(FX["category"])),
               payee=_title(f.get(FX["payee"])), payee_id=_id(f.get(FX["payee"])),
               tags=tuple(x.get("title") for x in f.get(FX["tags"]) or []), recurring=f.get(FX["recurring"]) is True,
               frequency=f.get(FX["freq"]), budget_id=_id(f.get(FX["budget"])))


def enrich(txns):
    """Fill category type/scope and current category names from the categories table (1 call, cached)."""
    cats = categories()
    for t in txns:
        c = cats.get(t.category_id)
        if c:
            t.category, t.category_type, t.category_scope = c["path"], c["type"], c["scope"]
    return txns


def _cond(field, op, value=None):
    return {"fieldId": field, "operator": op, "value": value}


def build_filter(period=None, *, types=None, categories=None, payees=None, accounts=None, tags=None, text=None,
                 min_amount=None, max_amount=None, recurring=None, uncategorized=False, exclude_categories=None,
                 exclude_payees=None):
    """Server-side filter. Name/id lists are resolved (raises NotFound/Ambiguous). `text`: every term must match
    the description, notes or payee name (case-insensitive)."""
    fs = []
    if period:
        fs += [_cond(FX["date"], "isOnOrAfter", _exact(period.start)), _cond(FX["date"], "isBefore", _exact(period.end))]
    if types:
        bad = [x for x in types if x not in TYPES]
        if bad:
            raise ValueError("unknown type %s; use %s" % (bad, ", ".join(TYPES)))
        fs.append(_cond(FX["type"], "isAnyOf", list(types)))
    if uncategorized:
        fs.append(_cond(FX["category"], "isEmpty"))
    for kind, refs, field, op in (("category", categories, "category", "isAnyOf"), ("payee", payees, "payee", "isAnyOf"),
                                  ("account", accounts, "account", "isAnyOf"), ("tag", tags, "tags", "hasAnyOf")):
        if refs:
            fs.append(_cond(FX[field], op, resolve_many(kind, refs)))
    if exclude_categories:  # isNoneOf keeps rows without a category
        fs.append(_cond(FX["category"], "isNoneOf", resolve_many("category", exclude_categories)))
    if exclude_payees:  # isNoneOf keeps rows without a payee
        fs.append(_cond(FX["payee"], "isNoneOf", resolve_many("payee", exclude_payees)))
    for w in (text.split() if isinstance(text, str) else list(text or [])):  # a list keeps phrases whole
        fs.append({"conjunction": "or", "filterSet": [_cond(FX["desc"], "contains", w), _cond(FX["notes"], "contains", w),
                                                      _cond(FX["payee"], "contains", w)]})
    if min_amount is not None:
        fs.append(_cond(FX["amount"], "isGreaterEqual", float(min_amount)))
    if max_amount is not None:
        fs.append(_cond(FX["amount"], "isLessEqual", float(max_amount)))
    if recurring is not None:
        fs.append(_cond(FX["recurring"], "is", bool(recurring)))
    return {"conjunction": "and", "filterSet": fs} if fs else None


def load_txns(period=None, *, scope=None, enrich_categories=None, **filters):
    """Filtered transactions as Txn, sorted by date. `scope` (Personal / Business) is applied client-side on the
    category scope (Shared counts in both, D-4). Categories are enriched when `scope` is given or
    `enrich_categories` is true (one extra call, cached)."""
    filt = build_filter(period, **filters)
    rows = [to_txn(r) for r in T.get_records(TX, filt, TX_PROJECTION, take=ALL)]
    if period:  # belt and braces: the server filter is by instant; keep exactly the local-date range
        rows = [t for t in rows if t.date and period.start <= t.date < period.end]
    if scope or enrich_categories:
        enrich(rows)
    if scope:
        want = scope.capitalize()
        if want not in ("Personal", "Business"):
            raise ValueError("scope must be Personal or Business")
        rows = [t for t in rows if t.scope in (want, "Shared")]
    rows.sort(key=lambda t: (t.date, t.description, t.id))
    return rows


def coverage():
    """First and last transaction date over the whole table (1 aggregation call, cached)."""
    if "cov" not in _LOOKUPS:
        res = T.call("GET", "/api/table/%s/aggregation" % TX, [("field[earliestDate][]", FX["date"]), ("field[latestDate][]", FX["date"])])
        got = {a["total"]["aggFunc"]: a["total"]["value"] for a in res["aggregations"]}
        first, last = T.local_date(got.get("earliestDate")), T.local_date(got.get("latestDate"))
        _LOOKUPS["cov"] = dict(first=first, last=last, age_days=(T.today() - last).days if last else None)
    return _LOOKUPS["cov"]


def coverage_warnings(period):
    """Why a period's totals may be incomplete: it starts before the first or ends after the last transaction."""
    cov, out = coverage(), []
    if not cov["last"] or not period:
        return out
    if period.start > cov["last"]:
        return ["no data in this period yet (last transaction %s)" % cov["last"]]
    if period.end <= cov["first"]:
        return ["no data in this period (first transaction %s)" % cov["first"]]
    if period.label == "all time":
        return out
    if period.start < cov["first"]:
        out.append("data starts %s, so %s..%s is not covered" % (cov["first"], period.start, cov["first"] - dt.timedelta(days=1)))
    if period.last > cov["last"]:
        out.append("no data after %s, so %s..%s is missing or partial" % (cov["last"], cov["last"] + dt.timedelta(days=1), period.last))
    return out


def coverage_note(period=None, rows=None, label=True):
    """One line: period, rows used, data coverage, and any coverage warnings."""
    cov = coverage()
    parts = []
    if period:
        dates = "%s..%s" % (period.start, period.last) if period.label != "all time" else "all time"
        parts.append(("%s (%s)" % (period.label, dates) if period.label != "all time" else dates) if label else dates)
    if rows is not None:
        parts.append("%d rows" % rows)
    if cov["last"]:
        parts.append("data %s..%s (%d days old)" % (cov["first"], cov["last"], cov["age_days"]))
        parts += ["WARNING: " + w for w in coverage_warnings(period)]
    return " · ".join(parts)


def server_sum(period=None, field="amount", **filters):
    """Server-side sum of a transaction number field under the same filter as load_txns (no scope)."""
    filt = build_filter(period, **filters)
    params = [("field[sum][]", FX[field])]
    if filt:
        params.append(("filter", json.dumps(filt)))
    res = T.call("GET", "/api/table/%s/aggregation" % TX, params)
    return round(float(res["aggregations"][0]["total"]["value"] or 0), 2)


# ---------- writes (callers preview first; nothing here runs without an explicit call) ----------

class Blocked(Exception):
    """A write refused by a check (bad option, duplicate, too many rows, verify failure)."""


UNDO_DIR = Path(os.environ.get("FIN_UNDO_DIR") or Path.home() / ".cache" / "finance-management" / "undo")
MAX_ROWS = 500
_META = {}


def field_meta(table):
    if table not in _META:
        _META[table] = {f["id"]: f for f in T.call("GET", "/api/table/%s/field" % table)}
    return _META[table]


def validate(table, fields):
    """Unknown or computed fields and invalid select options raise Blocked (the API would silently clear a
    select given a wrong option)."""
    meta = field_meta(table)
    for k, v in fields.items():
        f = meta.get(k)
        if f is None:
            raise Blocked("unknown field %s on table %s" % (k, table))
        if f.get("isComputed"):
            raise Blocked("field %r is computed and read-only" % f["name"])
        if f["type"] in ("singleSelect", "multipleSelect") and v is not None:
            names = [c["name"] for c in f["options"]["choices"]]
            bad = [x for x in (v if isinstance(v, list) else [v]) if x not in names]
            if bad:
                raise Blocked("invalid option %r for %s; valid: %s" % (bad, f["name"], ", ".join(names)))


def _link_ids(v):
    if v is None:
        return []
    return sorted(x["id"] for x in (v if isinstance(v, list) else [v]))


def _same(meta, want, got):
    t = meta["type"]
    if t == "link":
        return _link_ids(want) == _link_ids(got)
    if t == "checkbox":
        return bool(want) == bool(got)
    if t == "date":
        if want is None:
            return not got
        want_day = T.local_date(want) if "T" in str(want) else dt.date.fromisoformat(str(want)[:10])
        return bool(got) and T.local_date(got) == want_day
    if t == "number":
        return (want is None and got is None) or (got is not None and want is not None and abs(float(got) - float(want)) < 0.005)
    return (want or None) == (got or None)


def verify(table, rec_id, fields):
    """Read one record back and compare every written field; raises Blocked on mismatch."""
    got = T.get_record(table, rec_id, list(fields)).get("fields", {})
    meta = field_meta(table)
    bad = [meta[k]["name"] for k, v in fields.items() if not _same(meta[k], v, got.get(k))]
    if bad:
        raise Blocked("VERIFY FAILED on %s: %s (inspect the record in Teable)" % (rec_id, ", ".join(bad)))


def save_undo(op, table, before=None, created=None):
    """Write an undo file: previous values of updated records and ids of created ones. Returns its path."""
    UNDO_DIR.mkdir(parents=True, exist_ok=True)
    stamp = dt.datetime.now(MEL).strftime("%Y%m%d-%H%M%S")
    path = UNDO_DIR / ("%s-%s.json" % (stamp, op))
    n = 1
    while path.exists():
        n += 1
        path = UNDO_DIR / ("%s-%s-%d.json" % (stamp, op, n))
    path.write_text(json.dumps(dict(op=op, table=table, at=stamp, before=before or {}, created=created or []), indent=1))
    path.chmod(0o600)
    return path


def _writable(meta, v):
    """A value read from the API -> the shape the API accepts on write."""
    if meta["type"] == "link" and v is not None:
        return [{"id": x["id"]} for x in v] if isinstance(v, list) else {"id": v["id"]}
    return v


def snapshot(table, ids, fields):
    """{record id: {field: writable previous value}} for an undo file."""
    meta = field_meta(table)
    out = {}
    for rid in ids:
        f = T.get_record(table, rid, list(fields)).get("fields", {})
        out[rid] = {k: _writable(meta[k], f.get(k)) for k in fields}
    return out


def update_many(table, changes, op):
    """changes: {record id: {field: value}}. Validates, snapshots previous values to an undo file, PATCHes in
    batches of 100, verifies every record. Returns the undo path."""
    if not changes:
        return None
    if len(changes) > MAX_ROWS:
        raise Blocked("refusing: %d records exceeds the %d-row limit; narrow the selection" % (len(changes), MAX_ROWS))
    fields = sorted({k for v in changes.values() for k in v})
    for v in changes.values():
        validate(table, v)
    undo = save_undo(op, table, before=snapshot(table, list(changes), fields))
    items = list(changes.items())
    for i in range(0, len(items), 100):
        T.call("PATCH", "/api/table/%s/record" % table, body={
            "fieldKeyType": "id", "typecast": False, "records": [{"id": rid, "fields": f} for rid, f in items[i:i + 100]]})
    for rid, f in items:
        verify(table, rid, f)
    forget_lookups()
    return undo


def create_many(table, rows, op):
    """rows: list of {field: value}. Validates, creates, records the new ids in an undo file, verifies."""
    if len(rows) > MAX_ROWS:
        raise Blocked("refusing: %d rows exceeds the %d-row limit" % (len(rows), MAX_ROWS))
    for f in rows:
        validate(table, f)
    res = T.call("POST", "/api/table/%s/record" % table, body={"fieldKeyType": "id", "typecast": False,
                                                                "records": [{"fields": f} for f in rows]})
    ids = [r["id"] for r in res["records"]]
    undo = save_undo(op, table, created=ids)
    try:
        for rid, f in zip(ids, rows):
            verify(table, rid, f)
    except Blocked as e:
        raise Blocked("%s; created %s anyway (remove with: fin.py undo %s)" % (e, ", ".join(ids), undo))
    forget_lookups()
    return ids, undo


def undo(path, apply=False):
    """Restore an undo file: previous values are written back, created records are deleted (to the table
    trash). Returns a plan dict; writes only with apply=True."""
    data = json.loads(Path(path).read_text())
    plan = dict(file=str(path), op=data["op"], table=data["table"], restore=len(data["before"]), delete=len(data["created"]))
    if apply:
        if data["before"]:
            update_many(data["table"], data["before"], "undo-" + data["op"])
        if data["created"]:
            T.delete_records(data["table"], data["created"])
        forget_lookups()
    return plan


# ---------- domain writes ----------

def find_duplicates_of(day, amount, payee_id=None, description=None):
    """Existing transactions on the same local date with the same amount and payee (or description)."""
    p = Period(day, day + dt.timedelta(days=1), str(day))
    rows = load_txns(p, min_amount=amount - 0.005, max_amount=amount + 0.005)
    return [t for t in rows if (payee_id and t.payee_id == payee_id) or (description and t.description.strip().lower() == description.strip().lower())]


def plan_add(date, amount, type_, description, account=None, payee=None, category=None, tags=None, notes=None,
             recurring=False, frequency=None, transfer_account=None):
    """Resolve and check a new transaction. Returns (fields, info) where info lists what was inferred and any
    warnings/blocks. Category comes from the payee's Default Category when not given."""
    info = dict(inferred=[], warnings=[], blocks=[])
    day = date if isinstance(date, dt.date) else dt.date.fromisoformat(str(date))
    amount = round(float(amount), 2)
    if amount <= 0:
        info["blocks"].append("amount must be positive (Type carries the sign)")
    if type_ not in TYPES:
        info["blocks"].append("type must be one of %s" % ", ".join(TYPES))
    if account:
        acc = resolve("account", account)
    else:
        active = [a for a in accounts().values() if a["active"]]
        if len(active) != 1:
            raise Blocked("several active accounts: give --account (%s)" % ", ".join(a["name"] for a in active))
        acc = active[0]
        info["inferred"].append("account: %s (the only active account)" % acc["name"])
    fields = {FX["date"]: instant(day), FX["type"]: type_, FX["amount"]: amount, FX["desc"]: description,
              FX["account"]: {"id": acc["id"]}}
    pay = resolve("payee", payee) if payee else None
    if pay:
        fields[FX["payee"]] = {"id": pay["id"]}
    cat = resolve("category", category) if category else None
    if not cat and pay and pay["default"]:
        cat = categories().get(pay["default"])
        info["inferred"].append("category: %s (payee default)" % cat["path"])
    if cat:
        fields[FX["category"]] = {"id": cat["id"]}
        if type_ in ("Income", "Expense") and cat["type"] and cat["type"] != type_:
            info["blocks"].append("category %s is an %s category but the row is %s (use --force if intended)" % (cat["path"], cat["type"], type_))
    elif type_ != "Transfer":
        info["warnings"].append("no category (and the payee has no default): the row will count as uncategorised")
    if tags:
        fields[FX["tags"]] = [{"id": i} for i in resolve_many("tag", tags)]
    if notes:
        fields[FX["notes"]] = notes
    if recurring:
        fields[FX["recurring"]] = True
        fields[FX["freq"]] = frequency or "Monthly"
    if transfer_account:
        if type_ != "Transfer":
            info["blocks"].append("--transfer-account only applies to Transfer rows")
        fields[FX["transfer_account"]] = {"id": resolve("account", transfer_account)["id"]}
    dups = find_duplicates_of(day, amount, pay["id"] if pay else None, description)
    if dups:
        info["blocks"].append("possible duplicate of %s" % ", ".join("%s (%s %s)" % (t.id, t.date, t.description) for t in dups))
    try:
        validate(TX, fields)
    except Blocked as e:
        info["blocks"].append(str(e))
    info["preview"] = dict(date=day.isoformat(), type=type_, amount=amount, description=description, account=acc["name"],
                           payee=pay["name"] if pay else None, category=cat["path"] if cat else None,
                           tags=list(tags or []), recurring=bool(recurring), notes=notes)
    return fields, info


def select_txns(ids=None, period=None, **filters):
    """Target rows for a bulk write: explicit ids, or a filter (at least one condition besides the period)."""
    if ids:
        return [to_txn(T.get_record(TX, i, TX_PROJECTION)) for i in ids]
    if not any(v not in (None, False, [], "") for v in filters.values()):
        raise Blocked("give --ids or at least one filter (refusing to target every transaction)")
    return load_txns(period, **filters)


def plan_categorize(rows, category):
    cat = resolve("category", category)
    change = {t.id: {FX["category"]: {"id": cat["id"]}} for t in rows if t.category_id != cat["id"]}
    mismatch = [t for t in rows if t.type in ("Income", "Expense") and cat["type"] and cat["type"] != t.type]
    transfers = [t for t in rows if t.type == "Transfer"]
    return cat, change, mismatch, transfers


def plan_tag(rows, tag, remove=False):
    tid = resolve("tag", tag)["id"]
    raw = {r["id"]: r["fields"].get(FX["tags"]) or [] for r in (T.get_record(TX, t.id, [FX["tags"]]) for t in rows)}
    change = {}
    for rid, cur in raw.items():
        ids = [x["id"] for x in cur]
        if remove and tid in ids:
            change[rid] = {FX["tags"]: [{"id": i} for i in ids if i != tid] or None}
        elif not remove and tid not in ids:
            change[rid] = {FX["tags"]: [{"id": i} for i in ids + [tid]]}
    return tid, change


def plan_budget(month, category, amount):
    """-> (op, record id or None, fields). One budget row per category per month: update if it exists."""
    m = dt.date.fromisoformat(month + "-01") if len(month) == 7 else dt.date.fromisoformat(month).replace(day=1)
    cat = resolve("category", category)
    if cat["type"] == "Income":
        raise Blocked("%s is an income category; budgets are for spending" % cat["path"])
    if float(amount) < 0:
        raise Blocked("planned amount must be >= 0")
    existing = [b for b in budgets().values() if b["month"] == m and b["category"] == cat["id"]]
    if len(existing) > 1:
        raise Blocked("%d budget rows already exist for %s %s: fix them first (%s)" % (len(existing), cat["path"], m.strftime("%Y-%m"),
                                                                                      ", ".join(b["id"] for b in existing)))
    if existing:
        return "update", existing[0]["id"], {FB["planned"]: round(float(amount), 2)}, cat, m, existing[0]["planned"]
    return "create", None, {FB["month"]: m.isoformat(), FB["planned"]: round(float(amount), 2), FB["category"]: {"id": cat["id"]}}, cat, m, None
