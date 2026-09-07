#!/usr/bin/env python3
"""Command-line entry point for twenty-crm Person management, built for agent consumption.

Every subcommand prints one JSON document to stdout. On failure it prints a
plain-text message to stderr and exits non-zero.
"""
from __future__ import annotations

import argparse
import json
import sys

import client
import people


def _print(data) -> None:
    json.dump(data, sys.stdout, indent=2, default=str)
    sys.stdout.write("\n")


def _add_person_fields_args(parser, *, required_name: bool) -> None:
    parser.add_argument("--first-name", required=required_name)
    parser.add_argument("--last-name", required=required_name)
    parser.add_argument("--email", default=None)
    parser.add_argument("--job-title", default=None)
    parser.add_argument("--city", default=None)
    parser.add_argument("--company-id", default=None)
    parser.add_argument("--phone-number", default=None)
    parser.add_argument("--phone-country-code", default=None)
    parser.add_argument("--phone-calling-code", default=None)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="twenty-crm", description=__doc__)
    command = parser.add_subparsers(dest="command", required=True)

    p = command.add_parser("create", help="create one person")
    _add_person_fields_args(p, required_name=True)

    p = command.add_parser("update", help="partial update of one person by id")
    p.add_argument("person_id")
    _add_person_fields_args(p, required_name=False)

    p = command.add_parser("get", help="fetch one person by id")
    p.add_argument("person_id")

    p = command.add_parser("delete", help="delete one person by id")
    p.add_argument("person_id")

    p = command.add_parser("find-by-email", help="find one person by exact email match")
    p.add_argument("email")

    p = command.add_parser("find-by-name", help="find people by first and/or last name")
    p.add_argument("--first-name", default=None)
    p.add_argument("--last-name", default=None)

    command.add_parser("list", help="list every person (paginates automatically)")

    return parser


def _person_kwargs(args) -> dict:
    return {
        "email": args.email,
        "job_title": args.job_title,
        "city": args.city,
        "company_id": args.company_id,
        "phone_number": args.phone_number,
        "phone_country_code": args.phone_country_code,
        "phone_calling_code": args.phone_calling_code,
    }


def _dispatch(args) -> object:
    if args.command == "create":
        return people.create_person(args.first_name, args.last_name, **_person_kwargs(args))
    if args.command == "update":
        return people.update_person(
            args.person_id, first_name=args.first_name, last_name=args.last_name, **_person_kwargs(args)
        )
    if args.command == "get":
        return people.get_person(args.person_id)
    if args.command == "delete":
        return people.delete_person(args.person_id)
    if args.command == "find-by-email":
        return people.find_person_by_email(args.email)
    if args.command == "find-by-name":
        return people.find_people_by_name(first_name=args.first_name, last_name=args.last_name)
    if args.command == "list":
        return people.list_all_people()
    raise AssertionError(f"unhandled command: {args.command}")


def main(argv=None) -> int:
    args = _build_parser().parse_args(argv)
    try:
        _print(_dispatch(args))
    except client.TwentyCrmError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
