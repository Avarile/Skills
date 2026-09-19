"""Knowledge-base management: resolve, read, create, update, link, delete.

Relationship semantics verified live (see references/api-behavior.md):
  * `knowledge_parent` (manyOne) and `knowledges` (oneMany) are the two sides
    of ONE self-referencing relationship. Writing either updates the other.
  * Writing `knowledges` REPLACES the whole child set -- children left out are
    orphaned. Prefer setting the child's `knowledge_parent`.
  * `related_knowledge` (manyMany) is one-directional: linking A->B does not
    make B point back at A. Write both sides for a mutual link.
  * Reverse sides of a link take ~1s to appear. A read straight after a write
    can still show the old value.
"""
from __future__ import annotations

import client

REC_PREFIX = "rec"


def _ref_id(ref):
    return ref.get("id") if isinstance(ref, dict) else None


def _ref_title(ref):
    return ref.get("title") if isinstance(ref, dict) else None


def normalize(record: dict) -> dict:
    """Flatten a knowledges record into a stable shape."""
    f = record.get("fields", {})
    return {
        "record_id": record.get("id"),
        "num": f.get("id"),
        "title": f.get("title"),
        "context": f.get("context"),
        "is_active": bool(f.get("is_active")),
        "created_at": f.get("created_at"),
        "updated_at": f.get("updated_at"),
        "deleted_at": f.get("deleted_at"),
        "type": {"id": _ref_id(f.get("knowledge_type")),
                 "title": _ref_title(f.get("knowledge_type"))},
        "parent": {"id": _ref_id(f.get("knowledge_parent")),
                   "title": _ref_title(f.get("knowledge_parent"))},
        "children": [{"id": _ref_id(c), "title": _ref_title(c)}
                     for c in (f.get("knowledges") or [])],
        "related": [{"id": _ref_id(r), "title": _ref_title(r)}
                    for r in (f.get("related_knowledge") or [])],
    }


def normalize_type(record: dict) -> dict:
    f = record.get("fields", {})
    return {
        "record_id": record.get("id"),
        "num": f.get("id"),
        "title": f.get("title"),
        "context": f.get("context"),
        "is_active": bool(f.get("is_active")),
        "credentials": f.get("credentials"),
        "parent_type": {"id": _ref_id(f.get("parent_type")),
                        "title": _ref_title(f.get("parent_type"))},
        "child_types": [{"id": _ref_id(c), "title": _ref_title(c)}
                        for c in (f.get("child_types") or [])],
        "knowledge_count": len(f.get("knowledges") or []),
    }


# --- reading ---------------------------------------------------------------

def fetch_all(table: str = "knowledges", *, filter: dict | None = None,
              order_by: list | None = None) -> list:
    records = client.iter_records(table, filter=filter, order_by=order_by)
    shape = normalize if table == "knowledges" else normalize_type
    return [shape(r) for r in records]


def search(query: str, *, field: str | None = None, table: str = "knowledges") -> list:
    """Substring search, server-side and case-insensitive.

    One OR-of-`contains` request across `client.SEARCHABLE[table]`, or a single
    field when `field` is given. The API's own `search` param is not used: it
    returns every record even for a nonsense query.
    """
    fields = [field] if field else client.SEARCHABLE[table]
    return fetch_all(table, filter=client.or_contains_filter(fields, query))


def by_type(type_title: str) -> list:
    """Knowledge entries whose knowledge_type matches, case-insensitively."""
    wanted = type_title.casefold()
    return [e for e in fetch_all("knowledges")
            if (e["type"]["title"] or "").casefold() == wanted]


def resolve(ref: str, table: str = "knowledges") -> dict:
    """Turn a user-supplied reference into one record.

    Accepts a record id (`rec...`), an autonumber (`136` or `#136`), or a
    title (exact case-insensitive match preferred, else a unique substring).
    Raises when nothing matches or a title is ambiguous.
    """
    ref = str(ref).strip()
    shape = normalize if table == "knowledges" else normalize_type
    if ref.startswith(REC_PREFIX) and len(ref) > 10:
        return shape(client.get_record(table, ref))

    lookup = ref[1:] if ref.startswith("#") else ref
    if lookup.isdigit():
        wanted = int(lookup)
        for entry in fetch_all(table):
            if entry["num"] == wanted:
                return entry
        raise client.KnowledgeError(f"No {table} record with number {wanted}.")

    entries = fetch_all(table)
    needle = ref.casefold()
    exact = [e for e in entries if (e["title"] or "").casefold() == needle]
    if len(exact) == 1:
        return exact[0]
    if len(exact) > 1:
        raise client.KnowledgeError(
            f"{len(exact)} records share the title {ref!r}: "
            + ", ".join(f"{e['record_id']} (#{e['num']})" for e in exact[:8])
            + ". Use a record id or number.")
    partial = [e for e in entries if needle in (e["title"] or "").casefold()]
    if len(partial) == 1:
        return partial[0]
    if not partial:
        raise client.KnowledgeError(f"No {table} record matches {ref!r}.")
    raise client.KnowledgeError(
        f"{ref!r} matches {len(partial)} records: "
        + ", ".join(f"#{e['num']} {e['title']!r}" for e in partial[:8])
        + ". Be more specific or use a record id.")


# --- writing ---------------------------------------------------------------

def _link_one(ref: str | None, table: str):
    """A manyOne link value. Explicit empty string clears it."""
    if ref is None:
        return None
    if ref == "":
        return None
    return {"id": resolve(ref, table)["record_id"]}


def _link_many(refs, table: str):
    return [{"id": resolve(r, table)["record_id"]} for r in refs]


def build_fields(*, title=None, context=None, is_active=None, deleted_at=None,
                 type_ref=None, parent_ref=None, related_refs=None,
                 children_refs=None) -> dict:
    """Assemble a writable `fields` payload, resolving link references to ids.

    Link fields require `{"id": "rec..."}` -- a `{"title": ...}` alone is
    rejected by the API, so every reference is resolved first.
    """
    fields = {}
    if title is not None:
        fields["title"] = title
    if context is not None:
        fields["context"] = context
    if is_active is not None:
        fields["is_active"] = bool(is_active)
    if deleted_at is not None:
        fields["deleted_at"] = deleted_at or None
    if type_ref is not None:
        fields["knowledge_type"] = _link_one(type_ref, "knowledge_type")
    if parent_ref is not None:
        fields["knowledge_parent"] = _link_one(parent_ref, "knowledges")
    if related_refs is not None:
        fields["related_knowledge"] = _link_many(related_refs, "knowledges")
    if children_refs is not None:
        fields["knowledges"] = _link_many(children_refs, "knowledges")
    return fields


def create(**kwargs) -> dict:
    """Create one knowledge entry. `title` is not enforced by the API, but a
    record without one is unfindable by name, so require it here."""
    fields = build_fields(**kwargs)
    if not fields.get("title"):
        raise client.KnowledgeError("A title is required to create an entry.")
    created = client.create_records("knowledges", [fields])
    if not created:
        raise client.KnowledgeError("Create returned no record.")
    return normalize(created[0])


def update(ref: str, **kwargs) -> dict:
    fields = build_fields(**kwargs)
    if not fields:
        raise client.KnowledgeError("Nothing to update -- pass at least one field.")
    target = resolve(ref)
    return normalize(client.update_record("knowledges", target["record_id"], fields))


def add_related(ref: str, others: list, *, mutual: bool = False) -> dict:
    """Append to `related_knowledge` instead of replacing it.

    A bare PATCH of an array link replaces the whole list, so the current
    members are read first and merged.
    """
    target = resolve(ref)
    existing = [r["id"] for r in target["related"] if r["id"]]
    additions = [resolve(o)["record_id"] for o in others]
    merged = list(dict.fromkeys(existing + additions))
    result = client.update_record("knowledges", target["record_id"],
                                 {"related_knowledge": [{"id": i} for i in merged]})
    if mutual:
        # related_knowledge is one-directional; write the other side too.
        for other in additions:
            back = normalize(client.get_record("knowledges", other))
            ids = list(dict.fromkeys([r["id"] for r in back["related"] if r["id"]]
                                     + [target["record_id"]]))
            client.update_record("knowledges", other,
                                 {"related_knowledge": [{"id": i} for i in ids]})
    return normalize(result)


def remove_related(ref: str, others: list) -> dict:
    target = resolve(ref)
    drop = {resolve(o)["record_id"] for o in others}
    kept = [{"id": r["id"]} for r in target["related"] if r["id"] and r["id"] not in drop]
    return normalize(client.update_record("knowledges", target["record_id"],
                                          {"related_knowledge": kept}))


def set_parent(ref: str, parent_ref: str | None) -> dict:
    """Reparent one entry. Safer than writing the parent's `knowledges`, which
    replaces its entire child set."""
    target = resolve(ref)
    value = {"id": resolve(parent_ref)["record_id"]} if parent_ref else None
    return normalize(client.update_record("knowledges", target["record_id"],
                                          {"knowledge_parent": value}))


def delete(refs: list, table: str = "knowledges") -> list:
    """Delete one or many records. Resolves first so a bad reference fails
    before anything is removed."""
    targets = [resolve(r, table) for r in refs]
    ids = [t["record_id"] for t in targets]
    if len(ids) == 1:
        raw = [client.delete_record(table, ids[0])]
    else:
        raw = client.delete_records(table, ids)
    return [client.decode_deleted(table, r) for r in raw]


# --- structure -------------------------------------------------------------

def tree(type_title: str | None = None) -> list:
    """Forest of entries nested under `child_nodes`, rooted where the parent is
    absent or outside the selected set."""
    entries = by_type(type_title) if type_title else fetch_all("knowledges")
    nodes = {e["record_id"]: {**e, "child_nodes": []} for e in entries}
    roots = []
    for node in nodes.values():
        parent_id = node["parent"]["id"]
        if parent_id and parent_id in nodes:
            nodes[parent_id]["child_nodes"].append(node)
        else:
            roots.append(node)
    for node in nodes.values():
        node["child_nodes"].sort(key=lambda n: (n["title"] or "").casefold())
    roots.sort(key=lambda n: (n["title"] or "").casefold())
    return roots


def orphans() -> list:
    """Entries with no parent and no children -- unfiled knowledge."""
    return [e for e in fetch_all("knowledges")
            if not e["parent"]["id"] and not e["children"]]


def stats() -> dict:
    entries = fetch_all("knowledges")
    types = fetch_all("knowledge_type")
    by_type_count = {}
    for entry in entries:
        key = entry["type"]["title"] or "(untyped)"
        by_type_count[key] = by_type_count.get(key, 0) + 1
    return {
        "entries": len(entries),
        "active": sum(1 for e in entries if e["is_active"]),
        "inactive": sum(1 for e in entries if not e["is_active"]),
        "soft_deleted": sum(1 for e in entries if e["deleted_at"]),
        "untitled": sum(1 for e in entries if not e["title"]),
        "orphans": sum(1 for e in entries
                       if not e["parent"]["id"] and not e["children"]),
        "types": len(types),
        "by_type": dict(sorted(by_type_count.items(),
                               key=lambda kv: -kv[1])),
    }
