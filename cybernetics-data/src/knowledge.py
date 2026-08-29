"""Knowledge-base analysis helpers over the knowledges / knowledge_type tables."""
from __future__ import annotations

import client
import schema


def _title(ref):
    return ref.get("title") if isinstance(ref, dict) else None


def _normalize_knowledge(record: dict) -> dict:
    f = record.get("fields", {})
    parent = f.get("knowledge_parent")
    return {
        "id": record.get("id"),
        "title": f.get("title"),
        "context": f.get("context"),
        "is_active": f.get("is_active", False),
        "knowledge_type": _title(f.get("knowledge_type")),
        "parent_id": parent.get("id") if isinstance(parent, dict) else None,
        "parent_title": _title(parent),
        "children": [_title(c) for c in (f.get("knowledges") or [])],
        "related": [_title(r) for r in (f.get("related_knowledge") or [])],
    }


def fetch_knowledge(*, search: str | None = None, take: int = 1000) -> list:
    table_id = schema.TABLES["knowledges"]
    records = client.iter_records(table_id, search=search, take=take)
    return [_normalize_knowledge(r) for r in records]


def search_knowledge(query: str) -> list:
    return fetch_knowledge(search=query)


def list_knowledge_types() -> list:
    table_id = schema.TABLES["knowledge_type"]
    out = []
    for r in client.iter_records(table_id):
        f = r.get("fields", {})
        out.append({
            "id": r.get("id"),
            "title": f.get("title"),
            "context": f.get("context"),
            "is_active": f.get("is_active", False),
            "parent_type": _title(f.get("parent_type")),
        })
    return out


def knowledge_by_type(type_title: str) -> list:
    return [k for k in fetch_knowledge() if k["knowledge_type"] == type_title]


def build_knowledge_tree() -> list:
    """Forest of knowledge entries nested under `child_nodes`, rooted at
    entries with no (or an unresolved) knowledge_parent."""
    entries = fetch_knowledge()
    by_id = {e["id"]: {**e, "child_nodes": []} for e in entries}
    roots = []
    for entry in by_id.values():
        parent_id = entry["parent_id"]
        if parent_id and parent_id in by_id:
            by_id[parent_id]["child_nodes"].append(entry)
        else:
            roots.append(entry)
    return roots
