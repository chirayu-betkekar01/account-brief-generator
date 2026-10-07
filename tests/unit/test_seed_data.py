"""Guards on data/accounts.json: the seed data must stay synthetic and well-formed."""

import re
from decimal import Decimal

import pytest

from account_profile.handler import normalise

TEXT_FIELDS = ["company_name", "industry", "headquarters", "current_environment", "cloud_maturity"]
NUMBER_FIELDS = ["employees", "servers", "storage_tb", "annual_infra_cost_usd", "annual_growth_pct"]
LIST_FIELDS = ["workloads", "stated_pain_points", "compliance"]

PII_PATTERNS = {
    "email address": r"[\w.+-]+@[\w-]+\.[\w.]+",
    "phone number": r"\b\d{3}[-.\s]\d{3,4}[-.\s]\d{4}\b",
    "US social security number": r"\b\d{3}-\d{2}-\d{4}\b",
}


def test_there_are_five_accounts(accounts):
    assert len(accounts) == 5


def test_every_account_has_the_expected_fields_and_types(accounts):
    for account in accounts:
        assert set(account) == set(TEXT_FIELDS + NUMBER_FIELDS + LIST_FIELDS)
        for field in TEXT_FIELDS:
            assert isinstance(account[field], str) and account[field].strip()
        for field in NUMBER_FIELDS:
            assert isinstance(account[field], (int, Decimal)) and account[field] > 0
        for field in LIST_FIELDS:
            assert isinstance(account[field], list)


def test_company_keys_are_unique(accounts):
    keys = [normalise(a["company_name"]) for a in accounts]
    assert len(keys) == len(set(keys))


def test_key_matches_what_terraform_will_compute(accounts):
    # Terraform seeds the table with lower(trimspace(name)); the handler also
    # collapses inner whitespace. They only agree if the names are already clean.
    for account in accounts:
        name = account["company_name"]
        assert normalise(name) == name.strip().lower()


@pytest.mark.parametrize("label", PII_PATTERNS)
def test_seed_data_contains_no_pii_like_strings(accounts_text, label):
    assert not re.search(PII_PATTERNS[label], accounts_text), f"found a {label}"
