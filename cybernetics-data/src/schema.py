"""Table identifiers and field-name reference for the cybernetics-data instance.

Source: cybernetics-data/api-docs/* (captured 2026-08-29 from
https://cybernetics.avarile.com, a self-hosted Teable instance).

Field IDs are deliberately NOT captured here. The API requires field IDs
for `filter`/`orderBy` query params, but every function in this package
fetches with `fieldKeyType=name` and reshapes by field name in Python
instead, so that requirement never applies to this codebase.
"""

TABLES = {
    "finance_accounts": "tblJLklwpGwbrfDlwIz",
    "finance_budgets": "tblDk3iXFz5YiYUkwz6",
    "finance_categories": "tblp2Jvb2g90PN3fX4d",
    "finance_payees": "tblpyC3PfoG0DN8dQ2t",
    "finance_tags": "tblhOQKXpSzr0Ezh8rR",
    "finance_transactions": "tblylfLkXFkYH2qB0ZQ",
    "knowledge_type": "tblWcq6Kof1AFHvbC5e",
    "knowledges": "tblVTWb1kxXSFPBq4Fq",
}

FINANCE_TRANSACTIONS_FIELDS = [
    "Description", "Date", "Type", "Amount", "Recurring",
    "Recurring Frequency", "Receipt", "Notes", "Account", "Transfer Account",
    "Category", "Payee", "Tags", "Budget", "Scope", "Signed Amount",
]

FINANCE_ACCOUNTS_FIELDS = [
    "Name", "Scope", "Type", "Institution", "Opening Balance",
    "Opening Balance Date", "Active", "finance_Transactions",
    "Own Txn Total", "Incoming Transfer Total", "Net Activity",
    "Current Balance",
]

FINANCE_BUDGETS_FIELDS = [
    "Month", "Planned Amount", "Category", "finance_Transactions", "Scope",
    "Actual Spent", "Variance", "% Used",
]

FINANCE_CATEGORIES_FIELDS = [
    "Name", "Type", "Scope", "Parent Category", "finance_Categories",
    "Parent Name", "Full Path", "finance_Payees", "finance_Budgets",
    "finance_Transactions",
]

FINANCE_PAYEES_FIELDS = [
    "Name", "Type", "Scope", "Default Category", "finance_Transactions",
]

FINANCE_TAGS_FIELDS = ["Name", "Color", "finance_Transactions"]

KNOWLEDGE_FIELDS = [
    "title", "context", "created_at", "updated_at", "deleted_at",
    "is_active", "id", "knowledge_type", "knowledge_parent", "knowledges",
    "related_knowledge",
]

KNOWLEDGE_TYPE_FIELDS = [
    "title", "context", "created_at", "updated_at", "deleted_at",
    "is_active", "id", "knowledges", "credentials", "child_types",
    "parent_type",
]
