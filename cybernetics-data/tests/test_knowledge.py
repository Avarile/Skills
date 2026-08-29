import os
import sys
import unittest
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import knowledge  # noqa: E402


def _rec(rec_id, title, parent=None, ktype=None):
    return {
        "id": rec_id,
        "fields": {
            "title": title,
            "context": f"context for {title}",
            "is_active": True,
            "knowledge_parent": parent,
            "knowledge_type": ktype,
            "knowledges": [],
            "related_knowledge": [],
        },
    }


class NormalizeKnowledgeTests(unittest.TestCase):
    def test_pulls_parent_id_and_title(self):
        record = _rec("rec1", "Child", parent={"id": "rec0", "title": "Parent"})
        normalized = knowledge._normalize_knowledge(record)
        self.assertEqual(normalized["parent_id"], "rec0")
        self.assertEqual(normalized["parent_title"], "Parent")

    def test_no_parent_is_none(self):
        normalized = knowledge._normalize_knowledge(_rec("rec1", "Root"))
        self.assertIsNone(normalized["parent_id"])


class KnowledgeByTypeTests(unittest.TestCase):
    def test_filters_on_knowledge_type_title(self):
        records = [
            _rec("r1", "A", ktype={"title": "deployment"}),
            _rec("r2", "B", ktype={"title": "runbook"}),
        ]
        with mock.patch("knowledge.client.iter_records", return_value=records):
            result = knowledge.knowledge_by_type("deployment")
        self.assertEqual([r["title"] for r in result], ["A"])


class BuildKnowledgeTreeTests(unittest.TestCase):
    def test_nests_children_under_parents_and_roots_have_no_parent(self):
        records = [
            _rec("root", "Root"),
            _rec("child", "Child", parent={"id": "root", "title": "Root"}),
            _rec("grandchild", "Grandchild", parent={"id": "child", "title": "Child"}),
        ]
        with mock.patch("knowledge.client.iter_records", return_value=records):
            tree = knowledge.build_knowledge_tree()
        self.assertEqual(len(tree), 1)
        root = tree[0]
        self.assertEqual(root["title"], "Root")
        self.assertEqual(len(root["child_nodes"]), 1)
        self.assertEqual(root["child_nodes"][0]["title"], "Child")
        self.assertEqual(root["child_nodes"][0]["child_nodes"][0]["title"], "Grandchild")

    def test_dangling_parent_reference_becomes_a_root(self):
        records = [_rec("orphan", "Orphan", parent={"id": "missing", "title": "Ghost"})]
        with mock.patch("knowledge.client.iter_records", return_value=records):
            tree = knowledge.build_knowledge_tree()
        self.assertEqual(len(tree), 1)
        self.assertEqual(tree[0]["title"], "Orphan")


if __name__ == "__main__":
    unittest.main()
