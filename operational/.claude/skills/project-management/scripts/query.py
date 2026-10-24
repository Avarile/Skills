#!/usr/bin/env python3
"""Server-side filtered reads from the cybernetics-data Teable API (read-only).

The MCP `query_records` tool silently ignores `filter`, so filtered reads go here.
Token: CYBERNETICS_DATA_API_TOKEN from the environment or a .env in this or a parent directory (never printed).

Examples:
  query.py tblOMgDiajqa1moRRjE --project fldGqUoXO7oyq6ufX2Y fldMTuydiWUFAgtqAPX \
      --filter 'fldMTuydiWUFAgtqAPX isAnyOf urgent,important' --order fld2s647Pe9XgapERLS:desc
  query.py tblOMgDiajqa1moRRjE --filter 'fld6X3nrMTQlYiV5XSa isEmpty' --count
  query.py tbliD8gcOTRk9RZ9SmR --filter-json '{"conjunction":"or","filterSet":[...]}'

--filter 'FIELD_ID OPERATOR [VALUE]' can repeat (AND). isAnyOf/isNoneOf take comma-separated values;
VALUE date:YYYY-MM-DD becomes an exactDate (Australia/Melbourne).
Output: JSON {"count": n, "records": [{"id":..., "fields": {...}}]} (count only with --count).
Writes: see write.py (bulk) and the MCP tools (single create/update).
"""
import argparse, json
import teable as T


def main():
    a = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    a.add_argument("table")
    a.add_argument("--project", nargs="*", default=[], help="field IDs to return")
    a.add_argument("--filter", action="append", default=[])
    a.add_argument("--filter-json", help="full Teable filter object (overrides --filter)")
    a.add_argument("--order", action="append", default=[], help="FIELD_ID:asc|desc")
    a.add_argument("--search")
    a.add_argument("--take", type=int, default=1000)
    a.add_argument("--count", action="store_true")
    args = a.parse_args()

    flt = json.loads(args.filter_json) if args.filter_json else T.and_filter(args.filter)
    params = [("fieldKeyType", "id"), ("take", min(args.take, 1000))]
    params += [("projection[]", f) for f in args.project]
    if flt:
        params.append(("filter", json.dumps(flt)))
    if args.order:
        params.append(("orderBy", json.dumps([{"fieldId": o.split(":")[0], "order": (o.split(":") + ["asc"])[1]} for o in args.order])))
    if args.search:
        params.append(("search", args.search))

    records, skip = [], 0
    while True:
        page = T.call("GET", "/api/table/%s/record" % args.table, params + [("skip", skip)])["records"]
        records += page
        if len(page) < min(args.take, 1000) or len(records) >= args.take:
            break
        skip += len(page)

    out = {"count": len(records)}
    if not args.count:
        out["records"] = [{"id": r["id"], "fields": r.get("fields", {})} for r in records]
    print(json.dumps(out, ensure_ascii=False))


if __name__ == "__main__":
    main()
