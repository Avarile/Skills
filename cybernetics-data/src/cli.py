#!/usr/bin/env python3
"""Command-line entry point for cybernetics-data analysis, built for agent consumption.

Every subcommand prints one JSON document to stdout. On failure it prints a
plain-text message to stderr and exits non-zero.
"""
from __future__ import annotations

import argparse
import json
import sys

import client
import finance
import knowledge


def _print(data) -> None:
    json.dump(data, sys.stdout, indent=2, default=str)
    sys.stdout.write("\n")


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="cybernetics-data", description=__doc__)
    domain = parser.add_subparsers(dest="domain", required=True)

    fin = domain.add_parser("finance", help="finance_* table analysis").add_subparsers(
        dest="command", required=True
    )
    p = fin.add_parser("spending-by-category", help="total amount per category")
    p.add_argument("--type", default="Expense", dest="txn_type")
    p.add_argument("--month", default=None, help="YYYY-MM")
    fin.add_parser("monthly-cash-flow", help="income/expense/net per month")
    p = fin.add_parser("top-payees", help="biggest payees by spend")
    p.add_argument("--n", type=int, default=10)
    p.add_argument("--type", default="Expense", dest="txn_type")
    fin.add_parser("recurring", help="recurring transactions grouped by frequency")
    p = fin.add_parser("search", help="full-text search over transactions")
    p.add_argument("query")
    fin.add_parser("account-balances", help="balance + net activity per account")
    p = fin.add_parser("budget-variance", help="planned vs actual per budget line")
    p.add_argument("--month", default=None, help="YYYY-MM")

    know = domain.add_parser("knowledge", help="knowledge / knowledge_type analysis").add_subparsers(
        dest="command", required=True
    )
    p = know.add_parser("search", help="full-text search over knowledge entries")
    p.add_argument("query")
    know.add_parser("list-types", help="all knowledge_type entries")
    p = know.add_parser("by-type", help="knowledge entries of one type")
    p.add_argument("type_title")
    know.add_parser("tree", help="full knowledge hierarchy as nested JSON")

    return parser


def _dispatch_finance(args) -> object:
    if args.command == "spending-by-category":
        txns = finance.fetch_transactions()
        return finance.spending_by_category(txns, txn_type=args.txn_type, month=args.month)
    if args.command == "monthly-cash-flow":
        return finance.monthly_cash_flow(finance.fetch_transactions())
    if args.command == "top-payees":
        txns = finance.fetch_transactions()
        return finance.top_payees(txns, n=args.n, txn_type=args.txn_type)
    if args.command == "recurring":
        return finance.recurring_transactions(finance.fetch_transactions())
    if args.command == "search":
        return finance.search_transactions(args.query)
    if args.command == "account-balances":
        return finance.account_balances()
    if args.command == "budget-variance":
        return finance.budget_variance(month=args.month)
    raise AssertionError(f"unhandled finance command: {args.command}")


def _dispatch_knowledge(args) -> object:
    if args.command == "search":
        return knowledge.search_knowledge(args.query)
    if args.command == "list-types":
        return knowledge.list_knowledge_types()
    if args.command == "by-type":
        return knowledge.knowledge_by_type(args.type_title)
    if args.command == "tree":
        return knowledge.build_knowledge_tree()
    raise AssertionError(f"unhandled knowledge command: {args.command}")


def main(argv=None) -> int:
    args = _build_parser().parse_args(argv)
    try:
        if args.domain == "finance":
            _print(_dispatch_finance(args))
        else:
            _print(_dispatch_knowledge(args))
    except client.CyberneticsDataError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
