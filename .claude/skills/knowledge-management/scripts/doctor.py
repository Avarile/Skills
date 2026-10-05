"""Read-only data-quality report for the knowledge base (`kb.py doctor`). Never writes.

Groups match the clean-up plan (project "Knowledge Management Skill", Step 13):
  A type tree   B untyped   C wrong type   D series without a hub   E temp / empty   F near-duplicates
  plus G secrets outside credential types, H link coverage and I content risks (information only).
Secret values are compared internally and never printed: reuse is reported as a short keyed hash plus entry titles.
The key is random per run, so the hash cannot be looked up or brute-forced and is only comparable within one report.
Every finding carries the kb.py command that would fix it; apply only what the user approves, group by group.
"""
import difflib, hashlib, hmac, itertools, os, re

import safety

SERIES = re.compile(r"^(.*?)[\s:\-–=>]*\b(?:step|part)\s*(\d+)\b", re.I)
TEMPISH = re.compile(r"\b(temp|tmp|test|delete later|todo|wip)\b", re.I)
EMBED = re.compile(r"!\\?\[\\?\[[^\]\n]+\]\]")  # Obsidian ![[...]], also stored escaped as !\[\[...]]
FILLER = re.compile(r"\b(Certainly!|Sure!|As an AI\b|I hope this helps|Let me know if you|Feel free to (ask|reach out)|Great question|Want me to|Would you like me to|Do you want me to|Shall I\b|I'll include|verified this session|Here's the complete)", re.I)


_HID_KEY = os.urandom(16)


def _hid(v):
    return hmac.new(_HID_KEY, v.encode(), hashlib.sha256).hexdigest()[:8]


def _series(title):
    m = SERIES.match(title or "")
    return (re.sub(r"[\s\-:]+$", "", m.group(1)).strip().lower(), m.group(2)) if m and m.group(1).strip() else (None, None)


def _shingles(text, n=3):
    w = re.findall(r"\w+", (text or "").lower())
    return {" ".join(w[i:i + n]) for i in range(max(0, len(w) - n + 1))}


def run(a, kb):
    T, F, FT = kb.T, kb.F, kb.FT
    types = kb.load_types()
    ents = T.get_records(kb.K, None, [F["title"], F["context"], F["type"], F["parent"], F["related"], F["active"]])
    ents = [e for e in ents if e["fields"].get(F["active"]) is True or a_all(a)]
    used = set()
    for kind, (table, field, _) in kb.WORK.items():
        for r in T.get_records(table, {"conjunction": "and", "filterSet": [{"fieldId": field, "operator": "isNotEmpty", "value": None}]}, [field]):
            used.update(kb.ids(r["fields"].get(field)))
    title = lambda e: e["fields"].get(F["title"]) or ""
    tname = lambda e: kb.ftitle(e["fields"].get(F["type"]))
    findings = []

    def add(group, check, items, fix, note=""):
        if items:
            findings.append(dict(group=group, check=check, count=len(items), items=items, fix=fix, note=note))

    # A. type tree
    add("A", "types without a description", [t["title"] for t in types.values() if not t["desc"]],
        'kb.py type-set "<type>" --description "<what belongs here>" --yes')
    by_title = {t["title"].strip().lower(): t for t in types.values()}
    proposals = {}
    for t in types.values():
        if t["parent"]:
            continue
        low = t["title"].lower()
        if safety.is_credential_type(low) and low != "credentials":
            proposals.setdefault("credentials", []).append(t["title"])
        elif low.startswith("missav_meta_"):
            proposals.setdefault("missav_meta", []).append(t["title"])
        elif " - " in t["title"]:
            proposals.setdefault(low.split(" - ")[0].strip(), []).append(t["title"])
    tree = []
    for parent, kids in sorted(proposals.items()):
        if len(kids) >= 2 or parent in by_title:
            exists = parent in by_title
            tree.append("%s%s <- %s" % (parent, "" if exists else " (new)", ", ".join(sorted(kids))))
    add("A", "proposed parent types", tree,
        'kb.py type-set "<parent>" --create --yes; then kb.py type-set "<child>" --parent-type "<parent>" --yes',
        "parent_type is the only tree link; child_types is independent and never written")
    add("A", "types outside the '<domain> - <topic>' naming", sorted(
        t["title"] for t in types.values() if " - " not in t["title"] and not t["title"].lower().startswith(("credential", "missav"))
        and t["title"].lower() not in proposals), 'kb.py type-set "<type>" --title "<domain> - <topic>" --yes')
    add("A", "types with no entries", sorted(t["title"] for t in types.values() if t["entries"] == 0),
        "keep (planned), give it a parent, or leave; types are never deleted by this skill")

    # B. untyped
    add("B", "entries without a type", ["%s  %s" % (e["id"], title(e) or "(no title)") for e in ents if not e["fields"].get(F["type"])],
        'kb.py link <id> --type "<type>" --yes')

    # C/D. series
    groups = {}
    for e in ents:
        key, num = _series(title(e))
        if key:
            groups.setdefault(key, []).append((num, e))
    wrong, hubs = [], []
    for key, members in groups.items():
        if len(members) < 2:
            continue
        counts = {}
        for _, e in members:
            counts[tname(e)] = counts.get(tname(e), 0) + 1
        major = max(counts, key=counts.get)
        for _, e in members:
            if tname(e) != major and counts[tname(e)] < counts[major]:
                wrong.append("%s  %s  [%s] -> [%s]" % (e["id"], title(e), tname(e), major))
        if not any(e["fields"].get(F["parent"]) for _, e in members):
            hubs.append("%s: %s" % (key, "; ".join("%s (%s)" % (title(e), e["id"]) for _, e in sorted(members, key=lambda m: int(m[0])))))
    add("C", "entries typed differently from the rest of their series", wrong, 'kb.py link <id> --type "<type>" --yes')
    add("D", "step series without a hub entry", hubs,
        'kb.py capture --title "<Series>" --type "<type>" --body-file hub.md --yes; then kb.py link <step id> --parent <hub id> --yes')

    # E. temp / empty
    add("E", "entries without a title", [e["id"] for e in ents if not title(e).strip()], 'kb.py link <id> --title "<title>" --yes')
    add("E", "temporary-looking entries", ["%s  %s  [%s]" % (e["id"], title(e), tname(e)) for e in ents
                                          if TEMPISH.search(title(e)) or (tname(e) or "").lower().startswith("temp")],
        "kb.py archive <id> --yes (soft), or keep and retitle")
    add("E", "entries with an empty or near-empty body (<60 chars; credential/personal types: empty only)",
        ["%s  %s  (%d chars)" % (e["id"], title(e) or "(no title)", len(e["fields"].get(F["context"]) or "")) for e in ents
         if len((e["fields"].get(F["context"]) or "").strip()) < (1 if _short_ok(tname(e)) else 60)],
        "fill with kb.py append <id> --text-file F --yes, or kb.py archive <id> --yes")

    # F. near-duplicates
    pairs = []
    sh = {e["id"]: _shingles(e["fields"].get(F["context"])) for e in ents}
    for x, y in itertools.combinations(ents, 2):
        sx, sy = _series(title(x)), _series(title(y))
        if sx[0] and sx[0] == sy[0] and sx[1] != sy[1]:
            continue  # different steps of one series are not duplicates
        tr = difflib.SequenceMatcher(None, title(x).lower(), title(y).lower()).ratio()
        a_, b_ = sh[x["id"]], sh[y["id"]]
        br = len(a_ & b_) / len(a_ | b_) if len(a_) >= 30 and len(b_) >= 30 else 0
        # Shared "<x> - docker-compose" style titles alone are not duplicates: require body overlap unless titles are near-identical.
        if br >= 0.5 or tr >= 0.9 or (tr >= 0.75 and br >= 0.2):
            pairs.append("%s %s  <->  %s %s  (title %.2f, body %.2f)" % (x["id"], title(x), y["id"], title(y), tr, br))
    add("F", "near-duplicate pairs", pairs, "merge (append one into the other, archive the rest) or kb.py link <id> --related <other> --yes")

    # E (hygiene). leftovers from pasting
    body = lambda e: e["fields"].get(F["context"]) or ""
    add("E", "bodies with leftover paste junk (Obsidian embeds, AI chat filler)",
        ["%s  %s  (%s)" % (e["id"], title(e), ", ".join(x for x, hit in (("embeds", EMBED.search(body(e))), ("chat filler", FILLER.search(body(e)))) if hit))
         for e in ents if EMBED.search(body(e)) or FILLER.search(body(e))],
        "clean the body (replace embeds with links or text, cut the chat lines) via get + update, or kb.py append a note")

    # G / H. information
    def g_item(e):
        hits = len(safety.scan(body(e)))
        return "%s  %s  [%s]  %s" % (e["id"], title(e), tname(e), "%d hit(s)" % hits if hits else "body is a bare password-like value")
    add("G", "entries outside credential types whose body looks like it holds secrets",
        [g_item(e) for e in ents if not safety.is_credential_type(tname(e)) and (safety.scan(body(e)) or safety.looks_like_bare_secret(body(e)))],
        "information only (CR-1): move to a credential type with kb.py link <id> --type credentials --yes if wanted")
    linked_par = sum(1 for e in ents if e["fields"].get(F["parent"]))
    linked_rel = sum(1 for e in ents if e["fields"].get(F["related"]))
    add("H", "link coverage", ["%d entries, %d referenced by goals/projects/tasks, %d with a parent, %d with related links" % (
        len(ents), len(used & {e["id"] for e in ents}), linked_par, linked_rel)], "link at plan and close time (project-management)")

    # I. content risks (secret hygiene across entries; values never printed)
    owners = {}
    for e in ents:
        vals = safety.values(body(e))
        if safety.looks_like_bare_secret(body(e)):
            vals.append(body(e).strip().strip("`").strip())
        for v in set(vals):
            owners.setdefault(v, set()).add(e["id"])
    names = {e["id"]: title(e) or "(no title)" for e in ents}
    reuse = ["secret #%s used in %d entries: %s" % (_hid(v), len(ids), "; ".join(sorted(names[i] for i in ids)))
             for v, ids in sorted(owners.items(), key=lambda x: -len(x[1])) if len(ids) > 1]
    add("I", "the same secret value stored in several entries", reuse,
        "rotate it where it is still used, keep one copy (a credential entry or your password manager) and point the others to it")
    stems, seen = {}, set()
    pw = [(v, ids) for v, ids in owners.items() if 8 <= len(v) <= 40 and re.search(r"[A-Za-z]", v) and re.search(r"[0-9]", v)]
    for (va, ia), (vb, ib) in itertools.combinations(pw, 2):
        ka, kb_ = safety.stem_key(va), safety.stem_key(vb)
        n = len(os.path.commonprefix([ka, kb_]))
        if ka != kb_ and n >= 6 and n >= 0.6 * min(len(ka), len(kb_)) and not (ia == ib):
            key = _hid(ka[:n])
            stems.setdefault(key, set()).update(ia | ib)
    add("I", "different secrets sharing a common stem (password reuse pattern)",
        ["stem #%s across %d entries: %s" % (k, len(ids), "; ".join(sorted(names[i] for i in ids))) for k, ids in stems.items()],
        "change these to independent passwords (a password manager can generate them)")
    add("I", "entries holding private keys", ["%s  %s  [%s]" % (e["id"], title(e), tname(e)) for e in ents
                                             if re.search(r"-----BEGIN [A-Z ]*PRIVATE KEY-----", body(e))],
        "information only: consider keeping private keys in ~/.ssh or a password manager and recording only where they live")

    summary = dict(entries=len(ents), types=len(types), findings=sum(f["count"] for f in findings if f["group"] not in "GHI"),
                   http_calls=kb.CALLS[0])

    def human():
        out = ["knowledge doctor (read-only) · %d entries · %d types · %d actionable findings · %d HTTP calls" % (
            summary["entries"], summary["types"], summary["findings"], summary["http_calls"])]
        for f in findings:
            out.append("\n[%s] %s: %d" % (f["group"], f["check"], f["count"]))
            out += ["  - " + str(i) for i in f["items"][:a.limit]]
            if f["count"] > a.limit:
                out.append("  … %d more (--limit)" % (f["count"] - a.limit))
            out.append("  fix: " + f["fix"] + (("  · " + f["note"]) if f["note"] else ""))
        return "\n".join(out)
    kb.emit(a, dict(summary=summary, findings=findings), human)


def _short_ok(type_title):
    """Credential and personal-media entries are short by design; only an empty body is a finding there."""
    t = (type_title or "").lower()
    return safety.is_credential_type(t) or t.startswith("missav")


def a_all(a):
    return getattr(a, "all", False)
