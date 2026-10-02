#!/usr/bin/env python3
"""List and create saved views, including filtered ones (MCP create_view cannot set a filter).
`list` is read-only. `create` is DRY-RUN BY DEFAULT; pass --yes to write.

  views.py list tblOMgDiajqa1moRRjE
  views.py create tblOMgDiajqa1moRRjE --name 'Overdue' --type grid \
      --filter 'fldG7fZN9XhOa0lMy33 isNoneOf finished_reviewing,finished_validating,cancelled' --yes

A view's filter is then usable server-side through the MCP too: query_records(viewId=...).
"""
import argparse, json, sys
import teable as T


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    l = sub.add_parser("list")
    l.add_argument("table")
    c = sub.add_parser("create")
    c.add_argument("table")
    c.add_argument("--name", required=True)
    c.add_argument("--type", default="grid")
    c.add_argument("--filter", action="append", default=[])
    c.add_argument("--yes", action="store_true")
    a = p.parse_args()

    if a.cmd == "list":
        for v in T.call("GET", "/api/table/%s/view" % a.table):
            print(v["id"], v.get("type"), v.get("name"), "filter=" + json.dumps(v.get("filter")) if v.get("filter") else "")
        return

    body = {"name": a.name, "type": a.type}
    flt = T.and_filter(a.filter)
    if flt:
        body["filter"] = flt
    print("create view:", json.dumps(body, ensure_ascii=False))
    if not a.yes:
        print("DRY RUN: nothing written. Re-run with --yes to apply.")
        return
    v = T.call("POST", "/api/table/%s/view" % a.table, body=body)
    got = next((x for x in T.call("GET", "/api/table/%s/view" % a.table) if x["id"] == v["id"]), None)
    ok = got is not None and (not flt or got.get("filter"))
    print("created", v["id"], "· filter stored" if flt and ok else "")
    if not ok:
        print("VERIFY FAILED: view missing or filter not stored; delete it in the UI and report this")
        sys.exit(1)


if __name__ == "__main__":
    main()
