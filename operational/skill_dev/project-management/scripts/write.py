#!/usr/bin/env python3
"""Safe write helpers for cybernetics-data (Teable REST). DRY-RUN BY DEFAULT: nothing is written without --yes.

Use MCP for creating records and for single-record updates. Use this for what MCP cannot do safely:

  bulk-update   change the same fields on many records (MCP update_record is one record per call)
  ctx-append    append to (or create) a '## Section' inside a markdown `context` field without
                re-emitting the whole field, and without overwriting a concurrent human edit

Examples:
  write.py bulk-update tblOMgDiajqa1moRRjE --filter 'fldJMclfBagyBukSxoy is true' \
      --set 'fldJMclfBagyBukSxoy=false' --set 'fldkdTbYu0f3LaYK7wl=2026-10-02' --yes
  write.py bulk-update tblOMgDiajqa1moRRjE --ids recA recB --set 'fldMTuydiWUFAgtqAPX=important'
  write.py ctx-append tbliD8gcOTRk9RZ9SmR recXXXX --field fldnzxFdoNG8bN1y4kC \
      --section '## Status Log' --text-file entry.md --yes

--set 'FIELD_ID=VALUE': VALUE is JSON when it parses (true, 3, {"id":"recX"}, ["a"]), else a plain string.
Link fields: {"id":"recX"} (many-to-one) or [{"id":"recX"}] (many-to-many). Dates: YYYY-MM-DD strings.
Every applied write is read back and verified; exit code 1 if verification fails.
"""
import argparse, datetime as dt, difflib, json, sys
from zoneinfo import ZoneInfo
import teable as T


def local_date(iso):
    """API returns UTC timestamps; dates are meant in Australia/Melbourne."""
    return dt.datetime.fromisoformat(iso.replace("Z", "+00:00")).astimezone(ZoneInfo(T.TZ)).date().isoformat()


def validate_sets(table, sets):
    """Reject unknown fields and invalid select options. The API does NOT: a bad option silently clears the cell."""
    meta = {f["id"]: f for f in T.call("GET", "/api/table/%s/field" % table)}
    for k, v in sets.items():
        f = meta.get(k)
        if f is None:
            sys.exit("unknown field %s on table %s" % (k, table))
        if f.get("isComputed"):
            sys.exit("field %s (%s) is computed and read-only" % (k, f["name"]))
        if f["type"] in ("singleSelect", "multipleSelect") and v is not None:
            names = [c["name"] for c in f["options"]["choices"]]
            bad = [x for x in (v if isinstance(v, list) else [v]) if x not in names]
            if bad:
                sys.exit("invalid option %r for %s; valid: %s (a wrong spelling would silently CLEAR the field)" % (bad, f["name"], names))
    return meta


def shown(v, n=70):
    s = json.dumps(v, ensure_ascii=False) if not isinstance(v, str) else v
    return s if len(s) <= n else s[: n - 1] + "…"


def cmd_bulk_update(a):
    sets = {}
    for s in a.set:
        k, _, v = s.partition("=")
        if not k.startswith("fld") or not _:
            sys.exit("bad --set %r (need FIELD_ID=VALUE)" % s)
        sets[k] = T.parse_value(v)
    if not sets:
        sys.exit("nothing to set")
    meta = validate_sets(a.table, sets)
    proj = list(sets)
    if a.ids:
        recs = [T.get_record(a.table, i, proj) for i in a.ids]
    else:
        if not a.filter:
            sys.exit("give --ids or at least one --filter (refusing to update a whole table)")
        recs = T.get_records(a.table, T.and_filter(a.filter), proj)
    n = len(recs)
    print("targets: %d record(s); fields: %s" % (n, ", ".join(sets)))
    if n == 0:
        return
    if n > a.max:
        sys.exit("refusing: %d records exceeds --max %d" % (n, a.max))
    for r in recs[:15]:
        f = r.get("fields", {})
        print(" ", r["id"], " | ".join("%s: %s -> %s" % (k, shown(f.get(k)), shown(v)) for k, v in sets.items()))
    if n > 15:
        print("  … and %d more" % (n - 15))
    if not a.yes:
        print("DRY RUN: nothing written. Re-run with --yes to apply.")
        return
    for i in range(0, n, 100):
        T.call("PATCH", "/api/table/%s/record" % a.table, body={
            "fieldKeyType": "id", "typecast": True,
            "records": [{"id": r["id"], "fields": sets} for r in recs[i:i + 100]]})
    bad = 0
    for r in recs:
        got = T.get_record(a.table, r["id"], proj).get("fields", {})
        for k, v in sets.items():
            if isinstance(v, (dict, list)):
                ok = _ids(got.get(k)) == _ids(v)
            elif meta[k]["type"] == "checkbox":  # unchecked reads back as null, not false
                ok = bool(got.get(k)) == bool(v)
            elif meta[k]["type"] == "date" and isinstance(v, str):
                ok = bool(got.get(k)) and local_date(got[k]) == v[:10]
            else:
                ok = got.get(k) == v
            if not ok:
                bad += 1
                print("VERIFY MISMATCH", r["id"], k, shown(got.get(k)), "!=", shown(v))
    print("applied to %d record(s); verification %s" % (n, "FAILED (%d)" % bad if bad else "ok"))
    sys.exit(1 if bad else 0)


def _ids(v):
    if isinstance(v, dict):
        return [v.get("id")]
    if isinstance(v, list):
        return sorted(x.get("id") if isinstance(x, dict) else x for x in v)
    return v


def append_section(text, heading, body):
    """Append body to the end of `heading`'s section (a '## ' block); create the section at the end if absent."""
    body = body.strip("\n")
    lines = text.split("\n")
    start = next((i for i, l in enumerate(lines) if l.strip() == heading.strip()), None)
    if start is None:
        return text.rstrip("\n") + ("\n\n" if text.strip() else "") + heading + "\n" + body + "\n"
    end = next((i for i in range(start + 1, len(lines)) if lines[i].startswith("## ")), len(lines))
    section = "\n".join(lines[start:end]).rstrip("\n")
    tight = section.split("\n")[-1].startswith("- ") and body.startswith("- ")  # keep bullet lists contiguous
    sep = "\n" if tight else "\n\n"
    return "\n".join(lines[:start] + [section + sep + body + ("\n" if end < len(lines) else "")] + lines[end:]).rstrip("\n") + "\n"


def cmd_ctx_append(a):
    body = open(a.text_file).read() if a.text_file else a.text
    if not body or not body.strip():
        sys.exit("empty text")
    before = T.get_record(a.table, a.record, [a.field]).get("fields", {}).get(a.field) or ""
    after = append_section(before, a.section, body)
    print("record %s · field %s · section %r · +%d chars" % (a.record, a.field, a.section, len(after) - len(before)))
    for l in difflib.unified_diff(before.split("\n"), after.split("\n"), "before", "after", lineterm="", n=1):
        print(l)
    if not a.yes:
        print("DRY RUN: nothing written. Re-run with --yes to apply.")
        return
    again = T.get_record(a.table, a.record, [a.field]).get("fields", {}).get(a.field) or ""
    if again != before:
        sys.exit("ABORT: the field changed while preparing the edit (someone edited it). Re-run to merge against the new text.")
    T.call("PATCH", "/api/table/%s/record/%s" % (a.table, a.record), body={
        "fieldKeyType": "id", "record": {"fields": {a.field: after}}})
    got = T.get_record(a.table, a.record, [a.field]).get("fields", {}).get(a.field) or ""
    if got.strip() != after.strip():
        print("VERIFY FAILED: stored text differs from expected; previous text follows for manual restore:\n" + before)
        sys.exit(1)
    print("applied; verified (all other sections unchanged)")


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("bulk-update")
    b.add_argument("table")
    b.add_argument("--ids", nargs="*")
    b.add_argument("--filter", action="append", default=[], help="'FIELD_ID OPERATOR [VALUE]' (AND-ed)")
    b.add_argument("--set", action="append", default=[], help="FIELD_ID=VALUE")
    b.add_argument("--max", type=int, default=200)
    b.add_argument("--yes", action="store_true")
    b.set_defaults(fn=cmd_bulk_update)
    c = sub.add_parser("ctx-append")
    c.add_argument("table")
    c.add_argument("record")
    c.add_argument("--field", required=True, help="the markdown context field ID")
    c.add_argument("--section", required=True, help="e.g. '## Status Log'")
    g = c.add_mutually_exclusive_group(required=True)
    g.add_argument("--text")
    g.add_argument("--text-file")
    c.add_argument("--yes", action="store_true")
    c.set_defaults(fn=cmd_ctx_append)
    a = p.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()
