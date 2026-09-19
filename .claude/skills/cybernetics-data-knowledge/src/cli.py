#!/usr/bin/env python3
"""CLI for managing the Cybernetics knowledge base.

Every subcommand prints one JSON document to stdout. Errors go to stderr with
exit code 1 (2 for a refused destructive action). Run --help for the surface.
"""
from __future__ import annotations

import argparse
import json
import os
import sys

import client
import knowledge

REFUSED = 2


def _out(payload):
    json.dump(payload, sys.stdout, indent=2, ensure_ascii=False, default=str)
    sys.stdout.write("\n")


def _brief(entry: dict) -> dict:
    """Drop `context` so a list stays readable; `get` shows the full record."""
    return {k: v for k, v in entry.items() if k != "context"}


def _csv(value: str | None) -> list:
    return [p.strip() for p in (value or "").split(",") if p.strip()]


def _active_flag(args):
    if getattr(args, "active", False):
        return True
    if getattr(args, "inactive", False):
        return False
    return None


# --- commands --------------------------------------------------------------

def cmd_list(args):
    conditions = []
    if args.type:
        conditions.append({"fieldId": "knowledge_type", "operator": "is",
                           "value": knowledge.resolve(args.type, "knowledge_type")["record_id"]})
    active = _active_flag(args)
    if active is not None:
        conditions.append({"fieldId": "is_active", "operator": "is", "value": active})
    entries = knowledge.fetch_all(
        "knowledges", filter=client.and_filter(*conditions),
        order_by=[{"fieldId": args.sort, "order": args.order}])
    if args.limit:
        entries = entries[: args.limit]
    _out({"count": len(entries),
          "entries": entries if args.full else [_brief(e) for e in entries]})


def cmd_get(args):
    _out(knowledge.resolve(args.ref))


def cmd_search(args):
    entries = knowledge.search(args.query, field=args.field)
    if args.limit:
        entries = entries[: args.limit]
    _out({"query": args.query,
          "fields": [args.field] if args.field else client.SEARCHABLE["knowledges"],
          "count": len(entries),
          "entries": entries if args.full else [_brief(e) for e in entries]})


def cmd_create(args):
    context = args.context
    if context == "-":
        context = sys.stdin.read()
    entry = knowledge.create(
        title=args.title, context=context, is_active=_active_flag(args),
        type_ref=args.type, parent_ref=args.parent,
        related_refs=_csv(args.related) or None)
    _out({"created": entry})


def cmd_update(args):
    context = args.context
    if context == "-":
        context = sys.stdin.read()
    entry = knowledge.update(
        args.ref, title=args.title, context=context,
        is_active=_active_flag(args), type_ref=args.type, parent_ref=args.parent,
        related_refs=_csv(args.related) if args.related is not None else None)
    _out({"updated": entry})


def cmd_delete(args):
    targets = [knowledge.resolve(r) for r in args.refs]
    if not args.force:
        print("Refusing to delete without --force. Would delete:", file=sys.stderr)
        for t in targets:
            print(f"  {t['record_id']}  #{t['num']}  {t['title']!r}"
                  f"  children={len(t['children'])}", file=sys.stderr)
        children = [t for t in targets if t["children"]]
        if children:
            print("WARNING: deleting a parent orphans its children.", file=sys.stderr)
        sys.exit(REFUSED)
    _out({"deleted": knowledge.delete([t["record_id"] for t in targets])})


def cmd_parent(args):
    _out({"updated": knowledge.set_parent(args.ref, None if args.clear else args.parent)})


def cmd_relate(args):
    if args.remove:
        _out({"updated": knowledge.remove_related(args.ref, _csv(args.remove))})
    else:
        _out({"updated": knowledge.add_related(args.ref, _csv(args.add),
                                               mutual=args.mutual)})


def cmd_tree(args):
    def prune(nodes):
        return [{"record_id": n["record_id"], "num": n["num"], "title": n["title"],
                 "type": n["type"]["title"], "child_nodes": prune(n["child_nodes"])}
                for n in nodes]
    forest = knowledge.tree(args.type)
    _out({"roots": len(forest), "tree": forest if args.full else prune(forest)})


def cmd_children(args):
    target = knowledge.resolve(args.ref)
    _out({"parent": {"record_id": target["record_id"], "title": target["title"]},
          "children": target["children"]})


def cmd_orphans(args):
    entries = knowledge.orphans()
    _out({"count": len(entries), "entries": [_brief(e) for e in entries]})


def cmd_stats(args):
    _out(knowledge.stats())


def cmd_types(args):
    if args.action == "list":
        types = knowledge.fetch_all("knowledge_type")
        _out({"count": len(types),
              "types": types if args.full else [_brief(t) for t in types]})
    elif args.action == "get":
        _out(knowledge.resolve(args.ref, "knowledge_type"))
    elif args.action == "create":
        fields = {"title": args.title}
        if args.context:
            fields["context"] = args.context
        if args.parent:
            fields["parent_type"] = {
                "id": knowledge.resolve(args.parent, "knowledge_type")["record_id"]}
        created = client.create_records("knowledge_type", [fields])
        _out({"created": knowledge.normalize_type(created[0])})
    elif args.action == "delete":
        if not args.force:
            target = knowledge.resolve(args.ref, "knowledge_type")
            print(f"Refusing without --force. Would delete {target['record_id']} "
                  f"{target['title']!r} ({target['knowledge_count']} linked entries).",
                  file=sys.stderr)
            sys.exit(REFUSED)
        _out({"deleted": knowledge.delete([args.ref], "knowledge_type")})


def cmd_doctor(args):
    checks = {}
    try:
        config = client.get_config()
        checks["config"] = {"base_url": config["base_url"],
                            "token": f"present ({len(config['token'])} chars)"}
    except client.KnowledgeError as exc:
        checks["config"] = f"FAIL: {exc}"
        _out(checks)
        sys.exit(1)
    for table in ("knowledges", "knowledge_type"):
        try:
            page = client.list_records(table, take=1)
            checks[table] = {"reachable": True,
                             "sample": bool(page.get("records"))}
        except client.KnowledgeError as exc:
            checks[table] = {"reachable": False, "error": str(exc)}
    _out(checks)


# --- parser ----------------------------------------------------------------

def build_parser():
    p = argparse.ArgumentParser(prog="kb", description=__doc__.splitlines()[0])
    sub = p.add_subparsers(dest="command", required=True)

    def add_full(sp):
        sp.add_argument("--full", action="store_true",
                       help="include the context body (omitted by default)")

    sp = sub.add_parser("list", help="list knowledge entries")
    sp.add_argument("--type", help="filter by knowledge_type reference")
    sp.add_argument("--active", action="store_true")
    sp.add_argument("--inactive", action="store_true")
    sp.add_argument("--sort", default="id", help="field name to sort by (default id)")
    sp.add_argument("--order", default="asc", choices=["asc", "desc"])
    sp.add_argument("--limit", type=int)
    add_full(sp)
    sp.set_defaults(func=cmd_list)

    sp = sub.add_parser("get", help="show one entry in full")
    sp.add_argument("ref", help="record id, #number, or title")
    sp.set_defaults(func=cmd_get)

    sp = sub.add_parser("search", help="substring search over title+context")
    sp.add_argument("query")
    sp.add_argument("--field", choices=client.SEARCHABLE["knowledges"],
                    help="restrict to one field (default: all of them)")
    sp.add_argument("--limit", type=int)
    add_full(sp)
    sp.set_defaults(func=cmd_search)

    sp = sub.add_parser("create", help="create an entry")
    sp.add_argument("--title", required=True)
    sp.add_argument("--context", help="body text, or '-' to read stdin")
    sp.add_argument("--type", help="knowledge_type reference")
    sp.add_argument("--parent", help="parent entry reference")
    sp.add_argument("--related", help="comma-separated entry references")
    sp.add_argument("--active", action="store_true")
    sp.add_argument("--inactive", action="store_true")
    sp.set_defaults(func=cmd_create)

    sp = sub.add_parser("update", help="update an entry (partial)")
    sp.add_argument("ref")
    sp.add_argument("--title")
    sp.add_argument("--context", help="body text, or '-' to read stdin")
    sp.add_argument("--type")
    sp.add_argument("--parent", help="reference, or '' to clear")
    sp.add_argument("--related", help="comma-separated; REPLACES the list")
    sp.add_argument("--active", action="store_true")
    sp.add_argument("--inactive", action="store_true")
    sp.set_defaults(func=cmd_update)

    sp = sub.add_parser("delete", help="delete entries (needs --force)")
    sp.add_argument("refs", nargs="+")
    sp.add_argument("--force", action="store_true")
    sp.set_defaults(func=cmd_delete)

    sp = sub.add_parser("parent", help="reparent an entry")
    sp.add_argument("ref")
    sp.add_argument("--parent", help="new parent reference")
    sp.add_argument("--clear", action="store_true", help="detach from its parent")
    sp.set_defaults(func=cmd_parent)

    sp = sub.add_parser("relate", help="add or remove related_knowledge links")
    sp.add_argument("ref")
    sp.add_argument("--add", help="comma-separated references to append")
    sp.add_argument("--remove", help="comma-separated references to drop")
    sp.add_argument("--mutual", action="store_true",
                    help="also link back (the link is one-directional by default)")
    sp.set_defaults(func=cmd_relate)

    sp = sub.add_parser("tree", help="hierarchy as nested JSON")
    sp.add_argument("--type")
    add_full(sp)
    sp.set_defaults(func=cmd_tree)

    sp = sub.add_parser("children", help="direct children of an entry")
    sp.add_argument("ref")
    sp.set_defaults(func=cmd_children)

    sp = sub.add_parser("orphans", help="entries with no parent and no children")
    sp.set_defaults(func=cmd_orphans)

    sp = sub.add_parser("stats", help="counts by type, activity, orphans")
    sp.set_defaults(func=cmd_stats)

    sp = sub.add_parser("types", help="manage knowledge_type records")
    sp.add_argument("action", choices=["list", "get", "create", "delete"])
    sp.add_argument("ref", nargs="?")
    sp.add_argument("--title")
    sp.add_argument("--context")
    sp.add_argument("--parent")
    sp.add_argument("--force", action="store_true")
    add_full(sp)
    sp.set_defaults(func=cmd_types)

    sp = sub.add_parser("doctor", help="check config and table reachability")
    sp.set_defaults(func=cmd_doctor)
    return p


def main(argv=None):
    args = build_parser().parse_args(argv)
    try:
        args.func(args)
        # Flush inside the try: output is buffered, so a closed pipe would
        # otherwise only surface during the interpreter's exit-time flush --
        # after this handler is out of scope, which prints a traceback the
        # caller cannot suppress.
        sys.stdout.flush()
    except client.KnowledgeError as exc:
        print(f"error: {exc}", file=sys.stderr)
        sys.exit(1)
    except BrokenPipeError:
        # A downstream reader (head, or a consumer that exits early) closed the
        # pipe. Redirect stdout to devnull so the final flush stays silent.
        os.dup2(os.open(os.devnull, os.O_WRONLY), sys.stdout.fileno())
        sys.exit(1)


if __name__ == "__main__":
    main()
