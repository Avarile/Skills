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

    def test_supports_colon_delimited_lines(self):
        self.assertEqual(client.parse_dotenv("FOO: bar\n"), {"FOO": "bar"})

    def test_embedded_dots_and_equals_in_value_does_not_break_the_key(self):
        # Regression: JWT API tokens contain '.' and base64 padding '=' well
        # after the real key/value delimiter -- the delimiter must bind to
        # the first match right after the key, not scan the whole line.
        text = "TWENTY_CRM_APITOKEN: eyJhbGciOiJIUzI1NiJ9.eyJzdWIi.sig==\nOTHER=val=with=equals"
        self.assertEqual(
            client.parse_dotenv(text),
            {
                "TWENTY_CRM_APITOKEN": "eyJhbGciOiJIUzI1NiJ9.eyJzdWIi.sig==",
                "OTHER": "val=with=equals",
            },
        )


class GetConfigTests(unittest.TestCase):
    def test_env_var_wins_and_defaults_base_url(self):
        with mock.patch.object(client, "_load_dotenv", return_value={}):
            with mock.patch.dict(os.environ, {"TWENTY_API_KEY": "tok123"}, clear=False):
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
                with self.assertRaises(client.TwentyCrmError):
                    client.get_config()

    def test_base_url_trailing_slash_is_stripped(self):
        with mock.patch.object(client, "_load_dotenv", return_value={}):
            env = {"TWENTY_API_KEY": "t", "TWENTY_CRM_URL": "https://x.test/"}
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
            result = client.request("GET", "/rest/people", params={"limit": 10, "starting_after": None})
        self.assertEqual(result, {"ok": True})
        sent_request = urlopen.call_args[0][0]
        self.assertEqual(sent_request.full_url, "https://x.test/rest/people?limit=10")
        self.assertEqual(sent_request.get_header("Authorization"), "Bearer secret")

    def test_sends_json_body_on_write(self):
        with mock.patch("client.urllib.request.urlopen", return_value=_fake_response({"ok": True})) as urlopen:
            client.request("POST", "/rest/people", body={"jobTitle": "CTO"})
        sent_request = urlopen.call_args[0][0]
        self.assertEqual(json.loads(sent_request.data), {"jobTitle": "CTO"})
        self.assertEqual(sent_request.get_header("Content-type"), "application/json")

    def test_http_error_raises_twenty_crm_error(self):
        import urllib.error

        err = urllib.error.HTTPError("url", 404, "Not Found", {}, None)
        err.read = lambda: b"not found detail"
        with mock.patch("client.urllib.request.urlopen", side_effect=err):
            with self.assertRaises(client.TwentyCrmError) as ctx:
                client.request("GET", "/rest/people/bad-id")
        self.assertIn("404", str(ctx.exception))


class IterPeopleTests(unittest.TestCase):
    def test_paginates_via_cursor_until_has_next_page_is_false(self):
        pages = [
            {
                "data": {"people": [{"id": "p1"}, {"id": "p2"}]},
                "pageInfo": {"hasNextPage": True, "endCursor": "cursor1"},
            },
            {
                "data": {"people": [{"id": "p3"}]},
                "pageInfo": {"hasNextPage": False, "endCursor": "cursor2"},
            },
        ]
        with mock.patch.object(client, "list_people", side_effect=pages) as list_people:
            result = list(client.iter_people(page_size=2))
        self.assertEqual([r["id"] for r in result], ["p1", "p2", "p3"])
        self.assertEqual(list_people.call_count, 2)
        self.assertEqual(list_people.call_args_list[1].kwargs["starting_after"], "cursor1")

    def test_stops_immediately_on_empty_first_page(self):
        with mock.patch.object(
            client, "list_people", return_value={"data": {"people": []}, "pageInfo": {"hasNextPage": False}}
        ):
            self.assertEqual(list(client.iter_people()), [])


if __name__ == "__main__":
    unittest.main()
