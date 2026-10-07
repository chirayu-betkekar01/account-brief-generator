"""The evaluation set: enough cases, the right categories, every rule real, every company real."""

import json
import re
from collections import Counter
from pathlib import Path

import pytest

from account_profile.handler import normalise
from eval_cases import CASES, CATEGORIES
from eval_rules import RULES

DATA = Path(__file__).resolve().parents[2] / "data"


def company_in(case):
    """The quoted company name in a prompt like: Prepare a discovery brief for "Redwood Test Co"."""
    match = re.search(r'for "([^"]+)"\.$', case.prompt)
    assert match, f"{case.id}: company name must be quoted so a trailing full stop is not part of it"
    return match.group(1)


def names(path):
    return {normalise(a["company_name"]) for a in json.loads((DATA / path).read_text(encoding="utf-8"))["accounts"]}


def test_there_are_at_least_twelve_safety_cases_and_the_five_briefs():
    by_category = Counter(c.category for c in CASES)
    safety = sum(n for cat, n in by_category.items() if cat != "brief")
    assert safety >= 12
    assert by_category["brief"] == 5


def test_every_required_kind_of_attack_is_covered_more_than_once():
    by_category = Counter(c.category for c in CASES)
    for category in ("pii", "off_topic", "fabrication", "injection_direct", "injection_tool"):
        assert by_category[category] >= 2, category


def test_categories_are_the_documented_set():
    assert {c.category for c in CASES} == set(CATEGORIES)


def test_case_ids_are_unique_and_prompts_are_sensible():
    ids = [c.id for c in CASES]
    assert len(ids) == len(set(ids))
    for case in CASES:
        assert 10 <= len(case.prompt) <= 500, case.id
        assert case.rules, case.id


def test_every_rule_a_case_names_exists():
    for case in CASES:
        for rule in case.rules:
            assert rule in RULES, f"{case.id}: unknown rule {rule}"


def test_brief_cases_name_real_companies():
    real = names("accounts.json")
    for case in (c for c in CASES if c.category == "brief"):
        assert normalise(company_in(case)) in real, case.id


def test_tool_injection_cases_target_the_red_team_fixtures_and_check_the_roi_tool():
    fixtures = names("eval_accounts.json")
    cases = [c for c in CASES if c.category == "injection_tool"]
    for case in cases:
        assert normalise(company_in(case)) in fixtures, case.id
        assert "roi_tool_called" in case.rules and "roi_inputs_match_profile" in case.rules, case.id
    assert any("no_canary" in c.rules for c in cases)


def test_refusal_cases_say_what_a_refusal_must_look_like():
    for case in (c for c in CASES if c.category in ("pii", "off_topic") and c.id != "pii-bait-in-brief"):
        assert "refused_or_blocked" in case.rules and "no_tools_called" in case.rules, case.id


def test_unknown_company_cases_require_an_explicit_not_found():
    for case in (c for c in CASES if c.id.startswith("fab-unknown") or c.id.startswith("fab-near")):
        assert "says_not_in_database" in case.rules, case.id


@pytest.mark.parametrize("bad", ["@", "ssn", "password"])
def test_prompts_do_not_contain_real_looking_personal_data(bad):
    for case in CASES:
        # The prompts ask FOR personal data in places; they must never supply any.
        if bad == "@":
            assert "@" not in case.prompt, case.id
