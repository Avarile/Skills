"""Offline tests for the knowledge skill. No network unless KB_LIVE=1.

    python3 .claude/skills/cybernetics-data-knowledge/tests/test_knowledge.py
"""
from __future__ import annotations

import json
import os
import sys
import unittest
from pathlib import Path

SRC = Path(__file__).resolve().parent.parent / "src"
sys.path.insert(0, str(SRC))

import client  # noqa: E402
import knowledge  # noqa: E402


def rec(record_id, **fields):
    return {"id": record_id, "fields": fields}


class TestDotenv(unittest.TestCase):
    def test_both_delimiters(self):
        parsed = client.parse_dotenv("A=1\nB: 2\n")
        self.assertEqual(parsed, {"A": "1", "B": "2"})

    def test_value_keeps_later_delimiters(self):
        # A base64 token ends in '=' padding and a URL contains ':'.
        parsed = client.parse_dotenv("TOKEN=abc+/def==\nURL: https://x.test/y\n")
        self.assertEqual(parsed["TOKEN"], "abc+/def==")
        self.assertEqual(parsed["URL"], "https://x.test/y")

    def test_comments_blanks_and_quotes(self):
        parsed = client.parse_dotenv("# note\n\nA='v'\nB=\"w\"\nnot a line\n")
        self.assertEqual(parsed, {"A": "v", "B": "w"})


class TestNormalize(unittest.TestCase):
    def test_full_record(self):
        entry = knowledge.normalize(rec(
            "rec1", title="T", context="C", is_active=True, id=7,
            knowledge_type={"id": "recT", "title": "ty"},
            knowledge_parent={"id": "recP", "title": "par"},
            knowledges=[{"id": "recC", "title": "kid"}],
            related_knowledge=[{"id": "recR", "title": "rel"}]))
        self.assertEqual(entry["record_id"], "rec1")
        self.assertEqual(entry["num"], 7)
        self.assertEqual(entry["type"]["title"], "ty")
        self.assertEqual(entry["parent"]["id"], "recP")
        self.assertEqual(entry["children"], [{"id": "recC", "title": "kid"}])
        self.assertEqual(entry["related"], [{"id": "recR", "title": "rel"}])

    def test_missing_links_are_none_not_crash(self):
        entry = knowledge.normalize(rec("rec1", title="T"))
        self.assertIsNone(entry["type"]["id"])
        self.assertIsNone(entry["parent"]["id"])
        self.assertEqual(entry["children"], [])
        self.assertEqual(entry["related"], [])

    def test_unchecked_checkbox_reads_false_not_none(self):
        # Teable stores an unchecked box as null; callers expect a real bool.
        self.assertFalse(knowledge.normalize(rec("rec1", is_active=None))["is_active"])
        self.assertFalse(knowledge.normalize(rec("rec1"))["is_active"])
        self.assertTrue(knowledge.normalize(rec("rec1", is_active=True))["is_active"])

    def test_type_record(self):
        entry = knowledge.normalize_type(rec(
            "recT", title="ty", credentials="c", id=3,
            parent_type={"id": "recP", "title": "p"},
            child_types=[{"id": "recC", "title": "c1"}],
            knowledges=[{"id": "a"}, {"id": "b"}]))
        self.assertEqual(entry["credentials"], "c")
        self.assertEqual(entry["parent_type"]["title"], "p")
        self.assertEqual(entry["knowledge_count"], 2)


class TestFilters(unittest.TestCase):
    def test_contains_filter_shape(self):
        self.assertEqual(
            client.contains_filter("title", "x"),
            {"conjunction": "and",
             "filterSet": [{"fieldId": "title", "operator": "contains", "value": "x"}]})

    def test_and_filter_drops_empties(self):
        cond = {"fieldId": "is_active", "operator": "is", "value": True}
        self.assertIsNone(client.and_filter())
        self.assertIsNone(client.and_filter(None))
        self.assertEqual(client.and_filter(cond, None)["filterSet"], [cond])

    def test_terse_extracts_message_and_field_list(self):
        envelope = json.dumps({
            "message": 'Field "nope" does not exist in this table',
            "data": {"details": {"availableFieldKeys": ["title", "context"]}}})
        terse = client._terse(envelope)
        self.assertIn("does not exist", terse)
        self.assertIn("title, context", terse)

    def test_terse_survives_non_json(self):
        self.assertEqual(client._terse("plain failure"), "plain failure")


class TestDecodeDeleted(unittest.TestCase):
    def test_field_ids_map_back_to_names(self):
        # DELETE responses key fields by ID regardless of fieldKeyType.
        raw = {"id": "rec1", "fields": {
            client.FIELD_IDS["knowledges"]["title"]: "gone",
            client.FIELD_IDS["knowledges"]["id"]: 42}}
        decoded = client.decode_deleted("knowledges", raw)
        self.assertEqual(decoded["fields"]["title"], "gone")
        self.assertEqual(decoded["fields"]["id"], 42)


class FakeBackend:
    """Stands in for the network so resolution and link logic can be tested."""

    def __init__(self, entries):
        self.entries = entries
        self.updates = []

    def iter_records(self, table, **kwargs):
        return iter(self.entries.get(table, []))

    def get_record(self, table, record_id):
        for record in self.entries.get(table, []):
            if record["id"] == record_id:
                return record
        raise client.KnowledgeError("not found")

    def update_record(self, table, record_id, fields):
        self.updates.append((table, record_id, fields))
        return rec(record_id, **fields)


class LinkTestCase(unittest.TestCase):
    def setUp(self):
        self.backend = FakeBackend({
            "knowledges": [
                rec("recAAAAAAAAAAAAAAAA", title="Alpha", id=1),
                rec("recBBBBBBBBBBBBBBBB", title="Beta", id=2,
                    related_knowledge=[{"id": "recAAAAAAAAAAAAAAAA", "title": "Alpha"}]),
                rec("recCCCCCCCCCCCCCCCC", title="Alpha copy", id=3),
            ],
            "knowledge_type": [rec("recTTTTTTTTTTTTTTTT", title="general", id=1)],
        })
        self._saved = (client.iter_records, client.get_record, client.update_record)
        client.iter_records = self.backend.iter_records
        client.get_record = self.backend.get_record
        client.update_record = self.backend.update_record

    def tearDown(self):
        client.iter_records, client.get_record, client.update_record = self._saved


class TestResolve(LinkTestCase):
    def test_by_record_id(self):
        self.assertEqual(knowledge.resolve("recAAAAAAAAAAAAAAAA")["title"], "Alpha")

    def test_by_autonumber_with_and_without_hash(self):
        self.assertEqual(knowledge.resolve("2")["title"], "Beta")
        self.assertEqual(knowledge.resolve("#2")["title"], "Beta")

    def test_missing_autonumber(self):
        with self.assertRaisesRegex(client.KnowledgeError, "number 99"):
            knowledge.resolve("99")

    def test_exact_title_wins_over_substring(self):
        # "Alpha" is also a substring of "Alpha copy"; the exact match decides.
        self.assertEqual(knowledge.resolve("Alpha")["record_id"], "recAAAAAAAAAAAAAAAA")

    def test_title_is_case_insensitive(self):
        self.assertEqual(knowledge.resolve("alpha")["record_id"], "recAAAAAAAAAAAAAAAA")

    def test_unique_substring(self):
        self.assertEqual(knowledge.resolve("copy")["record_id"], "recCCCCCCCCCCCCCCCC")

    def test_ambiguous_substring_lists_candidates(self):
        with self.assertRaises(client.KnowledgeError) as caught:
            knowledge.resolve("Alph")
        self.assertIn("matches 2 records", str(caught.exception))

    def test_no_match(self):
        with self.assertRaisesRegex(client.KnowledgeError, "No knowledges record"):
            knowledge.resolve("nothing here")

    def test_resolves_in_type_table(self):
        self.assertEqual(knowledge.resolve("general", "knowledge_type")["record_id"],
                         "recTTTTTTTTTTTTTTTT")


class TestBuildFields(LinkTestCase):
    def test_only_supplied_fields_are_sent(self):
        self.assertEqual(knowledge.build_fields(title="T"), {"title": "T"})

    def test_link_reference_resolves_to_id(self):
        fields = knowledge.build_fields(type_ref="general", parent_ref="Beta")
        self.assertEqual(fields["knowledge_type"], {"id": "recTTTTTTTTTTTTTTTT"})
        self.assertEqual(fields["knowledge_parent"], {"id": "recBBBBBBBBBBBBBBBB"})

    def test_empty_string_clears_a_link(self):
        self.assertIsNone(knowledge.build_fields(parent_ref="")["knowledge_parent"])

    def test_is_active_false_is_kept_not_dropped(self):
        self.assertEqual(knowledge.build_fields(is_active=False), {"is_active": False})

    def test_create_requires_a_title(self):
        with self.assertRaisesRegex(client.KnowledgeError, "title is required"):
            knowledge.create(context="body")


class TestRelated(LinkTestCase):
    def test_add_related_merges_instead_of_replacing(self):
        # An array link PATCH replaces the list, so existing members must survive.
        knowledge.add_related("Beta", ["Alpha copy"])
        _, _, fields = self.backend.updates[0]
        self.assertEqual([r["id"] for r in fields["related_knowledge"]],
                         ["recAAAAAAAAAAAAAAAA", "recCCCCCCCCCCCCCCCC"])

    def test_add_related_is_idempotent(self):
        knowledge.add_related("Beta", ["Alpha"])
        _, _, fields = self.backend.updates[0]
        self.assertEqual([r["id"] for r in fields["related_knowledge"]],
                         ["recAAAAAAAAAAAAAAAA"])

    def test_mutual_writes_the_other_side_too(self):
        # related_knowledge is one-directional; --mutual patches both records.
        knowledge.add_related("Alpha", ["Alpha copy"], mutual=True)
        touched = [record_id for _, record_id, _ in self.backend.updates]
        self.assertIn("recAAAAAAAAAAAAAAAA", touched)
        self.assertIn("recCCCCCCCCCCCCCCCC", touched)

    def test_remove_related(self):
        knowledge.remove_related("Beta", ["Alpha"])
        _, _, fields = self.backend.updates[0]
        self.assertEqual(fields["related_knowledge"], [])

    def test_set_parent_clear(self):
        knowledge.set_parent("Alpha", None)
        _, _, fields = self.backend.updates[0]
        self.assertIsNone(fields["knowledge_parent"])


class TestTree(LinkTestCase):
    def test_nests_children_and_sorts(self):
        self.backend.entries["knowledges"] = [
            rec("recP", title="Root", id=1),
            rec("recZ", title="Zeta", id=2, knowledge_parent={"id": "recP"}),
            rec("recA", title="Alpha", id=3, knowledge_parent={"id": "recP"}),
        ]
        forest = knowledge.tree()
        self.assertEqual(len(forest), 1)
        self.assertEqual([n["title"] for n in forest[0]["child_nodes"]],
                         ["Alpha", "Zeta"])

    def test_parent_outside_the_set_becomes_a_root(self):
        self.backend.entries["knowledges"] = [
            rec("recX", title="Stray", id=1, knowledge_parent={"id": "recGONE"}),
        ]
        self.assertEqual(len(knowledge.tree()), 1)

    def test_orphans_excludes_parents_and_children(self):
        self.backend.entries["knowledges"] = [
            rec("recP", title="Root", id=1, knowledges=[{"id": "recC"}]),
            rec("recC", title="Kid", id=2, knowledge_parent={"id": "recP"}),
            rec("recO", title="Lonely", id=3),
        ]
        self.assertEqual([e["title"] for e in knowledge.orphans()], ["Lonely"])


class TestSearch(LinkTestCase):
    """Search must filter server-side. The API's own `search` param returns the
    whole table even for a nonsense query, so it is never used."""

    def _captured(self, *args, **kwargs):
        captured = {}
        original = client.iter_records

        def spy(table, **kw):
            captured["table"] = table
            captured["filter"] = kw.get("filter")
            return original(table, **kw)

        client.iter_records = spy
        try:
            knowledge.search(*args, **kwargs)
        finally:
            client.iter_records = original
        return captured

    def test_builds_an_or_contains_filter_over_the_searchable_set(self):
        captured = self._captured("docker")
        self.assertEqual(captured["filter"]["conjunction"], "or")
        self.assertEqual([c["fieldId"] for c in captured["filter"]["filterSet"]],
                         client.SEARCHABLE["knowledges"])
        for condition in captured["filter"]["filterSet"]:
            self.assertEqual(condition["operator"], "contains")
            self.assertEqual(condition["value"], "docker")

    def test_field_narrows_to_one_condition(self):
        self.assertEqual(
            self._captured("docker", field="title")["filter"]["filterSet"],
            [{"fieldId": "title", "operator": "contains", "value": "docker"}])

    def test_uses_the_type_table_field_set(self):
        captured = self._captured("x", table="knowledge_type")
        self.assertEqual([c["fieldId"] for c in captured["filter"]["filterSet"]],
                         client.SEARCHABLE["knowledge_type"])

    def test_credentials_is_not_searched_by_default(self):
        # It holds real secrets and no normalizer returns it.
        self.assertNotIn("credentials", client.SEARCHABLE["knowledge_type"])

    def test_or_contains_filter_rejects_an_empty_field_list(self):
        # An empty filterSet would match everything.
        with self.assertRaises(client.KnowledgeError):
            client.or_contains_filter([], "x")

    def test_results_are_normalized(self):
        self.backend.entries["knowledges"] = [rec("rec1", title="Hit", id=1)]
        self.assertEqual([e["title"] for e in knowledge.search("Hit")], ["Hit"])


@unittest.skipUnless(os.environ.get("KB_LIVE") == "1",
                     "set KB_LIVE=1 to hit the live instance")
class TestLive(unittest.TestCase):
    """Round-trips a real record. Creates then deletes what it makes."""

    def test_create_read_update_delete(self):
        import importlib
        importlib.reload(client)
        importlib.reload(knowledge)
        entry = knowledge.create(title="KB selftest", context="tmp")
        try:
            fetched = knowledge.resolve(entry["record_id"])
            self.assertEqual(fetched["title"], "KB selftest")
            knowledge.update(entry["record_id"], title="KB selftest v2")
            self.assertEqual(knowledge.resolve(entry["record_id"])["title"],
                             "KB selftest v2")
        finally:
            knowledge.delete([entry["record_id"]])
        with self.assertRaises(client.KnowledgeError):
            client.get_record("knowledges", entry["record_id"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
