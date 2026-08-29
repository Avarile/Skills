import os
import sys
import unittest
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import finance  # noqa: E402


def _txn(**overrides):
    fields = {
        "Description": "Sample",
        "Date": "2026-08-15T00:00:00.000Z",
        "Type": "Expense",
        "Amount": 10,
        "Recurring": False,
        "Category": {"id": "rec1", "title": "Food"},
        "Payee": {"id": "rec2", "title": "Coles"},
        "Tags": [{"id": "rec3", "title": "Groceries"}],
        "Account": {"id": "rec4", "title": "Checking"},
    }
    fields.update(overrides)
    return {"id": "recTxn", "fields": fields}


class NormalizeTransactionTests(unittest.TestCase):
    def test_pulls_titles_out_of_link_fields(self):
        normalized = finance._normalize_transaction(_txn())
        self.assertEqual(normalized["category"], "Food")
        self.assertEqual(normalized["payee"], "Coles")
        self.assertEqual(normalized["tags"], ["Groceries"])
        self.assertEqual(normalized["account"], "Checking")

    def test_missing_amount_defaults_to_zero(self):
        normalized = finance._normalize_transaction(_txn(Amount=None))
        self.assertEqual(normalized["amount"], 0)


class SpendingByCategoryTests(unittest.TestCase):
    def test_sums_per_category_largest_first(self):
        txns = [
            finance._normalize_transaction(_txn(Amount=10, Category={"title": "Food"})),
            finance._normalize_transaction(_txn(Amount=30, Category={"title": "Rent"})),
            finance._normalize_transaction(_txn(Amount=5, Category={"title": "Food"})),
        ]
        self.assertEqual(list(finance.spending_by_category(txns).items()), [("Rent", 30), ("Food", 15)])

    def test_ignores_other_types_and_filters_by_month(self):
        txns = [
            finance._normalize_transaction(_txn(Amount=10, Type="Income", Category={"title": "Salary"})),
            finance._normalize_transaction(_txn(Amount=10, Date="2026-07-01T00:00:00Z", Category={"title": "Food"})),
            finance._normalize_transaction(_txn(Amount=20, Date="2026-08-01T00:00:00Z", Category={"title": "Food"})),
        ]
        self.assertEqual(finance.spending_by_category(txns, month="2026-08"), {"Food": 20})

    def test_uncategorized_bucket(self):
        txns = [finance._normalize_transaction(_txn(Category=None))]
        self.assertEqual(finance.spending_by_category(txns), {"(Uncategorized)": 10})


class MonthlyCashFlowTests(unittest.TestCase):
    def test_buckets_income_expense_transfers_and_nets_by_signed_amount(self):
        # Signed Amount follows Teable's own convention: Income positive,
        # Expense/Transfer negative -- net must match that, not income-expense.
        txns = [
            finance._normalize_transaction(_txn(Type="Income", Amount=100, **{"Signed Amount": 100}, Date="2026-08-01T00:00:00Z")),
            finance._normalize_transaction(_txn(Type="Expense", Amount=40, **{"Signed Amount": -40}, Date="2026-08-05T00:00:00Z")),
            finance._normalize_transaction(_txn(Type="Transfer", Amount=999, **{"Signed Amount": -999}, Date="2026-08-06T00:00:00Z")),
        ]
        result = finance.monthly_cash_flow(txns)
        self.assertEqual(
            result,
            {"2026-08": {"income": 100, "expense": 40, "transfers": 999, "net": -939}},
        )


class TopPayeesTests(unittest.TestCase):
    def test_ranks_by_total_descending_and_respects_n(self):
        txns = [
            finance._normalize_transaction(_txn(Amount=5, Payee={"title": "A"})),
            finance._normalize_transaction(_txn(Amount=50, Payee={"title": "B"})),
            finance._normalize_transaction(_txn(Amount=15, Payee={"title": "A"})),
        ]
        self.assertEqual(
            finance.top_payees(txns, n=1), [{"payee": "B", "total": 50}]
        )


class RecurringTransactionsTests(unittest.TestCase):
    def test_groups_by_frequency_and_skips_non_recurring(self):
        txns = [
            finance._normalize_transaction(_txn(Recurring=True, **{"Recurring Frequency": "Monthly"})),
            finance._normalize_transaction(_txn(Recurring=False)),
        ]
        grouped = finance.recurring_transactions(txns)
        self.assertEqual(list(grouped.keys()), ["Monthly"])
        self.assertEqual(len(grouped["Monthly"]), 1)


class AccountBalancesTests(unittest.TestCase):
    def test_reads_precomputed_formula_fields_without_recomputing(self):
        record = {
            "id": "recAcc",
            "fields": {
                "Name": "Checking",
                "Type": "Checking",
                "Current Balance": 1234.5,
                "Net Activity": 34.5,
                "Opening Balance": 1200,
            },
        }
        with mock.patch("finance.client.iter_records", return_value=[record]):
            balances = finance.account_balances()
        self.assertEqual(balances, [{
            "id": "recAcc", "name": "Checking", "type": "Checking", "scope": None,
            "active": False, "opening_balance": 1200, "current_balance": 1234.5,
            "net_activity": 34.5,
        }])


class BudgetVarianceTests(unittest.TestCase):
    def test_filters_by_month_and_reads_precomputed_fields(self):
        records = [
            {"id": "b1", "fields": {"Month": "2026-08-01T00:00:00Z", "Category": {"title": "Food"},
                                     "Planned Amount": 100, "Actual Spent": 80, "Variance": 20, "% Used": 80}},
            {"id": "b2", "fields": {"Month": "2026-07-01T00:00:00Z", "Category": {"title": "Food"},
                                     "Planned Amount": 100, "Actual Spent": 50, "Variance": 50, "% Used": 50}},
        ]
        with mock.patch("finance.client.iter_records", return_value=records):
            result = finance.budget_variance(month="2026-08")
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["actual_spent"], 80)


if __name__ == "__main__":
    unittest.main()
