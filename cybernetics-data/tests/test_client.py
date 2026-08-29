import json
import os
import sys
import unittest
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import client  # noqa: E402


class ParseDotenvTests(unittest.TestCase):
    def test_ignores_comments_and_blank_lines(self):
        text = "\n# comment\nFOO=bar\n\nBAZ=qux\n"
        self.assertEqual(client.parse_dotenv(text), {"FOO": "bar", "BAZ": "qux"})

    def test_strips_matching_quotes(self):
        text = 'A="hello world"\nB=\'single\'\nC=unquoted\n'
        self.assertEqual(
            client.parse_dotenv(text), {"A": "hello world", "B": "single", "C": "unquoted"}
        )

    def test_lines_without_equals_are_skipped(self):
        self.assertEqual(client.parse_dotenv("not-a-kv-line\nOK=1"), {"OK": "1"})

    def test_supports_colon_delimited_lines(self):
        self.assertEqual(client.parse_dotenv("FOO: bar\n"), {"FOO": "bar"})

    def test_embedded_equals_in_value_does_not_break_the_key(self):
        # Regression: base64-padded tokens can contain '=' well after the
        # real key/value delimiter -- the delimiter must bind to the first
        # match right after the key, not the first '=' anywhere in the line.
        text = "TOKEN: cybernetics_abc123+def==\nOTHER=val=with=equals"
        self.assertEqual(
            client.parse_dotenv(text),
            {"TOKEN": "cybernetics_abc123+def==", "OTHER": "val=with=equals"},
        )


class GetConfigTests(unittest.TestCase):
    def test_env_var_wins_and_defaults_base_url(self):
        with mock.patch.object(client, "_load_dotenv", return_value={}):
            with mock.patch.dict(os.environ, {"CYBERNETICS_DATA_API_TOKEN": "tok123"}, clear=False):
                config = client.get_config()
        self.assertEqual(config["token"], "tok123")
        self.assertEqual(config["base_url"], client.DEFAULT_BASE_URL)

    def test_falls_back_through_token_candidates(self):
        with mock.patch.object(client, "_load_dotenv", return_value={"API_TOKEN": "fallback-tok"}):
            with mock.patch.dict(os.environ, {}, clear=True):
                config = client.get_config()
        self.assertEqual(config["token"], "fallback-tok")

    def test_raises_when_no_token_found_anywhere(self):
        with mock.patch.object(client, "_load_dotenv", return_value={}):
            with mock.patch.dict(os.environ, {}, clear=True):
                with self.assertRaises(client.CyberneticsDataError):
                    client.get_config()

    def test_base_url_trailing_slash_is_stripped(self):
        with mock.patch.object(client, "_load_dotenv", return_value={}):
            env = {"CYBERNETICS_DATA_API_TOKEN": "t", "CYBERNETICS_DATA_BASE_URL": "https://x.test/"}
            with mock.patch.dict(os.environ, env, clear=False):
                config = client.get_config()
        self.assertEqual(config["base_url"], "https://x.test")


def _fake_response(payload):
    body = json.dumps(payload).encode("utf-8")
    response = mock.MagicMock()
    response.read.return_value = body
    response.__enter__.return_value = response
    response.__exit__.return_value = False
    return response


class RequestTests(unittest.TestCase):
    def setUp(self):
        patcher = mock.patch.object(
            client, "get_config", return_value={"base_url": "https://x.test", "token": "secret"}
        )
        self.addCleanup(patcher.stop)
        patcher.start()

    def test_builds_url_with_query_and_auth_header(self):
        with mock.patch("client.urllib.request.urlopen", return_value=_fake_response({"ok": True})) as urlopen:
            result = client.request("GET", "/api/table/tbl1/record", params={"take": 10, "skip": None})
        self.assertEqual(result, {"ok": True})
        sent_request = urlopen.call_args[0][0]
        self.assertEqual(sent_request.full_url, "https://x.test/api/table/tbl1/record?take=10")
        self.assertEqual(sent_request.get_header("Authorization"), "Bearer secret")

    def test_http_error_raises_cybernetics_data_error(self):
        import urllib.error

        err = urllib.error.HTTPError("url", 404, "Not Found", {}, None)
        err.read = lambda: b"not found detail"
        with mock.patch("client.urllib.request.urlopen", side_effect=err):
            with self.assertRaises(client.CyberneticsDataError) as ctx:
                client.request("GET", "/api/table/tbl1/record")
        self.assertIn("404", str(ctx.exception))


class IterRecordsTests(unittest.TestCase):
    def test_paginates_until_short_page(self):
        pages = [
            {"records": [{"id": "r1"}, {"id": "r2"}]},
            {"records": [{"id": "r3"}]},
        ]
        with mock.patch.object(client, "list_records", side_effect=pages) as list_records:
            result = list(client.iter_records("tbl1", take=2))
        self.assertEqual([r["id"] for r in result], ["r1", "r2", "r3"])
        self.assertEqual(list_records.call_count, 2)
        self.assertEqual(list_records.call_args_list[1].kwargs["skip"], 2)

    def test_stops_immediately_on_empty_first_page(self):
        with mock.patch.object(client, "list_records", return_value={"records": []}):
            self.assertEqual(list(client.iter_records("tbl1")), [])


if __name__ == "__main__":
    unittest.main()
