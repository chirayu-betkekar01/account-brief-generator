"""Guards on src/lambdas/roi_estimator/assumptions.json, the file a skeptical CFO will read."""

import json
from pathlib import Path

import pytest

from roi_estimator.roi import compute_roi

CONFIG_FILE = Path(__file__).resolve().parents[2] / "src" / "lambdas" / "roi_estimator" / "assumptions.json"
REQUIRED = {
    "aws_cost_per_server_year_usd",
    "rightsizing_factor",
    "aws_cost_per_tb_year_usd",
    "migration_cost_per_server_usd",
    "retained_cost_fraction",
}


@pytest.fixture(scope="module")
def assumptions():
    return json.loads(CONFIG_FILE.read_text(encoding="utf-8"))["assumptions"]


def test_config_defines_exactly_the_assumptions_the_model_uses(assumptions):
    assert set(assumptions) == REQUIRED


@pytest.mark.parametrize("name", sorted(REQUIRED))
def test_each_assumption_has_a_positive_number(assumptions, name):
    value = assumptions[name]["value"]
    assert isinstance(value, (int, float)) and not isinstance(value, bool), "value must be a number"
    assert value > 0


@pytest.mark.parametrize("name", sorted(REQUIRED))
def test_each_assumption_is_explained_and_sourced(assumptions, name):
    entry = assumptions[name]
    for field in ["unit", "rationale", "source"]:
        text = entry[field]
        assert isinstance(text, str) and "TODO" not in text, f"{field} still has a TODO"
    assert len(entry["unit"].strip()) >= 5
    assert len(entry["rationale"].strip()) >= 40, "explain WHY this number is reasonable"
    assert len(entry["source"].strip()) >= 10, "say where the number comes from"


def test_rightsizing_factor_is_a_fraction(assumptions):
    assert 0 < assumptions["rightsizing_factor"]["value"] <= 1


def test_retained_cost_fraction_is_a_fraction_below_one(assumptions):
    assert 0 < assumptions["retained_cost_fraction"]["value"] < 1


def test_config_values_run_through_the_model(assumptions):
    flat = {name: entry["value"] for name, entry in assumptions.items()}
    result = compute_roi(
        on_prem_annual_cost_usd=3_900_000,
        servers=340,
        storage_tb=180,
        annual_growth_pct=12,
        assumptions=flat,
    )
    assert len(result["years"]) == 3
