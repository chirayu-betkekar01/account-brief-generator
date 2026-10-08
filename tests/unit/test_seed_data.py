"""Guards on data/accounts.json: the seed data must stay synthetic and well-formed."""

import json
import re
from decimal import Decimal
from pathlib import Path

import pytest

from account_profile.handler import normalise
from roi_estimator.roi import compute_roi

ASSUMPTIONS_FILE = Path(__file__).resolve().parents[2] / "src" / "lambdas" / "roi_estimator" / "assumptions.json"

TEXT_FIELDS = ["company_name", "industry", "headquarters", "current_environment", "cloud_maturity"]
NUMBER_FIELDS = ["employees", "servers", "storage_tb", "annual_infra_cost_usd", "annual_growth_pct"]
LIST_FIELDS = ["workloads", "stated_pain_points", "compliance"]

PII_PATTERNS = {
    "email address": r"[\w.+-]+@[\w-]+\.[\w.]+",
    "phone number": r"\b\d{3}[-.\s]\d{3,4}[-.\s]\d{4}\b",
    "US social security number": r"\b\d{3}-\d{2}-\d{4}\b",
}


def test_there_are_nine_accounts(accounts):
    assert len(accounts) == 9


def _roi(account):
    assumptions = {k: v["value"] for k, v in json.loads(ASSUMPTIONS_FILE.read_text(encoding="utf-8"))["assumptions"].items()}
    return compute_roi(
        on_prem_annual_cost_usd=account["annual_infra_cost_usd"],
        servers=account["servers"],
        storage_tb=account["storage_tb"],
        annual_growth_pct=account["annual_growth_pct"],
        assumptions=assumptions,
    )


def test_every_account_can_be_run_through_the_roi_model(accounts):
    for account in accounts:
        assert _roi(account)["totals"]["on_prem_usd"] > 0, account["company_name"]


def test_at_least_one_demo_account_loses_money_so_the_tool_is_seen_reporting_it(accounts):
    # The model must report a losing case as it is (negative savings, no breakeven). A demo set where
    # every company wins would never show that. Lighthouse is storage-heavy and cheap to run on premises.
    losers = [a["company_name"] for a in accounts if _roi(a)["totals"]["savings_usd"] < 0]
    assert losers == ["Lighthouse Archive Trust"]
    assert _roi(next(a for a in accounts if a["company_name"] == losers[0]))["breakeven_year"] is None


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
