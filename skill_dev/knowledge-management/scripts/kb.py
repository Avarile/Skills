#!/usr/bin/env python3
"""Knowledge base CLI for cybernetics-data (`knowledges` + `knowledge_type`) over the Teable REST API.

Reads return everything, credential types included, unredacted (owner decision CR-1, 2026-10-05).
Writes are DRY-RUN BY DEFAULT: nothing is written without --yes. Token: CYBERNETICS_DATA_API_TOKEN (env or .env).

Query
  kb.py find k3s backup               every term must match title or body (aliases on: k8s=k3s=kubernetes ...)
  kb.py find caddy nginx --any        any term
  kb.py find docker --type deployment  limit to a type and its child types
  kb.py get recXXXX | "K3S - Cheatsheet"   full entry; --toc headings only; --section "Backup"; --max-chars 4000
  kb.py types                         type tree with entry counts
  kb.py type "deployment - k8s"       one type: description, parent/children, credentials value, entries
  kb.py tree recXXXX                  parent chain, children and related entries

Write
  kb.py capture --title "Caddy - Reverse Proxy Basics" --type "deployment - caddy" --body-file note.md
        [--parent REC] [--related REC ...] [--refer project:REC|task:REC|goal:REC ...] [--new-type [--parent-type T]]
        [--allow-duplicate] [--yes]
  kb.py append REC --text-file more.md [--section "## Updates"] [--no-date] [--yes]

Add --json to any command for machine output. Exit codes: 0 ok, 2 blocked by a check, 3 not found or ambiguous.
"""
import argparse, difflib, json, re, sys, time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import teable as T
import safety

K, KT = "tblVTWb1kxXSFPBq4Fq", "tblWcq6Kof1AFHvbC5e"
F = dict(title="fldROFj15OlD8COVxX0", context="fld5tr2rH8oJXLrjUo9", type="fldAEK8ULw9urxE0qiF",
         parent="fldzUUVy3q1vSWURhZD", children="fldKzPJEFtElf4liepG", related="fldz7U2RsCfm0j1RZOs",
         active="fldZKMuaBBPd6tIzSG3", deleted="fldNS9SNNWG07NnBZhE", created="fldRs8i67CkuzpDyubP",
         updated="fldCpv0ts2jxxgQPg7n", num="fldNxPGGDuchpHCvz0U")
FT = dict(title="fldvL1LqKmEAfNKVBCO", context="fldsnpIqBqoYZJxZwI5", parent="fld924GlXY0tL5um2wk",
          children="fldehPY6CjjdpeK3H6j", entries="fldtBWHVokGwcAywjtc", credentials="fld1s2dEom17aZIu4nx",
          active="fldte086UL30roxKKAl", deleted="fldMcIaV4FSsuV9OG9J")
# Work tables that point at knowledge through a one-way many-to-many `refer_knowledge` link.
WORK = {"goal": ("tblbGSzWdR7KEtPVClg", "fldRMySX5jvdIUWIkGB", "fld8ipvRLGq7YTgPQkI"),
        "project": ("tbliD8gcOTRk9RZ9SmR", "fldCw3cnpw8EWs09C1v", "fldiDksJhyT8mDAhCBP"),
        "task": ("tblOMgDiajqa1moRRjE", "fldJzsKyzBaDFt7bHIu", "fldGqUoXO7oyq6ufX2Y")}

# Search aliases: a term in one group also matches the others. Keep groups specific (no short ambiguous tokens).
ALIASES = [
    ["k8s", "k3s", "kubernetes", "microk8s", "kubectl"],
    ["postgres", "postgresql"],
    ["mariadb", "mysql"],
    ["nvim", "neovim", "lazyvim"],
    ["docker-compose", "docker compose"],
    ["wow", "world of warcraft", "azerothcore"],
    ["credential", "credentials", "password", "api key", "apikey"],
    ["ssl", "tls", "certificate"],
    ["firewall", "ufw", "iptables", "nftables"],
    ["raid", "mdadm"],
]
STOP = set("a an and the of for to in on with how what is are my new setup set up guide using use via from".split())
REC = re.compile(r"rec[A-Za-z0-9]{16}")

CALLS = [0]
_call = T.call


def _counted(*a, **k):
    CALLS[0] += 1
    return _call(*a, **k)


T.call = _counted  # teable.get_records resolves `call` from its module globals, so this counts every request


def emit(args, data, human):
    if getattr(args, "json", False):
        print(json.dumps(data, ensure_ascii=False, indent=1))
    else:
        print(human() if callable(human) else human)


def ftitle(v):
    return (v or {}).get("title") if isinstance(v, dict) else None


def ids(v):
    if isinstance(v, dict):
        return [v["id"]]
    return [x["id"] for x in v or []]


def date(iso):
    return T.local_date(iso).isoformat() if iso else None


def kchars(n):
    return "%.1fk chars" % (n / 1000) if n >= 1000 else "%d chars" % n


# ---------- types ----------

def load_types():
    recs = T.get_records(KT, projection=[FT["title"], FT["parent"], FT["entries"], FT["context"], FT["active"]])
    out = {}
    for r in recs:
        f = r["fields"]
        out[r["id"]] = dict(id=r["id"], title=f.get(FT["title"]) or "", parent=(f.get(FT["parent"]) or {}).get("id"),
                            entries=len(f.get(FT["entries"]) or []), desc=(f.get(FT["context"]) or "").strip(),
                            active=f.get(FT["active"]) is True)
    return out


def descendants(types, tid):
    out, todo = [], [tid]
    while todo:
        cur = todo.pop()
        out.append(cur)
        todo += [t["id"] for t in types.values() if t["parent"] == cur]
    return out


def resolve_type(types, ref):
    """-> (type dict | None, candidates). Exact (case-insensitive) title or id, else a unique partial match."""
    if ref in types:
        return types[ref], []
    low = ref.strip().lower()
    exact = [t for t in types.values() if t["title"].strip().lower() == low]
    if len(exact) == 1:
        return exact[0], []
    part = [t for t in types.values() if low in t["title"].lower()]
    if len(part) == 1:
        return part[0], []
    pool = part or sorted(types.values(), key=lambda t: -difflib.SequenceMatcher(None, low, t["title"].lower()).ratio())[:5]
    return None, pool


# ---------- entries ----------

def alias_group(term):
    t = term.lower()
    for g in ALIASES:
        if t in g:
            return g
    return [t]


def term_groups(terms, exact):
    return [[t.lower()] if exact else alias_group(t) for t in terms]


def contains_any(group):
    return {"conjunction": "or", "filterSet": [{"fieldId": fid, "operator": "contains", "value": a}
                                               for a in group for fid in (F["title"], F["context"])]}


def snippet(ctx, group_list, width=200):
    if not ctx:
        return ""
    low = ctx.lower()
    hits = [low.find(a) for g in group_list for a in g if low.find(a) >= 0]
    pos = min(hits) if hits else 0
    start = max(0, pos - 70)
    s = re.sub(r"\s+", " ", ctx[start:start + width]).strip()
    return ("…" if start else "") + s + ("…" if start + width < len(ctx) else "")


def score(f, groups):
    title, ctx = (f.get(F["title"]) or "").lower(), (f.get(F["context"]) or "").lower()
    s, in_title = 0, 0
    for g in groups:
        th = any(a in title for a in g)
        in_title += th
        s += (10 if th else 0) + min(5, sum(ctx.count(a) for a in g))
    lead = any(title.startswith(a) for a in groups[0]) if groups else False  # the entry is *about* the first term
    return s + (10 if groups and in_title == len(groups) else 0) + (5 if lead else 0)


def resolve_entry(ref, projection):
    """Record id, or title: exact (case-insensitive), else a unique partial match. Exits 3 otherwise."""
    if REC.fullmatch(ref.strip()):
        return T.get_record(K, ref.strip(), projection)
    recs = T.get_records(K, {"conjunction": "and", "filterSet": [{"fieldId": F["title"], "operator": "contains", "value": ref}]},
                         projection + [F["title"]] if F["title"] not in projection else projection)
    exact = [r for r in recs if (r["fields"].get(F["title"]) or "").strip().lower() == ref.strip().lower()]
    pick = exact if len(exact) == 1 else recs
    if len(pick) == 1:
        return pick[0]
    if not pick:
        print("no knowledge entry titled like %r; try: kb.py find %s" % (ref, ref))
    else:
        print("ambiguous title %r, %d matches:" % (ref, len(pick)))
        for r in pick[:15]:
            print("  %s  %s" % (r["id"], r["fields"].get(F["title"])))
    sys.exit(3)


def headings(ctx):
    """[(line_no, '##', title)] for Markdown headings outside fenced code blocks."""
    out, fence = [], False
    for i, l in enumerate((ctx or "").split("\n")):
        if re.match(r"^\s*(```|~~~)", l):
            fence = not fence
            continue
        m = None if fence else re.match(r"^(#{1,6})\s+(.+)$", l)
        if m:
            out.append((i + 1, m.group(1), m.group(2).strip()))
    return out


def section(ctx, name):
    """Text of the first heading whose title equals (else starts with, else contains) name, up to the next heading
    of the same or higher level."""
    lines, want = (ctx or "").split("\n"), name.strip().lstrip("#").strip().lower()
    hs = headings(ctx)
    for test in (lambda h: h == want, lambda h: h.startswith(want), lambda h: want in h):
        for ln, hashes, title in hs:
            if test(title.lower()):
                end = next((l2 - 1 for l2, h2, _ in hs if l2 > ln and len(h2) <= len(hashes)), len(lines))
                return "\n".join(lines[ln - 1:end]).rstrip()
    return None


# ---------- commands: query ----------

def cmd_find(a):
    t0 = time.time()
    groups = term_groups(a.terms, a.exact)
    sets = [contains_any(g) for g in groups]
    flt = {"conjunction": "or" if a.any else "and", "filterSet": sets}
    if a.type:
        types = load_types()
        ty, cand = resolve_type(types, a.type)
        # A domain prefix ("deployment") matches every type whose title contains it, plus their child types.
        picked = [ty] if ty else [t for t in cand if a.type.strip().lower() in t["title"].lower()]
        if not picked:
            sys.exit("unknown type %r; candidates: %s" % (a.type, ", ".join(t["title"] for t in cand)))
        tids = sorted({d for t in picked for d in descendants(types, t["id"])})
        tf = {"fieldId": F["type"], "operator": "isAnyOf", "value": tids}
        flt = {"conjunction": "and", "filterSet": [flt, tf]}
    if not a.all:
        flt = {"conjunction": "and", "filterSet": [flt, {"fieldId": F["active"], "operator": "is", "value": True}]}
    recs = T.get_records(K, flt, [F["title"], F["type"], F["updated"], F["context"], F["active"]])
    recs.sort(key=lambda r: (score(r["fields"], groups), r["fields"].get(F["updated"]) or ""), reverse=True)
    rows = [dict(id=r["id"], title=r["fields"].get(F["title"]), type=ftitle(r["fields"].get(F["type"])),
                 updated=date(r["fields"].get(F["updated"])), chars=len(r["fields"].get(F["context"]) or ""),
                 score=score(r["fields"], groups), active=r["fields"].get(F["active"]) is True,
                 snippet=snippet(r["fields"].get(F["context"]), groups)) for r in recs]
    meta = dict(query=a.terms, mode="any" if a.any else "all", aliases=[g for g in groups if len(g) > 1],
                total=len(rows), shown=min(len(rows), a.limit), http_calls=CALLS[0], seconds=round(time.time() - t0, 2))

    def human():
        out = ['%d match(es) for %s (%s terms%s) · %d HTTP call(s), %.2fs' % (
            meta["total"], " ".join(a.terms), meta["mode"], ", aliases on" if meta["aliases"] else "", CALLS[0], meta["seconds"])]
        for i, r in enumerate(rows[:a.limit], 1):
            out.append("%d. %s  [%s]  %s  %s  %s%s" % (i, r["title"], r["type"] or "untyped", r["id"], r["updated"],
                                                     kchars(r["chars"]), "" if r["active"] else "  (archived)"))
            if r["snippet"] and not a.titles:
                out.append("   " + r["snippet"])
        if meta["total"] > a.limit:
            out.append("… %d more (raise --limit or add terms)" % (meta["total"] - a.limit))
        if not rows:
            out.append("nothing found; try other words, --any, or kb.py types to browse")
        return "\n".join(out)
    emit(a, dict(meta=meta, results=rows[:a.limit]), human)


def cmd_get(a):
    proj = [F["title"], F["context"], F["type"], F["parent"], F["children"], F["related"], F["active"], F["updated"], F["created"]]
    r = resolve_entry(a.ref, proj)
    f = r["fields"]
    ctx = f.get(F["context"]) or ""
    head = dict(id=r["id"], title=f.get(F["title"]), type=ftitle(f.get(F["type"])), type_id=ids(f.get(F["type"]))[:1],
                parent=f.get(F["parent"]), children=f.get(F["children"]) or [], related=f.get(F["related"]) or [],
                active=f.get(F["active"]) is True, created=date(f.get(F["created"])), updated=date(f.get(F["updated"])),
                chars=len(ctx))
    body, note = ctx, None
    if a.toc:
        body = "\n".join("%s%s (line %d)" % ("  " * (len(h) - 1), t, ln) for ln, h, t in headings(ctx)) or "(no headings)"
    elif a.section:
        body = section(ctx, a.section)
        if body is None:
            sys.stdout.write("no section %r; headings: %s\n" % (a.section, "; ".join(t for _, _, t in headings(ctx)) or "none"))
            sys.exit(3)
    if a.max_chars and len(body) > a.max_chars:
        note = "truncated at %d of %d chars; use --toc and --section to read the rest" % (a.max_chars, len(body))
        body = body[:a.max_chars]

    def human():
        lines = ["# %s" % head["title"], "id %s · type %s · updated %s · %s%s" % (
            head["id"], head["type"] or "untyped", head["updated"], kchars(head["chars"]), "" if head["active"] else " · ARCHIVED")]
        if head["parent"]:
            lines.append("parent: %s (%s)" % (head["parent"].get("title"), head["parent"]["id"]))
        if head["children"]:
            lines.append("children: " + "; ".join("%s (%s)" % (c.get("title"), c["id"]) for c in head["children"]))
        if head["related"]:
            lines.append("related: " + "; ".join("%s (%s)" % (c.get("title"), c["id"]) for c in head["related"]))
        lines += ["---", body]
        if note:
            lines.append("[%s]" % note)
        return "\n".join(lines)
    emit(a, dict(head, body=body, note=note), human)


def cmd_types(a):
    types = load_types()
    total = lambda tid: sum(types[d]["entries"] for d in descendants(types, tid))
    roots = sorted([t for t in types.values() if not t["parent"] or t["parent"] not in types], key=lambda t: t["title"].lower())

    def walk(t, depth, out):
        out.append("%s- %s  (%d%s)  %s%s" % ("  " * depth, t["title"], t["entries"],
                                           "" if total(t["id"]) == t["entries"] else ", %d with children" % total(t["id"]),
                                           t["id"], ("  · " + t["desc"].split("\n")[0][:80]) if t["desc"] else ""))
        for c in sorted([c for c in types.values() if c["parent"] == t["id"]], key=lambda c: c["title"].lower()):
            walk(c, depth + 1, out)
        return out
    lines = ["%d types, %d entries typed" % (len(types), sum(t["entries"] for t in types.values()))]
    for r in roots:
        walk(r, 0, lines)
    emit(a, dict(types=list(types.values())), "\n".join(lines))


def cmd_type(a):
    types = load_types()
    ty, cand = resolve_type(types, a.ref)
    if not ty:
        print("no single type matches %r; candidates: %s" % (a.ref, ", ".join("%s (%s)" % (t["title"], t["id"]) for t in cand)))
        sys.exit(3)
    r = T.get_record(KT, ty["id"], [FT["title"], FT["context"], FT["parent"], FT["children"], FT["entries"], FT["credentials"]])
    f = r["fields"]
    d = dict(id=r["id"], title=f.get(FT["title"]), description=f.get(FT["context"]) or "", parent=f.get(FT["parent"]),
             children=f.get(FT["children"]) or [], credentials=f.get(FT["credentials"]), entries=f.get(FT["entries"]) or [])

    def human():
        out = ["# %s  (%s)" % (d["title"], d["id"]), "description: " + (d["description"] or "(none)")]
        if d["parent"]:
            out.append("parent: %s" % d["parent"].get("title"))
        if d["children"]:
            out.append("children: " + ", ".join(c.get("title") for c in d["children"]))
        if d["credentials"]:
            out.append("credentials: " + d["credentials"])
        out.append("%d entries:" % len(d["entries"]))
        out += ["  %s  %s" % (e["id"], e.get("title")) for e in d["entries"]]
        return "\n".join(out)
    emit(a, d, human)


def cmd_tree(a):
    proj = [F["title"], F["type"], F["parent"], F["children"], F["related"]]
    r = resolve_entry(a.ref, proj)
    chain, cur = [], r["fields"].get(F["parent"])
    while cur and len(chain) < 10:
        chain.append(cur)
        cur = T.get_record(K, cur["id"], [F["title"], F["parent"]])["fields"].get(F["parent"])
    f = r["fields"]
    d = dict(id=r["id"], title=f.get(F["title"]), type=ftitle(f.get(F["type"])), ancestors=chain[::-1],
             children=f.get(F["children"]) or [], related=f.get(F["related"]) or [])

    def human():
        out = []
        for i, p in enumerate(d["ancestors"]):
            out.append("%s%s (%s)" % ("  " * i, p.get("title"), p["id"]))
        depth = len(d["ancestors"])
        out.append("%s* %s (%s) [%s]" % ("  " * depth, d["title"], d["id"], d["type"] or "untyped"))
        out += ["%s- %s (%s)" % ("  " * (depth + 1), c.get("title"), c["id"]) for c in d["children"]]
        out.append("related: " + ("; ".join("%s (%s)" % (c.get("title"), c["id"]) for c in d["related"]) or "none"))
        return "\n".join(out)
    emit(a, d, human)


# ---------- commands: write ----------

def read_body(a):
    if getattr(a, "body_file", None) or getattr(a, "text_file", None):
        p = a.body_file if getattr(a, "body_file", None) else a.text_file
        return sys.stdin.read() if p == "-" else Path(p).read_text()
    return getattr(a, "body", None) or getattr(a, "text", None) or ""


def words(title):
    return [w for w in re.findall(r"[a-z0-9][a-z0-9.+_-]*", title.lower()) if len(w) >= 3 and w not in STOP]


def similar_titles(title, exclude=()):
    ws = words(title)
    if not ws:
        return []
    flt = {"conjunction": "or", "filterSet": [{"fieldId": F["title"], "operator": "contains", "value": w} for w in ws[:8]]}
    recs = T.get_records(K, flt, [F["title"], F["type"], F["active"]])
    out = []
    for r in recs:
        t = r["fields"].get(F["title"]) or ""
        ratio = difflib.SequenceMatcher(None, title.lower(), t.lower()).ratio()
        jac = len(set(ws) & set(words(t))) / max(1, len(set(ws) | set(words(t))))
        if r["id"] not in exclude and (ratio >= 0.55 or jac >= 0.5):
            out.append(dict(id=r["id"], title=t, type=ftitle(r["fields"].get(F["type"])), similarity=round(max(ratio, jac), 2),
                            exact=t.strip().lower() == title.strip().lower(), active=r["fields"].get(F["active"]) is True))
    return sorted(out, key=lambda x: -x["similarity"])[:5]


def parse_refer(spec):
    kind, _, rid = spec.partition(":")
    if kind not in WORK or not REC.fullmatch(rid):
        sys.exit("bad --refer %r: use project:recXXX, task:recXXX or goal:recXXX" % spec)
    return kind, rid


def add_link(table, rid, field, target):
    """Add `target` to a many-to-many link cell without dropping existing links; verified by read-back."""
    cur = ids(T.get_record(table, rid, [field])["fields"].get(field))
    if target in cur:
        return "already linked"
    T.call("PATCH", "/api/table/%s/record/%s" % (table, rid),
           body={"fieldKeyType": "id", "record": {"fields": {field: [{"id": i} for i in cur + [target]]}}})
    got = ids(T.get_record(table, rid, [field])["fields"].get(field))
    if set(got) != set(cur + [target]):
        sys.exit("VERIFY FAILED on %s %s %s: expected %s, got %s" % (table, rid, field, cur + [target], got))
    return "linked"


def add_refer(kind, rid, kid):
    """goal/project/task refer_knowledge is one-way: write it on the work record."""
    table, field, _ = WORK[kind]
    return add_link(table, rid, field, kid)


def add_related(a_id, b_id):
    """related_knowledge has no working reverse field (its symmetric field id is dangling), so write both sides."""
    return add_link(K, a_id, F["related"], b_id), add_link(K, b_id, F["related"], a_id)


def cmd_capture(a):
    body = read_body(a)
    blocks, warns, plan = [], [], {}
    title = (a.title or "").strip()
    if not title:
        blocks.append("title is empty")
    elif len(title) > 120:
        warns.append("title is %d chars; keep it under 120 and searchable" % len(title))
    if title and " - " not in title:
        warns.append('title does not follow "<Subject> - <Aspect>" (e.g. "Caddy - Reverse Proxy Basics")')

    dups = similar_titles(title) if title else []
    if any(d["exact"] for d in dups) and not a.allow_duplicate:
        blocks.append("an entry with this exact title exists; update it with `kb.py append` or pass --allow-duplicate")
    elif dups:
        warns.append("similar entries exist; consider appending to one of them instead")

    types = load_types()
    ty, cand = resolve_type(types, a.type)
    new_type = None
    if not ty:
        if a.new_type:
            pt = None
            if a.parent_type:
                pt, pc = resolve_type(types, a.parent_type)
                if not pt:
                    blocks.append("unknown --parent-type %r; candidates: %s" % (a.parent_type, ", ".join(t["title"] for t in pc)))
            new_type = dict(title=a.type.strip(), parent=pt)
        else:
            blocks.append("no single type matches %r; candidates: %s (or pass --new-type, which needs the user's OK)" % (
                a.type, ", ".join("%s" % t["title"] for t in cand)))
    elif ty["title"].strip().lower() != a.type.strip().lower() and ty["id"] != a.type:
        warns.append("type %r resolved by partial match to %r" % (a.type, ty["title"]))
    type_title = ty["title"] if ty else (new_type or {}).get("title")

    if not body.strip():
        warns.append("body is empty; an entry should say what it is, when it applies and the steps or facts")
    elif len(body) > 600 and not headings(body):
        warns.append("long body without Markdown headings; add sections (When to use / Steps / Caveats)")
    secrets = safety.scan(body)
    if secrets and type_title and not safety.is_credential_type(type_title):
        warns.append("body looks like it holds %d secret(s) but the type %r is not a credential type; "
                     "consider --type credentials (or a credential_* type)" % (len(secrets), type_title))

    links = {}
    for key, refs in (("parent", [a.parent] if a.parent else []), ("related", a.related or [])):
        for ref in refs:
            if not REC.fullmatch(ref):
                blocks.append("--%s needs a record id, got %r" % (key, ref))
                continue
            links.setdefault(key, []).append(dict(id=ref, title=T.get_record(K, ref, [F["title"]])["fields"].get(F["title"])))
    refers = []
    for spec in a.refer or []:
        kind, rid = parse_refer(spec)
        table, _, tfield = WORK[kind]
        refers.append(dict(kind=kind, id=rid, title=T.get_record(table, rid, [tfield])["fields"].get(tfield)))

    plan = dict(title=title, type=type_title, type_id=ty["id"] if ty else None, new_type=bool(new_type),
                chars=len(body), headings=[t for _, _, t in headings(body)], parent=links.get("parent", [None])[0],
                related=links.get("related", []), refer=refers, duplicates=dups,
                secrets=[dict(kind=k, line=l, hint=h) for k, l, h in secrets], warnings=warns, blocked=blocks)

    def preview():
        out = ["capture preview", "  title:   %s" % title, "  type:    %s%s" % (type_title, "  (NEW TYPE%s)" % (
            " under " + new_type["parent"]["title"] if new_type and new_type["parent"] else "") if new_type else ""),
            "  body:    %s, headings: %s" % (kchars(len(body)), ", ".join(plan["headings"][:8]) or "none")]
        if plan["parent"]:
            out.append("  parent:  %s (%s)" % (plan["parent"]["title"], plan["parent"]["id"]))
        for r in plan["related"]:
            out.append("  related: %s (%s)" % (r["title"], r["id"]))
        for r in refers:
            out.append("  refer:   %s %s (%s)" % (r["kind"], r["title"], r["id"]))
        for d in dups:
            out.append("  similar: %.2f  %s  [%s]  %s%s" % (d["similarity"], d["title"], d["type"], d["id"], "  EXACT" if d["exact"] else ""))
        for s in plan["secrets"]:
            out.append("  secret?: line %d %s %s" % (s["line"], s["kind"], s["hint"]))
        out += ["  WARN: " + w for w in warns] + ["  BLOCKED: " + b for b in blocks]
        return "\n".join(out)

    if blocks or not a.yes:
        emit(a, dict(plan, written=False), lambda: preview() + ("" if blocks else "\nDRY RUN: nothing written. Re-run with --yes to apply."))
        sys.exit(2 if blocks else 0)

    if new_type:
        tf = {FT["title"]: new_type["title"], FT["active"]: True}
        if new_type["parent"]:
            tf[FT["parent"]] = {"id": new_type["parent"]["id"]}
        type_id = T.call("POST", "/api/table/%s/record" % KT, body={"fieldKeyType": "id", "records": [{"fields": tf}]})["records"][0]["id"]
    else:
        type_id = ty["id"]
    fields = {F["title"]: title, F["context"]: body, F["type"]: {"id": type_id}, F["active"]: True}
    if links.get("parent"):
        fields[F["parent"]] = {"id": links["parent"][0]["id"]}
    kid = T.call("POST", "/api/table/%s/record" % K, body={"fieldKeyType": "id", "records": [{"fields": fields}]})["records"][0]["id"]
    got = T.get_record(K, kid, [F["title"], F["context"], F["type"]])["fields"]
    if got.get(F["title"]) != title or ids(got.get(F["type"])) != [type_id] or (got.get(F["context"]) or "").strip() != body.strip():
        sys.exit("VERIFY FAILED: created %s but the stored values differ; inspect with kb.py get %s" % (kid, kid))
    for r in links.get("related", []):
        add_related(kid, r["id"])
    results = [dict(r, result=add_refer(r["kind"], r["id"], kid)) for r in refers]
    emit(a, dict(plan, written=True, id=kid, type_id=type_id, refer=results),
         lambda: preview() + "\ncreated %s \"%s\" [%s]%s; verified" % (
             kid, title, type_title, "".join("; %s %s %s" % (r["result"], r["kind"], r["id"]) for r in results)))


def append_section(text, heading, body):
    """Append body to the end of `heading`'s '## ' section; create the section at the end if absent.
    Same algorithm as project-management write.py ctx-append."""
    body = body.strip("\n")
    lines = text.split("\n")
    start = next((i for i, l in enumerate(lines) if l.strip() == heading.strip()), None)
    if start is None:
        return text.rstrip("\n") + ("\n\n" if text.strip() else "") + heading + "\n" + body + "\n"
    end = next((i for i in range(start + 1, len(lines)) if lines[i].startswith("## ")), len(lines))
    section_ = "\n".join(lines[start:end]).rstrip("\n")
    tight = section_.split("\n")[-1].startswith("- ") and body.startswith("- ")
    sep = "\n" if tight else "\n\n"
    return "\n".join(lines[:start] + [section_ + sep + body + ("\n" if end < len(lines) else "")] + lines[end:]).rstrip("\n") + "\n"


def cmd_append(a):
    text = read_body(a)
    if not text.strip():
        sys.exit("empty text")
    r = resolve_entry(a.ref, [F["title"], F["context"], F["type"]])
    kid, before = r["id"], r["fields"].get(F["context"]) or ""
    entry = text.strip("\n") if a.no_date else "### %s\n%s" % (T.today().isoformat(), text.strip("\n"))
    after = append_section(before, a.section, entry)
    secrets = safety.scan(text)
    type_title = ftitle(r["fields"].get(F["type"]))
    plan = dict(id=kid, title=r["fields"].get(F["title"]), section=a.section, added_chars=len(after) - len(before),
                secrets=[dict(kind=k, line=l, hint=h) for k, l, h in secrets])
    warn = ("WARN: text looks like it holds %d secret(s) and %r is not a credential type" % (len(secrets), type_title)
            if secrets and not safety.is_credential_type(type_title) else "")
    if not a.yes:
        emit(a, dict(plan, written=False), lambda: "append preview: %s (%s) · section %r · +%d chars\n%s\n%s\nDRY RUN: nothing written. Re-run with --yes to apply." % (
            plan["title"], kid, a.section, plan["added_chars"], entry, warn))
        return
    again = T.get_record(K, kid, [F["context"]])["fields"].get(F["context"]) or ""
    if again != before:
        sys.exit("ABORT: the entry changed while preparing the edit. Re-run to merge against the new text.")
    T.call("PATCH", "/api/table/%s/record/%s" % (K, kid), body={"fieldKeyType": "id", "record": {"fields": {F["context"]: after}}})
    got = T.get_record(K, kid, [F["context"]])["fields"].get(F["context"]) or ""
    if got.strip() != after.strip():
        print("VERIFY FAILED: stored text differs; previous text follows for manual restore:\n" + before)
        sys.exit(1)
    emit(a, dict(plan, written=True), "appended to %s (%s) under %s; verified (rest of the entry unchanged)%s" % (
        plan["title"], kid, a.section, ("\n" + warn) if warn else ""))


def remove_link(table, rid, field, target):
    """Remove `target` from a many-to-many link cell, keeping the rest; verified by read-back."""
    cur = ids(T.get_record(table, rid, [field])["fields"].get(field))
    if target not in cur:
        return "not linked"
    keep = [i for i in cur if i != target]
    T.call("PATCH", "/api/table/%s/record/%s" % (table, rid),
           body={"fieldKeyType": "id", "record": {"fields": {field: [{"id": i} for i in keep] or None}}})
    got = ids(T.get_record(table, rid, [field])["fields"].get(field))
    if set(got) != set(keep):
        sys.exit("VERIFY FAILED on %s %s %s: expected %s, got %s" % (table, rid, field, keep, got))
    return "unlinked"


def entry_ref(ref):
    return resolve_entry(ref, [F["title"]])


def work_record(spec):
    kind, rid = parse_refer(spec)
    table, field, tfield = WORK[kind]
    r = T.get_record(table, rid, [tfield, field])
    return kind, rid, r["fields"].get(tfield), r["fields"].get(field) or []


# ---------- commands: links ----------

def cmd_link(a):
    proj = [F["title"], F["type"], F["parent"], F["related"]]
    r = resolve_entry(a.ref, proj)
    kid, f = r["id"], r["fields"]
    changes, ops = [], []
    if a.type:
        types = load_types()
        ty, cand = resolve_type(types, a.type)
        if not ty:
            sys.exit("no single type matches %r; candidates: %s" % (a.type, ", ".join(t["title"] for t in cand)))
        changes.append("type: %s -> %s" % (ftitle(f.get(F["type"])), ty["title"]))
        ops.append(("set", F["type"], {"id": ty["id"]}))
    if a.title:
        changes.append("title: %s -> %s" % (f.get(F["title"]), a.title))
        ops.append(("set", F["title"], a.title))
    if a.parent or a.no_parent:
        if a.parent and a.parent == kid:
            sys.exit("an entry cannot be its own parent")
        new = entry_ref(a.parent) if a.parent else None
        changes.append("parent: %s -> %s" % (ftitle(f.get(F["parent"])), new["fields"].get(F["title"]) if new else None))
        ops.append(("set", F["parent"], {"id": new["id"]} if new else None))
    for ref in a.related or []:
        o = entry_ref(ref)
        changes.append("related +: %s (%s), both sides" % (o["fields"].get(F["title"]), o["id"]))
        ops.append(("relate", o["id"], None))
    for ref in a.unrelate or []:
        o = entry_ref(ref)
        changes.append("related -: %s (%s), both sides" % (o["fields"].get(F["title"]), o["id"]))
        ops.append(("unrelate", o["id"], None))
    if not ops:
        sys.exit("nothing to change: give --type, --title, --parent/--no-parent, --related or --unrelate")
    head = "link %s (%s)\n  " % (f.get(F["title"]), kid) + "\n  ".join(changes)
    if not a.yes:
        emit(a, dict(id=kid, changes=changes, written=False), head + "\nDRY RUN: nothing written. Re-run with --yes to apply.")
        return
    sets = {fid: v for op, fid, v in ops if op == "set"}
    if sets:
        T.call("PATCH", "/api/table/%s/record/%s" % (K, kid), body={"fieldKeyType": "id", "record": {"fields": sets}})
        got = T.get_record(K, kid, list(sets))["fields"]
        for fid, v in sets.items():
            want = ids(v) if isinstance(v, dict) else v
            have = ids(got.get(fid)) if isinstance(v, dict) or v is None else got.get(fid)
            if (v is None and got.get(fid)) or (v is not None and have != want):
                sys.exit("VERIFY FAILED on %s field %s" % (kid, fid))
    for op, other, _ in ops:
        if op == "relate":
            add_related(kid, other)
        elif op == "unrelate":
            remove_link(K, kid, F["related"], other), remove_link(K, other, F["related"], kid)
    emit(a, dict(id=kid, changes=changes, written=True), head + "\napplied; verified")


def cmd_refer(a):
    kind, rid, wtitle, cur = work_record(a.to)
    table, field, _ = WORK[kind]
    entries = [entry_ref(r) for r in a.refs]
    have = set(ids(cur))
    rows = [dict(id=e["id"], title=e["fields"].get(F["title"]),
                 action=("remove" if e["id"] in have else "not linked") if a.remove else ("already linked" if e["id"] in have else "add"))
            for e in entries]
    head = "%s %s \"%s\" refer_knowledge (%d now)\n" % (kind, rid, wtitle, len(have)) + "\n".join(
        "  %-14s %s (%s)" % (r["action"], r["title"], r["id"]) for r in rows)
    if not a.yes:
        emit(a, dict(kind=kind, id=rid, title=wtitle, rows=rows, written=False), head + "\nDRY RUN: nothing written. Re-run with --yes to apply.")
        return
    for r in rows:
        if r["action"] == "add":
            add_link(table, rid, field, r["id"])
        elif r["action"] == "remove":
            remove_link(table, rid, field, r["id"])
    emit(a, dict(kind=kind, id=rid, title=wtitle, rows=rows, written=True), head + "\napplied; verified")


def trace_rows(kid):
    out = []
    for kind, (table, field, tfield) in WORK.items():
        for r in T.get_records(table, {"conjunction": "and", "filterSet": [{"fieldId": field, "operator": "hasAnyOf", "value": [kid]}]}, [tfield]):
            out.append(dict(kind=kind, id=r["id"], title=r["fields"].get(tfield)))
    return out


def cmd_trace(a):
    e = entry_ref(a.ref)
    rows = trace_rows(e["id"])
    emit(a, dict(id=e["id"], title=e["fields"].get(F["title"]), used_by=rows),
         "%s (%s) is referenced by %d work record(s)%s" % (e["fields"].get(F["title"]), e["id"], len(rows),
                                                            "".join("\n  %-7s %s  %s" % (r["kind"], r["id"], r["title"]) for r in rows)))


def cmd_for_work(a):
    """Knowledge linked to a project (with its goal and tasks), a task (with its project) or a goal, plus suggestions."""
    kind, rid, wtitle, cur = work_record(a.target)
    linked = {x["id"]: dict(id=x["id"], title=x.get("title"), via="%s %s" % (kind, rid)) for x in cur}
    related_work = []
    if kind == "project":
        tasks = T.get_records(WORK["task"][0], {"conjunction": "and", "filterSet": [
            {"fieldId": "fld6X3nrMTQlYiV5XSa", "operator": "is", "value": rid}]}, [WORK["task"][2], WORK["task"][1]])
        related_work = [("task", t["id"], t["fields"].get(WORK["task"][1]) or []) for t in tasks]
        goal = T.get_record(WORK["project"][0], rid, ["flduhpVlKOqQrmbIQv2"])["fields"].get("flduhpVlKOqQrmbIQv2")
        for g in ([goal] if isinstance(goal, dict) else goal or []):
            related_work.append(("goal", g["id"], T.get_record(WORK["goal"][0], g["id"], [WORK["goal"][1]])["fields"].get(WORK["goal"][1]) or []))
    elif kind == "task":
        proj = T.get_record(WORK["task"][0], rid, ["fld6X3nrMTQlYiV5XSa"])["fields"].get("fld6X3nrMTQlYiV5XSa")
        if proj:
            related_work.append(("project", proj["id"], T.get_record(WORK["project"][0], proj["id"], [WORK["project"][1]])["fields"].get(WORK["project"][1]) or []))
    for k2, r2, links in related_work:
        for x in links:
            linked.setdefault(x["id"], dict(id=x["id"], title=x.get("title"), via="%s %s" % (k2, r2)))
    sugg = []
    terms = (a.terms or words(wtitle or ""))[:8]
    if terms and a.suggest:
        groups = [alias_group(t) for t in terms]
        flt = {"conjunction": "and", "filterSet": [{"conjunction": "or", "filterSet": [contains_any(g) for g in groups]},
                                                   {"fieldId": F["active"], "operator": "is", "value": True}]}
        recs = [r for r in T.get_records(K, flt, [F["title"], F["type"], F["context"]]) if r["id"] not in linked]
        recs.sort(key=lambda r: score(r["fields"], groups), reverse=True)
        sugg = [dict(id=r["id"], title=r["fields"].get(F["title"]), type=ftitle(r["fields"].get(F["type"])),
                     score=score(r["fields"], groups)) for r in recs[:a.suggest]]

    def human():
        out = ["%s %s \"%s\"" % (kind, rid, wtitle), "linked knowledge (%d):" % len(linked)]
        out += ["  %s  %s  (via %s)" % (x["id"], x["title"], x["via"]) for x in linked.values()] or ["  none"]
        if a.suggest:
            out.append("suggested (search: %s):" % " ".join(terms))
            out += ["  %s  %s  [%s]" % (s["id"], s["title"], s["type"] or "untyped") for s in sugg] or ["  none"]
            out.append("link picks with: kb.py refer <id> ... --to %s:%s --yes" % (kind, rid))
        return "\n".join(out)
    emit(a, dict(kind=kind, id=rid, title=wtitle, linked=list(linked.values()), suggested=sugg, search_terms=terms), human)


def cmd_archive(a):
    r = resolve_entry(a.ref, [F["title"], F["active"]])
    kid, title = r["id"], r["fields"].get(F["title"])
    sets = {F["active"]: True, F["deleted"]: None} if a.restore else {F["active"]: False, F["deleted"]: T.today().isoformat()}
    used = trace_rows(kid)
    head = "%s %s (%s)%s" % ("restore" if a.restore else "archive", title, kid,
                              "\n  note: referenced by %d work record(s); links are kept" % len(used) if used else "")
    if not a.yes:
        emit(a, dict(id=kid, title=title, written=False), head + "\nDRY RUN: nothing written. Re-run with --yes to apply.")
        return
    T.call("PATCH", "/api/table/%s/record/%s" % (K, kid), body={"fieldKeyType": "id", "record": {"fields": sets}})
    got = T.get_record(K, kid, [F["active"]])["fields"].get(F["active"]) is True
    if got != bool(a.restore):
        sys.exit("VERIFY FAILED: is_active is %s" % got)
    emit(a, dict(id=kid, title=title, written=True), head + "\napplied; verified")


def cmd_type_set(a):
    """Create a type (--create) or change one: title, parent_type, description. Needs the user's OK (taxonomy is shared)."""
    types = load_types()
    sets, changes = {}, []
    if a.create:
        if any(t["title"].strip().lower() == a.ref.strip().lower() for t in types.values()):
            sys.exit("type %r already exists" % a.ref)
        ty = None
        sets[FT["title"]], sets[FT["active"]] = a.ref.strip(), True
        changes.append("create type %r" % a.ref.strip())
    else:
        ty, cand = resolve_type(types, a.ref)
        if not ty:
            sys.exit("no single type matches %r; candidates: %s" % (a.ref, ", ".join(t["title"] for t in cand)))
        if a.title:
            sets[FT["title"]] = a.title
            changes.append("title: %s -> %s" % (ty["title"], a.title))
    if a.parent_type or a.no_parent:
        pt = None
        if a.parent_type:
            pt, pc = resolve_type(types, a.parent_type)
            if not pt:
                sys.exit("no single type matches --parent-type %r; candidates: %s" % (a.parent_type, ", ".join(t["title"] for t in pc)))
            if ty and pt["id"] in descendants(types, ty["id"]):
                sys.exit("refusing: %r is %r itself or one of its descendants (would make a cycle)" % (pt["title"], ty["title"]))
        sets[FT["parent"]] = {"id": pt["id"]} if pt else None
        changes.append("parent_type: %s -> %s" % (types[ty["parent"]]["title"] if ty and ty["parent"] in types else None,
                                                   pt["title"] if pt else None))
    if a.description is not None:
        sets[FT["context"]] = a.description
        changes.append("description: %r" % a.description[:80])
    if not sets:
        sys.exit("nothing to change: give --title, --parent-type/--no-parent or --description (or --create)")
    head = "type %s\n  " % (ty["title"] if ty else a.ref) + "\n  ".join(changes)
    if not a.yes:
        emit(a, dict(changes=changes, written=False), head + "\nDRY RUN: nothing written. Re-run with --yes to apply (needs the user's OK).")
        return
    if a.create:
        tid = T.call("POST", "/api/table/%s/record" % KT, body={"fieldKeyType": "id", "records": [{"fields": sets}]})["records"][0]["id"]
    else:
        tid = ty["id"]
        T.call("PATCH", "/api/table/%s/record/%s" % (KT, tid), body={"fieldKeyType": "id", "record": {"fields": sets}})
    got = T.get_record(KT, tid, list(sets))["fields"]
    for fid, v in sets.items():
        ok = (not got.get(fid)) if v is None else (ids(got.get(fid)) == ids(v) if isinstance(v, dict) else
                                                   bool(got.get(fid)) == v if isinstance(v, bool) else got.get(fid) == v)
        if not ok:
            sys.exit("VERIFY FAILED on type %s field %s" % (tid, fid))
    emit(a, dict(id=tid, changes=changes, written=True), head + "\napplied; verified (%s)" % tid)


def cmd_doctor(a):
    import doctor
    doctor.run(a, sys.modules[__name__])


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)

    def add(name, fn, **kw):
        s = sub.add_parser(name, **kw)
        s.add_argument("--json", action="store_true")
        s.set_defaults(fn=fn)
        return s

    s = add("find", cmd_find, help="search titles and bodies")
    s.add_argument("terms", nargs="+")
    s.add_argument("--any", action="store_true", help="match any term (default: all terms)")
    s.add_argument("--exact", action="store_true", help="no alias expansion")
    s.add_argument("--type", help="type name or id; includes child types")
    s.add_argument("--all", action="store_true", help="include archived entries")
    s.add_argument("--limit", type=int, default=10)
    s.add_argument("--titles", action="store_true", help="no snippets")

    s = add("get", cmd_get, help="read one entry")
    s.add_argument("ref", help="record id or title")
    s.add_argument("--toc", action="store_true")
    s.add_argument("--section")
    s.add_argument("--max-chars", type=int)

    add("types", cmd_types, help="type tree with counts")
    s = add("type", cmd_type, help="one type in detail")
    s.add_argument("ref")
    s = add("tree", cmd_tree, help="an entry's parent chain, children, related")
    s.add_argument("ref")

    s = add("capture", cmd_capture, help="create an entry (dry-run unless --yes)")
    s.add_argument("--title", required=True)
    s.add_argument("--type", required=True)
    g = s.add_mutually_exclusive_group()
    g.add_argument("--body")
    g.add_argument("--body-file", help="path, or - for stdin")
    s.add_argument("--parent")
    s.add_argument("--related", nargs="*")
    s.add_argument("--refer", action="append", help="project:REC | task:REC | goal:REC")
    s.add_argument("--new-type", action="store_true", help="create --type if it does not exist (needs the user's OK)")
    s.add_argument("--parent-type")
    s.add_argument("--allow-duplicate", action="store_true")
    s.add_argument("--yes", action="store_true")

    s = add("append", cmd_append, help="append a dated section to an entry (dry-run unless --yes)")
    s.add_argument("ref")
    g = s.add_mutually_exclusive_group(required=True)
    g.add_argument("--text")
    g.add_argument("--text-file", help="path, or - for stdin")
    s.add_argument("--section", default="## Updates")
    s.add_argument("--no-date", action="store_true")
    s.add_argument("--yes", action="store_true")

    s = add("link", cmd_link, help="organise one entry: type, title, parent, related (dry-run unless --yes)")
    s.add_argument("ref")
    s.add_argument("--type")
    s.add_argument("--title")
    s.add_argument("--parent")
    s.add_argument("--no-parent", action="store_true")
    s.add_argument("--related", nargs="*")
    s.add_argument("--unrelate", nargs="*")
    s.add_argument("--yes", action="store_true")

    s = add("refer", cmd_refer, help="link entries to a goal/project/task refer_knowledge (dry-run unless --yes)")
    s.add_argument("refs", nargs="+", help="entry ids or titles")
    s.add_argument("--to", required=True, help="project:REC | task:REC | goal:REC")
    s.add_argument("--remove", action="store_true")
    s.add_argument("--yes", action="store_true")

    s = add("trace", cmd_trace, help="which goals/projects/tasks reference an entry")
    s.add_argument("ref")

    s = add("for-work", cmd_for_work, help="knowledge linked to a project/task/goal, plus suggestions")
    s.add_argument("target", help="project:REC | task:REC | goal:REC")
    s.add_argument("--terms", nargs="*", help="search words for suggestions (default: words of the work title)")
    s.add_argument("--suggest", type=int, default=5, help="number of suggestions (0 = none)")

    s = add("archive", cmd_archive, help="soft delete an entry (dry-run unless --yes)")
    s.add_argument("ref")
    s.add_argument("--restore", action="store_true")
    s.add_argument("--yes", action="store_true")

    s = add("type-set", cmd_type_set, help="create or change a type (needs the user's OK; dry-run unless --yes)")
    s.add_argument("ref", help="type name or id (the new name with --create)")
    s.add_argument("--create", action="store_true")
    s.add_argument("--title")
    s.add_argument("--parent-type")
    s.add_argument("--no-parent", action="store_true")
    s.add_argument("--description")
    s.add_argument("--yes", action="store_true")

    s = add("doctor", cmd_doctor, help="read-only data-quality report (clean-up groups A-F)")
    s.add_argument("--all", action="store_true", help="include archived entries")
    s.add_argument("--limit", type=int, default=12, help="items shown per check")

    a = p.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()
