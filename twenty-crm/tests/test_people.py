import os
import sys
import unittest
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import people  # noqa: E402


def _raw_person(**overrides):
    record = {
        "id": "rec1",
        "name": {"firstName": "Ada", "lastName": "Lovelace"},
        "emails": {"primaryEmail": "ada@example.com", "additionalEmails": []},
        "jobTitle": "CTO",
        "city": "Melbourne",
        "companyId": None,
        "phones": {"primaryPhoneNumber": "", "primaryPhoneCountryCode": "", "primaryPhoneCallingCode": ""},
        "createdAt": "2026-09-07T10:38:38.500Z",
        "updatedAt": "2026-09-07T10:38:38.500Z",
    }
    record.update(overrides)
    return record


class BuildPersonFieldsTests(unittest.TestCase):
    def test_only_passed_fields_are_included(self):
        fields = people.build_person_fields(job_title="CTO")
        self.assertEqual(fields, {"jobTitle": "CTO"})

    def test_name_requires_either_part_present(self):
        fields = people.build_person_fields(first_name="Ada")
        self.assertEqual(fields["name"], {"firstName": "Ada", "lastName": ""})

    def test_email_builds_nested_shape(self):
        fields = people.build_person_fields(email="ada@example.com")
        self.assertEqual(fields["emails"], {"primaryEmail": "ada@example.com", "additionalEmails": []})

    def test_phone_builds_nested_shape_with_defaults(self):
        fields = people.build_person_fields(phone_number="412345678")
        self.assertEqual(
            fields["phones"],
            {"primaryPhoneNumber": "412345678", "primaryPhoneCountryCode": "", "primaryPhoneCallingCode": ""},
        )

    def test_no_arguments_builds_empty_payload(self):
        self.assertEqual(people.build_person_fields(), {})


class NormalizePersonTests(unittest.TestCase):
    def test_flattens_nested_fields(self):
        normalized = people.normalize_person(_raw_person())
        self.assertEqual(normalized["first_name"], "Ada")
        self.assertEqual(normalized["last_name"], "Lovelace")
        self.assertEqual(normalized["email"], "ada@example.com")
        self.assertEqual(normalized["job_title"], "CTO")

    def test_blank_email_and_phone_become_none(self):
        record = _raw_person(emails={"primaryEmail": "", "additionalEmails": []})
        normalized = people.normalize_person(record)
        self.assertIsNone(normalized["email"])
        self.assertIsNone(normalized["phone_number"])


class CreatePersonTests(unittest.TestCase):
    def test_sends_built_fields_and_normalizes_response(self):
        with mock.patch.object(
            people.client, "create_person", return_value={"data": {"createPerson": _raw_person()}}
        ) as create_person:
            result = people.create_person("Ada", "Lovelace", email="ada@example.com")
        sent_fields = create_person.call_args[0][0]
        self.assertEqual(sent_fields["name"], {"firstName": "Ada", "lastName": "Lovelace"})
        self.assertEqual(result["email"], "ada@example.com")


class UpdatePersonTests(unittest.TestCase):
    def test_partial_update_only_sends_passed_fields(self):
        with mock.patch.object(
            people.client, "update_person", return_value={"data": {"updatePerson": _raw_person(city="Sydney")}}
        ) as update_person:
            result = people.update_person("rec1", city="Sydney")
        update_person.assert_called_once_with("rec1", {"city": "Sydney"})
        self.assertEqual(result["city"], "Sydney")


class BatchCreatePeopleTests(unittest.TestCase):
    def test_builds_one_payload_entry_per_person(self):
        raw = [_raw_person(id="rec1"), _raw_person(id="rec2", name={"firstName": "Alan", "lastName": "Turing"})]
        with mock.patch.object(
            people.client, "batch_create_people", return_value={"data": {"createPeople": raw}}
        ) as batch_create:
            result = people.batch_create_people(
                [{"first_name": "Ada", "last_name": "Lovelace"}, {"first_name": "Alan", "last_name": "Turing"}]
            )
        sent_payload = batch_create.call_args[0][0]
        self.assertEqual(len(sent_payload), 2)
        self.assertEqual(batch_create.call_args.kwargs["upsert"], True)
        self.assertEqual(len(result), 2)


class FindPersonByEmailTests(unittest.TestCase):
    def test_returns_none_when_no_match(self):
        with mock.patch.object(people.client, "list_people", return_value={"data": {"people": []}}):
            self.assertIsNone(people.find_person_by_email("nobody@example.com"))

    def test_uses_eq_filter_and_returns_first_match(self):
        with mock.patch.object(
            people.client, "list_people", return_value={"data": {"people": [_raw_person()]}}
        ) as list_people:
            result = people.find_person_by_email("ada@example.com")
        list_people.assert_called_once_with(filter="emails.primaryEmail[eq]:ada@example.com", limit=1)
        self.assertEqual(result["email"], "ada@example.com")


class FindPeopleByNameTests(unittest.TestCase):
    def test_combines_first_and_last_name_clauses_with_comma(self):
        with mock.patch.object(people.client, "list_people", return_value={"data": {"people": []}}) as list_people:
            people.find_people_by_name(first_name="Ada", last_name="Lovelace")
        list_people.assert_called_once_with(
            filter="name.firstName[eq]:Ada,name.lastName[eq]:Lovelace", limit=60
        )

    def test_no_arguments_sends_no_filter(self):
        with mock.patch.object(people.client, "list_people", return_value={"data": {"people": []}}) as list_people:
            people.find_people_by_name()
        list_people.assert_called_once_with(filter=None, limit=60)


if __name__ == "__main__":
    unittest.main()
