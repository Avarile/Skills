"""Person CRUD helpers over the Twenty CRM `/rest/people` endpoints.

Twenty stores several fields as nested objects (`name`, `emails`, `phones`,
`linkedinLink`, `xLink`). The functions here accept flat keyword arguments
and build/flatten that shape so callers never have to hand-assemble it.
"""
from __future__ import annotations

import client


def build_person_fields(
    *,
    first_name: str | None = None,
    last_name: str | None = None,
    email: str | None = None,
    job_title: str | None = None,
    city: str | None = None,
    company_id: str | None = None,
    phone_number: str | None = None,
    phone_country_code: str | None = None,
    phone_calling_code: str | None = None,
    linkedin_url: str | None = None,
    x_url: str | None = None,
) -> dict:
    """Builds a `/rest/people` request body from flat arguments, omitting
    anything not passed so this doubles as a partial-update payload."""
    fields: dict = {}
    if first_name is not None or last_name is not None:
        fields["name"] = {"firstName": first_name or "", "lastName": last_name or ""}
    if email is not None:
        fields["emails"] = {"primaryEmail": email, "additionalEmails": []}
    if job_title is not None:
        fields["jobTitle"] = job_title
    if city is not None:
        fields["city"] = city
    if company_id is not None:
        fields["companyId"] = company_id
    if phone_number is not None:
        fields["phones"] = {
            "primaryPhoneNumber": phone_number,
            "primaryPhoneCountryCode": phone_country_code or "",
            "primaryPhoneCallingCode": phone_calling_code or "",
        }
    if linkedin_url is not None:
        fields["linkedinLink"] = {"primaryLinkLabel": "", "primaryLinkUrl": linkedin_url, "secondaryLinks": []}
    if x_url is not None:
        fields["xLink"] = {"primaryLinkLabel": "", "primaryLinkUrl": x_url, "secondaryLinks": []}
    return fields


def normalize_person(record: dict) -> dict:
    """Flattens a raw Twenty person record into simple, flat fields."""
    name = record.get("name") or {}
    emails = record.get("emails") or {}
    phones = record.get("phones") or {}
    return {
        "id": record.get("id"),
        "first_name": name.get("firstName"),
        "last_name": name.get("lastName"),
        "email": emails.get("primaryEmail") or None,
        "job_title": record.get("jobTitle") or None,
        "city": record.get("city") or None,
        "company_id": record.get("companyId"),
        "phone_number": phones.get("primaryPhoneNumber") or None,
        "created_at": record.get("createdAt"),
        "updated_at": record.get("updatedAt"),
    }


def create_person(
    first_name: str,
    last_name: str,
    *,
    email: str | None = None,
    job_title: str | None = None,
    city: str | None = None,
    company_id: str | None = None,
    phone_number: str | None = None,
    phone_country_code: str | None = None,
    phone_calling_code: str | None = None,
) -> dict:
    fields = build_person_fields(
        first_name=first_name,
        last_name=last_name,
        email=email,
        job_title=job_title,
        city=city,
        company_id=company_id,
        phone_number=phone_number,
        phone_country_code=phone_country_code,
        phone_calling_code=phone_calling_code,
    )
    result = client.create_person(fields)
    return normalize_person(result["data"]["createPerson"])


def batch_create_people(people: list, *, upsert: bool = True) -> list:
    """`people` is a list of dicts using the same keyword names as
    `create_person` (e.g. `{"first_name": "Ada", "last_name": "Lovelace",
    "email": "ada@example.com"}`)."""
    payload = [
        build_person_fields(
            first_name=p.get("first_name"),
            last_name=p.get("last_name"),
            email=p.get("email"),
            job_title=p.get("job_title"),
            city=p.get("city"),
            company_id=p.get("company_id"),
            phone_number=p.get("phone_number"),
            phone_country_code=p.get("phone_country_code"),
            phone_calling_code=p.get("phone_calling_code"),
        )
        for p in people
    ]
    result = client.batch_create_people(payload, upsert=upsert)
    return [normalize_person(r) for r in result["data"]["createPeople"]]


def get_person(person_id: str) -> dict:
    result = client.get_person(person_id)
    return normalize_person(result["data"]["person"])


def update_person(
    person_id: str,
    *,
    first_name: str | None = None,
    last_name: str | None = None,
    email: str | None = None,
    job_title: str | None = None,
    city: str | None = None,
    company_id: str | None = None,
    phone_number: str | None = None,
    phone_country_code: str | None = None,
    phone_calling_code: str | None = None,
) -> dict:
    """Only the fields passed are sent -- everything else on the record is
    left untouched (Twenty's PATCH is a partial update)."""
    fields = build_person_fields(
        first_name=first_name,
        last_name=last_name,
        email=email,
        job_title=job_title,
        city=city,
        company_id=company_id,
        phone_number=phone_number,
        phone_country_code=phone_country_code,
        phone_calling_code=phone_calling_code,
    )
    result = client.update_person(person_id, fields)
    return normalize_person(result["data"]["updatePerson"])


def delete_person(person_id: str) -> dict:
    return client.delete_person(person_id)


def find_person_by_email(email: str) -> dict | None:
    page = client.list_people(filter=f"emails.primaryEmail[eq]:{email}", limit=1)
    records = page.get("data", {}).get("people", [])
    return normalize_person(records[0]) if records else None


def find_people_by_name(*, first_name: str | None = None, last_name: str | None = None, limit: int = 60) -> list:
    clauses = []
    if first_name:
        clauses.append(f"name.firstName[eq]:{first_name}")
    if last_name:
        clauses.append(f"name.lastName[eq]:{last_name}")
    filter_str = ",".join(clauses) if clauses else None
    page = client.list_people(filter=filter_str, limit=limit)
    return [normalize_person(r) for r in page.get("data", {}).get("people", [])]


def list_all_people() -> list:
    return [normalize_person(r) for r in client.iter_people()]
