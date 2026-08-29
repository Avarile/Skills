"""Finance analysis helpers over the finance_* tables in cybernetics-data."""
from __future__ import annotations

from collections import defaultdict

import client
import schema


def _title(ref):
    """Pull the display title out of a Teable link-field reference (or None)."""
    return ref.get("title") if isinstance(ref, dict) else None


def _month_key(date_str):
    """'2026-08-29T00:57:40.819Z' -> '2026-08'."""
    return date_str[:7] if date_str else None


def _normalize_transaction(record: dict) -> dict:
    f = record.get("fields", {})
    return {
        "id": record.get("id"),
        "description": f.get("Description"),
        "date": f.get("Date"),
        "type": f.get("Type"),
        "amount": f.get("Amount") or 0,
        "signed_amount": f.get("Signed Amount"),
        "recurring": f.get("Recurring", False),
        "recurring_frequency": f.get("Recurring Frequency"),
        "account": _title(f.get("Account")),
        "transfer_account": _title(f.get("Transfer Account")),
        "category": _title(f.get("Category")),
        "payee": _title(f.get("Payee")),
        "tags": [_title(t) for t in (f.get("Tags") or [])],
        "budget": _title(f.get("Budget")),
        "scope": f.get("Scope"),
        "notes": f.get("Notes"),
    }


def fetch_transactions(*, search: str | None = None, take: int = 1000) -> list:
    table_id = schema.TABLES["finance_transactions"]
    records = client.iter_records(table_id, search=search, take=take)
    return [_normalize_transaction(r) for r in records]


def search_transactions(query: str) -> list:
    return fetch_transactions(search=query)


def spending_by_category(transactions: list, *, txn_type: str = "Expense", month: str | None = None) -> dict:
    """Total amount per category, largest first. `month` is a 'YYYY-MM' filter."""
    totals: dict = defaultdict(float)
    for t in transactions:
        if t["type"] != txn_type:
            continue
        if month and _month_key(t["date"]) != month:
            continue
        totals[t["category"] or "(Uncategorized)"] += t["amount"]
    return dict(sorted(totals.items(), key=lambda kv: kv[1], reverse=True))


def monthly_cash_flow(transactions: list) -> dict:
    """{'YYYY-MM': {income, expense, transfers, net}} across all months present.

    `net` sums each transaction's own Signed Amount (Income positive,
    Expense/Transfer negative -- Teable's own convention, matching the
    account's Net Activity/Current Balance fields). Transfer-type
    transactions are NOT excluded from `net`: a transfer only nets to zero
    across the ledger if its counterparty is another tracked account, and
    this API has no reliable way to tell whether that's the case (the
    sampled data includes transfers to external account numbers with no
    Transfer Account link at all). `transfers` is broken out separately so
    callers can inspect that assumption rather than have it hidden.
    """
    buckets: dict = defaultdict(lambda: {"income": 0.0, "expense": 0.0, "transfers": 0.0, "net": 0.0})
    for t in transactions:
        key = _month_key(t["date"])
        if key is None:
            continue
        bucket = buckets[key]
        bucket["net"] += t["signed_amount"] if t["signed_amount"] is not None else 0.0
        if t["type"] == "Income":
            bucket["income"] += t["amount"]
        elif t["type"] == "Expense":
            bucket["expense"] += t["amount"]
        elif t["type"] == "Transfer":
            bucket["transfers"] += t["amount"]
    return dict(sorted(buckets.items()))


def top_payees(transactions: list, *, n: int = 10, txn_type: str = "Expense") -> list:
    totals: dict = defaultdict(float)
    for t in transactions:
        if t["type"] != txn_type or not t["payee"]:
            continue
        totals[t["payee"]] += t["amount"]
    ranked = sorted(totals.items(), key=lambda kv: kv[1], reverse=True)[:n]
    return [{"payee": payee, "total": total} for payee, total in ranked]


def recurring_transactions(transactions: list) -> dict:
    """Recurring transactions grouped by frequency ('Weekly', 'Monthly', ...)."""
    grouped: dict = defaultdict(list)
    for t in transactions:
        if t["recurring"]:
            grouped[t["recurring_frequency"] or "(Unspecified)"].append(t)
    return dict(grouped)


def account_balances() -> list:
    """Current Balance / Net Activity are Teable formula fields, already
    computed server-side -- this just fetches and reshapes them."""
    table_id = schema.TABLES["finance_accounts"]
    out = []
    for r in client.iter_records(table_id):
        f = r.get("fields", {})
        out.append({
            "id": r.get("id"),
            "name": f.get("Name"),
            "type": f.get("Type"),
            "scope": f.get("Scope"),
            "active": f.get("Active", False),
            "opening_balance": f.get("Opening Balance"),
            "current_balance": f.get("Current Balance"),
            "net_activity": f.get("Net Activity"),
        })
    return out


def budget_variance(*, month: str | None = None) -> list:
    """Planned vs actual per budget line. Actual Spent/Variance/% Used are
    Teable rollup/formula fields, already computed server-side."""
    table_id = schema.TABLES["finance_budgets"]
    out = []
    for r in client.iter_records(table_id):
        f = r.get("fields", {})
        if month and _month_key(f.get("Month")) != month:
            continue
        out.append({
            "id": r.get("id"),
            "month": f.get("Month"),
            "category": _title(f.get("Category")),
            "planned_amount": f.get("Planned Amount"),
            "actual_spent": f.get("Actual Spent"),
            "variance": f.get("Variance"),
            "percent_used": f.get("% Used"),
            "scope": f.get("Scope"),
        })
    return out
