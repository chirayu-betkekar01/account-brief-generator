import json

import pytest

from roi_estimator import handler
from roi_estimator.roi import compute_roi

ENTRIES = {
    "aws_cost_per_server_year_usd": 4000,
    "rightsizing_factor": 0.5,
    "aws_cost_per_tb_year_usd": 300,
    "migration_cost_per_server_usd": 2000,
    "retained_cost_fraction": 0.25,
}
EVENT = {"on_prem_annual_cost_usd": 1_000_000, "servers": 100, "storage_tb": 50, "annual_growth_pct": 10}


@pytest.fixture(autouse=True)
def test_assumptions(tmp_path, monkeypatch):
    """Point the handler at a known assumptions file so these tests do not depend on the real one."""
    config = {
        "assumptions": {
            name: {"value": value, "unit": "test unit", "rationale": f"why {name}", "source": "test"}
            for name, value in ENTRIES.items()
        }
    }
    path = tmp_path / "assumptions.json"
    path.write_text(json.dumps(config), encoding="utf-8")
    monkeypatch.setattr(handler, "ASSUMPTIONS_FILE", path)


def call(event):
    return handler.lambda_handler(event, None)  # the handler does not use the Lambda context


def test_returns_the_model_result_for_valid_input():
    result = call(EVENT)

    expected = compute_roi(assumptions=ENTRIES, **EVENT)
    assert result["ok"] is True
    assert result["totals"] == expected["totals"]
    assert result["years"] == expected["years"]
    assert result["breakeven_year"] == expected["breakeven_year"]


def test_assumptions_are_surfaced_with_their_reasoning():
    result = call(EVENT)

    entry = result["assumptions"]["rightsizing_factor"]
    assert entry["value"] == 0.5
    assert entry["rationale"] == "why rightsizing_factor"
    assert entry["source"] == "test"


def test_inputs_are_echoed_back():
    assert call(EVENT)["inputs"] == EVENT


def test_result_is_json_serialisable():
    json.dumps(call(EVENT))


@pytest.mark.parametrize(
    "event, field",
    [
        ({**EVENT, "servers": 0}, "servers"),
        ({**EVENT, "annual_growth_pct": -100}, "annual_growth_pct"),
        ({**EVENT, "on_prem_annual_cost_usd": "lots"}, "on_prem_annual_cost_usd"),
        ({k: v for k, v in EVENT.items() if k != "storage_tb"}, "storage_tb"),
        ({}, "on_prem_annual_cost_usd"),
        (None, "on_prem_annual_cost_usd"),
    ],
)
def test_bad_input_becomes_an_error_message_naming_the_field(event, field):
    result = call(event)

    assert result["ok"] is False
    assert field in result["error"]
    assert "years" not in result


def test_a_very_long_bad_value_cannot_flood_the_error_message():
    result = call({**EVENT, "on_prem_annual_cost_usd": "x" * 5000})

    assert result["ok"] is False
    assert len(result["error"]) <= handler.MAX_ERROR_LENGTH
