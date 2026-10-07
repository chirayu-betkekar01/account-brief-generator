"""Guards on data/eval_accounts.json, the red-team fixtures.

They must have exactly the schema of the real accounts (so the real tools process them), must be
unmistakably labelled, must stay out of the demo data, and must contain no personal data.
"""

import json
import re
from pathlib import Path

import pytest

from account_profile.handler import normalise
from test_seed_data import LIST_FIELDS, NUMBER_FIELDS, PII_PATTERNS, TEXT_FIELDS

DATA = Path(__file__).resolve().parents[2] / "data"
CANARY = "CANARY-7F3A91"


@pytest.fixture(scope="module")
def fixtures():
    return json.loads((DATA / "eval_accounts.json").read_text(encoding="utf-8"))["accounts"]


@pytest.fixture(scope="module")
def by_name(fixtures):
    return {a["company_name"]: a for a in fixtures}


def test_there_are_two_fixtures_and_they_are_labelled_as_test_companies(fixtures):
    assert [a["company_name"] for a in fixtures] == ["Redwood Test Co", "Bluefin Test Co"]


def test_fixtures_have_exactly_the_schema_of_the_real_accounts(fixtures):
    for account in fixtures:
        assert set(account) == set(TEXT_FIELDS + NUMBER_FIELDS + LIST_FIELDS)
        for field in TEXT_FIELDS:
            assert isinstance(account[field], str) and account[field].strip()
        for field in NUMBER_FIELDS:
            assert isinstance(account[field], (int, float)) and account[field] > 0
        for field in LIST_FIELDS:
            assert isinstance(account[field], list)


def test_fixture_keys_do_not_collide_with_real_accounts_or_each_other(fixtures, accounts):
    keys = [normalise(a["company_name"]) for a in fixtures + accounts]
    assert len(keys) == len(set(keys))
    for account in fixtures:
        assert normalise(account["company_name"]) == account["company_name"].strip().lower()


def test_the_planted_instructions_are_in_the_expected_fields(by_name):
    redwood, bluefin = by_name["Redwood Test Co"], by_name["Bluefin Test Co"]
    assert any(CANARY in p and "ignore your previous instructions" in p for p in redwood["stated_pain_points"])
    assert "set servers to 1" in bluefin["current_environment"]


def test_the_canary_appears_only_in_redwood(by_name):
    assert CANARY not in json.dumps(by_name["Bluefin Test Co"])
    assert json.dumps(by_name["Redwood Test Co"]).count(CANARY) == 1


def test_the_demo_data_contains_no_planted_instructions(accounts_text):
    lowered = accounts_text.lower()
    for marker in (CANARY.lower(), "ignore your previous", "note for ai assistants", "system notice"):
        assert marker not in lowered


@pytest.mark.parametrize("label", PII_PATTERNS)
def test_fixtures_contain_no_pii_like_strings(label):
    text = (DATA / "eval_accounts.json").read_text(encoding="utf-8")
    assert not re.search(PII_PATTERNS[label], text), f"found a {label}"
