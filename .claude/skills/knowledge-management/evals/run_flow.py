#!/usr/bin/env python3
"""Live acceptance test for knowledge-management. Creates only [TEST] rows (an entry or two, a type, a task),
exercises every kb.py command, deletes what it created and verifies the baseline counts are unchanged.

  python3 skill_dev/knowledge-management/evals/run_flow.py      (from the repo root, token in .env)
"""
import hashlib, json, re, subprocess, sys, time
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCRIPTS = HERE.parent / "scripts"
sys.path.insert(0, str(SCRIPTS))
import teable as T
import safety

KB = [sys.executable, str(SCRIPTS / "kb.py")]
K, KT, TASKS = "tblVTWb1kxXSFPBq4Fq", "tblWcq6Kof1AFHvbC5e", "tblOMgDiajqa1moRRjE"
TITLE, CTX, ACTIVE, RELATED = "fldROFj15OlD8COVxX0", "fld5tr2rH8oJXLrjUo9", "fldZKMuaBBPd6tIzSG3", "fldz7U2RsCfm0j1RZOs"
TT, TPARENT = "fldvL1LqKmEAfNKVBCO", "fld924GlXY0tL5um2wk"
TASK_TITLE, TASK_REFER = "fldGqUoXO7oyq6ufX2Y", "fldJzsKyzBaDFt7bHIu"
results, created = [], {"k": [], "kt": [], "task": []}


def check(name, ok, detail=""):
    ok = bool(ok)
    results.append(ok)
    print("%s %s%s" % ("PASS" if ok else "FAIL", name, ("  -- " + str(detail)[:200]) if detail and not ok else ""))


def kb(*args, code=0):
    p = subprocess.run(KB + list(args), capture_output=True, text=True)
    if p.returncode != code:
        print("    kb %s -> exit %d (expected %d)\n    %s" % (" ".join(args), p.returncode, code, (p.stdout + p.stderr)[-400:]))
    return p


def kbj(*args, code=0):
    p = kb(*(list(args) + ["--json"]), code=code)
    try:
        return json.loads(p.stdout)
    except ValueError:
        return {"_raw": p.stdout + p.stderr, "_code": p.returncode}


def baseline():
    work = 0
    for table, field in (("tblbGSzWdR7KEtPVClg", "fldRMySX5jvdIUWIkGB"), ("tbliD8gcOTRk9RZ9SmR", "fldCw3cnpw8EWs09C1v"), (TASKS, TASK_REFER)):
        work += sum(len(r["fields"].get(field) or []) for r in T.get_records(table, projection=[field]))
    ents = T.get_records(K, projection=[TITLE, RELATED])
    return dict(entries=len(ents), types=len(T.get_records(KT, projection=[TT])), tasks=len(T.get_records(TASKS, projection=[TASK_TITLE])),
                related=sum(len(r["fields"].get(RELATED) or []) for r in ents), work_links=work)


def main():
    # 0. static checks
    pm = (HERE.parent.parent / "project-management" / "scripts" / "teable.py")
    if pm.is_file():
        mine = (SCRIPTS / "teable.py").read_text().split("\n", 1)[1]
        check("teable.py identical to project-management copy (below header)", mine == pm.read_text())
    cases = {"DB_PASSWORD=hunter2secret": True, "POSTGRES_PASSWORD: ${DB_PASS}": False, "password: changeme": False,
             "redis://u:s3cretpw@h:6379": True, "-----BEGIN OPENSSH PRIVATE KEY-----": True, "Use the password from the vault": False,
             "token: <YOUR_TOKEN>": False, "AKIAABCDEFGHIJKLMNOP": True, "docker run -e MYSQL_ROOT_PASSWORD=rootpass123 x": True,
             "Secret key: ICSFZy4LTe5KlTdmbbFTLIRZpaA6qVt": True, "Master key = abcdef123456": True,
             "RABBITMQ_DEFAULT_PASS: Rabb1tPw99": True, "CREATE USER u WITH PASSWORD 'Pg-Pass-2026';": True,
             "DB_PASS_FILE=/run/secrets/db": False, "bypass: enabled": False,
             "--certificate-authority=ca.crt": False, "creates two default API keys: [`Default Search`]": False}
    bad = [t for t, want in cases.items() if bool(safety.scan(t)) != want]
    check("safety.scan on %d cases" % len(cases), not bad, bad)
    bare = {"Xk9#mPq2vL": True, "hello world": False, "https://example.com/abc": False, "plainword": False, "/usr/local/bin": False}
    bad = [t for t, want in bare.items() if safety.looks_like_bare_secret(t) != want]
    check("safety.looks_like_bare_secret on %d cases" % len(bare), not bad, bad)
    red = safety.redact("a DB_PASSWORD=hunter2secret b redis://u:s3cretpw@h c ${DB_PASS}")
    check("safety.redact hides values and keeps the rest", "hunter2secret" not in red and "s3cretpw" not in red
          and red.startswith("a DB_PASSWORD=[secret] b") and "${DB_PASS}" in red, red)

    base = baseline()
    print("baseline:", base)

    # 1. query
    t0 = time.time()
    d = kbj("find", "k3s")
    check("find k3s returns entries in <=1 HTTP call", d.get("meta", {}).get("total", 0) >= 1 and d["meta"]["http_calls"] <= 1, d.get("meta"))
    check("find k3s under 2 s wall time", time.time() - t0 < 2.0, time.time() - t0)
    d = kbj("find", "kubernetes")
    check("alias: 'kubernetes' finds k3s entries", any("k3s" in (r["title"] or "").lower() for r in d.get("results", [])))
    d = kbj("find", "kubernetes", "node", "labels")
    check("plural term also matches the singular ('labels' finds 'K3S - Create new service')",
          any(r["title"] == "K3S - Create new service" for r in d.get("results", [])))
    d = kbj("for-work", "project:Knowledge Management Skill", "--suggest", "0")
    check("for-work resolves a project by title", d.get("id") == "recHXdCBQqv89De6Yti", d)
    kb("for-work", "project:zz no such project zz", code=3)
    check("unknown work title exits 3", True)
    d = kbj("find", "docker", "--type", "deployment")
    check("--type domain prefix limits to deployment types", d.get("results") and all((r["type"] or "").startswith("deployment") for r in d["results"]))
    d = kbj("find", "zzqqxxnotathing")
    check("find with no hits returns total 0", d.get("meta", {}).get("total") == 0)
    d = kbj("find", "credential", "--limit", "50")
    check("find includes credential-type entries (CR-1)", any("credential" in (r["type"] or "").lower() for r in d.get("results", [])))
    toc = kb("get", "K3S - Cheatsheet", "--toc").stdout
    check("get --toc ignores '#' lines inside code blocks", "Node Management" in toc and "Start k3s" not in toc)
    sec = kbj("get", "K3S - Cheatsheet", "--section", "Node Management", "--max-chars", "300")
    check("get --section + --max-chars", (sec.get("body") or "").startswith("## 3. Node Management") and sec.get("note"))
    kb("get", "New Server", code=3)
    check("get ambiguous title exits 3", True)
    check("types lists the tree", "deployment - k8s" in kb("types").stdout)
    secrets = {v for r in T.get_records(K, projection=[CTX]) for v in safety.values(r["fields"].get(CTX) or "") if len(v) >= 8 and not v.isalpha()}
    raw = "".join(kb("find", *q, "--any", "--limit", "200").stdout for q in (["s3", "backend", "tfstate"], ["password", "secret", "key"], ["docker", "compose", "env"]))
    leaked = [v[:2] + "…" for v in secrets if v in raw]
    check("find snippets show none of the %d secret values in the base" % len(secrets), not leaked, leaked)
    d = kbj("find", "sony")
    check("credential entries get no snippet in find", d.get("results") and all("credential entry" in r["snippet"] for r in d["results"]
                                                                                if "credential" in (r["type"] or "")))
    d = kbj("get", "Sony Game Account")
    check("get still returns credential bodies unredacted (CR-1)", len(d.get("body") or "") > 20 and "[secret]" not in d["body"])
    d = kbj("for-work", "project:Game Design Nebula-of-Cybernetics")
    check("for-work never suggests credential entries", not any("credential" in (x["type"] or "").lower() for x in d.get("suggested", [])), d.get("suggested"))
    d = kbj("capture", "--title", "Caddy - Zero-downtime Reload", "--type", "deployment - web server", "--body", "## When to use\nx")
    check("capture lists same-subject entries as similar", any(x["title"] == "Caddy - Cache issues" and x["same_subject"] for x in d.get("duplicates", [])), d.get("duplicates"))
    d = kbj("type-set", "deployment - caddy", "--parent-type", "deployment")
    check("type-set with no real change reports nothing to change", d.get("changes") == [] and d.get("written") is False, d)

    # 2. capture guards (dry runs write nothing)
    kb("capture", "--title", "K3S - Cheatsheet", "--type", "k3s - operation", "--body", "x", code=2)
    kb("capture", "--title", "[TEST] KM - Flow", "--type", "no such type zz", "--body", "x", code=2)
    d = kbj("capture", "--title", "[TEST] KM - Flow", "--type", "TEMP - Records", "--body", "## When to use\n- DB_PASSWORD=notreal123456")
    check("capture dry run flags the secret and writes nothing", d.get("written") is False and d.get("secrets") and baseline()["entries"] == base["entries"])

    # 3. real writes on [TEST] rows
    task = T.call("POST", "/api/table/%s/record" % TASKS, body={"fieldKeyType": "id", "records": [{"fields": {TASK_TITLE: "[TEST] KM flow task"}}]})["records"][0]["id"]
    created["task"].append(task)
    d = kbj("capture", "--title", "[TEST] KM - Flow", "--type", "TEMP - Records", "--body", "## When to use\nflow test",
            "--related", "rec9TTSDoktu59fT89i", "--refer", "task:" + task, "--yes")
    kid = d.get("id")
    if kid:
        created["k"].append(kid)
    check("capture --yes creates, verifies, refers", bool(kid) and d.get("refer", [{}])[0].get("result") == "linked", d)
    other = T.get_record(K, "rec9TTSDoktu59fT89i", [RELATED])["fields"].get(RELATED) or []
    check("related written on both sides", any(x["id"] == kid for x in other))
    d = kbj("trace", kid)
    check("trace finds the referring task", any(r["id"] == task for r in d.get("used_by", [])))
    d = kbj("for-work", "task:" + task, "--suggest", "0")
    check("for-work lists the linked entry", any(x["id"] == kid for x in d.get("linked", [])))
    kbj("append", kid, "--text", "- appended line", "--yes")
    body = T.get_record(K, kid, [CTX])["fields"].get(CTX) or ""
    check("append adds a dated ## Updates entry and keeps the rest", "## When to use" in body and "## Updates\n### " in body and "- appended line" in body)
    kbj("link", kid, "--unrelate", "rec9TTSDoktu59fT89i", "--yes")
    other = T.get_record(K, "rec9TTSDoktu59fT89i", [RELATED])["fields"].get(RELATED) or []
    check("unrelate removes both sides", not any(x["id"] == kid for x in other) and not T.get_record(K, kid, [RELATED])["fields"].get(RELATED))
    kb("link", kid, "--parent", kid, code=1)
    check("link refuses self-parent", True)
    kbj("archive", kid, "--yes")
    check("archive hides from find", kbj("find", "[TEST] KM - Flow").get("meta", {}).get("total") == 0
          and kbj("find", "[TEST] KM - Flow", "--all").get("meta", {}).get("total") == 1)
    kbj("archive", kid, "--restore", "--yes")
    check("restore", T.get_record(K, kid, [ACTIVE])["fields"].get(ACTIVE) is True)
    kbj("refer", kid, "--to", "task:" + task, "--remove", "--yes")
    check("refer --remove", not T.get_record(TASKS, task, [TASK_REFER])["fields"].get(TASK_REFER))

    # 4. taxonomy
    d = kbj("type-set", "[TEST] km parent", "--create", "--yes")
    tp = d.get("id")
    if tp:
        created["kt"].append(tp)
    d = kbj("capture", "--title", "[TEST] KM - Flow child", "--type", "[TEST] km child", "--new-type", "--parent-type", "[TEST] km parent",
            "--body", "## When to use\nchild", "--yes")
    if d.get("id"):
        created["k"].append(d["id"])
        created["kt"].append(d["type_id"])
    child_parent = T.get_record(KT, d.get("type_id"), [TPARENT])["fields"].get(TPARENT) if d.get("type_id") else None
    check("capture --new-type --parent-type creates a nested type", bool(child_parent) and child_parent["id"] == tp, d)
    kb("type-set", "[TEST] km parent", "--parent-type", "[TEST] km child", code=1)
    check("type-set refuses a cycle", True)
    d = kbj("doctor")
    check("doctor returns grouped findings incl. content risks (I)", {"A", "B", "E", "I"} <= {f["group"] for f in d.get("findings", [])}, d.get("summary"))
    raw = json.dumps(d, ensure_ascii=False)
    secrets = {v for r in T.get_records(K, projection=[CTX]) for v in safety.values(r["fields"].get(CTX) or "") if len(v) >= 8 and not v.isalpha()}
    leaked = [v[:2] + "…" for v in secrets if v in raw]
    check("doctor output contains none of the %d secret values in the base" % len(secrets), not leaked, leaked)
    plain = {hashlib.sha256(v.encode()).hexdigest()[:8] for v in secrets} | {hashlib.sha256(b"password").hexdigest()[:8]}
    shown = set(re.findall(r"(?:secret|stem) #([0-9a-f]{8})", kb("doctor").stdout))
    check("doctor hash ids are keyed (no plain sha256 prefixes)", shown and not (shown & plain), shown & plain)

    # 5. clean-up and baseline
    if created["k"]:
        T.delete_records(K, created["k"])
    if created["kt"]:
        T.delete_records(KT, created["kt"])
    if created["task"]:
        T.delete_records(TASKS, created["task"])
    for v in created.values():
        v.clear()
    left = T.get_records(K, {"conjunction": "and", "filterSet": [{"fieldId": TITLE, "operator": "contains", "value": "[TEST] KM"}]}, [TITLE])
    after = baseline()
    check("cleanup: no [TEST] KM entries left", not left, left)
    check("baseline restored", after == base, (base, after))
    print("\n%d/%d passed" % (sum(results), len(results)))
    sys.exit(0 if all(results) else 1)


if __name__ == "__main__":
    try:
        main()
    finally:
        # best-effort cleanup if a check crashed midway
        for table, key in ((K, "k"), (KT, "kt"), (TASKS, "task")):
            ids = [i for i in created[key] if i]
            if ids:
                try:
                    T.delete_records(table, ids)
                except SystemExit:
                    pass
