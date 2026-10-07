"""The specification for compute_roi. Hand-computed numbers; see the comment in each test.

Base case: on-prem 1,000,000/yr, 100 servers, 50 TB, 10% growth, with
  AWS 4,000 per server-year x 0.5 rightsizing, 300 per TB-year, 2,000 migration per server,
  and no retained on-prem cost (retained_cost_fraction = 0) so the arithmetic stays easy to follow.
Growth multipliers by year: 1.00, 1.10, 1.21.
"""

import copy

import pytest

from roi_estimator.roi import compute_roi

ASSUMPTIONS = {
    "aws_cost_per_server_year_usd": 4000,
    "rightsizing_factor": 0.5,
    "aws_cost_per_tb_year_usd": 300,
    "migration_cost_per_server_usd": 2000,
    "retained_cost_fraction": 0.0,
}
BASE = {
    "on_prem_annual_cost_usd": 1_000_000,
    "servers": 100,
    "storage_tb": 50,
    "annual_growth_pct": 10,
}
YEAR_MONEY_FIELDS = [
    "on_prem_cost_usd",
    "aws_run_cost_usd",
    "retained_cost_usd",
    "migration_cost_usd",
    "aws_total_usd",
    "savings_usd",
    "cumulative_savings_usd",
]


def roi(assumptions=None, **overrides):
    args = {**BASE, **overrides}
    return compute_roi(assumptions={**ASSUMPTIONS, **(assumptions or {})}, **args)


def column(result, field):
    return [year[field] for year in result["years"]]


def test_covers_three_years_in_order():
    assert column(roi(), "year") == [1, 2, 3]


def test_on_prem_cost_grows_with_the_workload():
    assert column(roi(), "on_prem_cost_usd") == pytest.approx([1_000_000, 1_100_000, 1_210_000])


def test_aws_run_cost_uses_rightsized_servers_plus_storage():
    # multiplier x (100 servers x 0.5 x 4000 + 50 TB x 300) = multiplier x 215,000
    assert column(roi(), "aws_run_cost_usd") == pytest.approx([215_000, 236_500, 260_150])


def test_migration_is_a_one_off_in_year_one():
    # 100 servers x 2,000
    assert column(roi(), "migration_cost_usd") == pytest.approx([200_000, 0, 0])


def test_aws_total_is_run_cost_plus_retained_plus_migration():
    assert column(roi(), "aws_total_usd") == pytest.approx([415_000, 236_500, 260_150])


def test_retained_cost_is_a_share_of_the_on_prem_bill_that_never_goes_away():
    # 25% of on-prem (staff, licences, network) stays: 250,000 / 275,000 / 302,500
    # AWS total = run + retained + migration = 665,000 / 511,500 / 562,650
    result = roi(assumptions={"retained_cost_fraction": 0.25})
    assert column(result, "retained_cost_usd") == pytest.approx([250_000, 275_000, 302_500])
    assert column(result, "aws_total_usd") == pytest.approx([665_000, 511_500, 562_650])
    assert result["totals"]["aws_usd"] == pytest.approx(1_739_150)
    assert result["totals"]["savings_usd"] == pytest.approx(1_570_850)
    assert result["totals"]["roi_pct"] == 90.3


def test_no_retained_cost_when_the_fraction_is_zero():
    assert column(roi(), "retained_cost_usd") == pytest.approx([0, 0, 0])


def test_savings_and_cumulative_savings():
    result = roi()
    assert column(result, "savings_usd") == pytest.approx([585_000, 863_500, 949_850])
    assert column(result, "cumulative_savings_usd") == pytest.approx([585_000, 1_448_500, 2_398_350])


def test_three_year_totals_and_roi():
    totals = roi()["totals"]
    assert totals["on_prem_usd"] == pytest.approx(3_310_000)
    assert totals["aws_usd"] == pytest.approx(911_650)
    assert totals["savings_usd"] == pytest.approx(2_398_350)
    # savings / AWS cost x 100 = 263.0779..., rounded to one decimal
    assert totals["roi_pct"] == 263.1


def test_breakeven_is_year_one_when_savings_are_positive_immediately():
    assert roi()["breakeven_year"] == 1


def test_breakeven_moves_to_year_two_when_migration_is_expensive():
    # migration 100 x 10,000 = 1,000,000 -> cumulative savings -215,000 after year 1, +648,500 after year 2
    result = roi(assumptions={"migration_cost_per_server_usd": 10_000})
    assert column(result, "cumulative_savings_usd")[0] == pytest.approx(-215_000)
    assert result["breakeven_year"] == 2


def test_a_losing_case_is_reported_honestly_not_hidden():
    # on-prem is only 100,000/yr: AWS costs far more, so ROI must go negative and never break even
    result = roi(on_prem_annual_cost_usd=100_000)
    assert result["breakeven_year"] is None
    assert result["totals"]["savings_usd"] == pytest.approx(-580_650)
    assert result["totals"]["roi_pct"] == -63.7


def test_zero_growth_keeps_every_year_flat():
    result = roi(annual_growth_pct=0)
    assert column(result, "on_prem_cost_usd") == pytest.approx([1_000_000] * 3)
    assert column(result, "aws_run_cost_usd") == pytest.approx([215_000] * 3)


def test_money_is_rounded_to_cents():
    result = roi(on_prem_annual_cost_usd=1_234_567.89, annual_growth_pct=3.3)
    for year in result["years"]:
        for field in YEAR_MONEY_FIELDS:
            assert year[field] == round(year[field], 2), field
    for field in ["on_prem_usd", "aws_usd", "savings_usd"]:
        assert result["totals"][field] == round(result["totals"][field], 2), field


def test_inputs_are_not_modified():
    assumptions = copy.deepcopy(ASSUMPTIONS)
    compute_roi(assumptions=assumptions, **BASE)
    assert assumptions == ASSUMPTIONS


@pytest.mark.parametrize(
    "overrides",
    [
        {"on_prem_annual_cost_usd": 0},
        {"on_prem_annual_cost_usd": -5},
        {"on_prem_annual_cost_usd": "abc"},
        {"on_prem_annual_cost_usd": None},
        {"servers": 0},
        {"storage_tb": -1},
        {"annual_growth_pct": -100},
        {"annual_growth_pct": -150},
    ],
)
def test_invalid_inputs_raise_value_error(overrides):
    with pytest.raises(ValueError):
        roi(**overrides)


def test_zero_storage_is_allowed():
    assert column(roi(storage_tb=0), "aws_run_cost_usd")[0] == pytest.approx(200_000)


@pytest.mark.parametrize("missing", sorted(ASSUMPTIONS))
def test_a_missing_assumption_raises_value_error(missing):
    incomplete = {k: v for k, v in ASSUMPTIONS.items() if k != missing}
    with pytest.raises(ValueError, match=missing):
        compute_roi(assumptions=incomplete, **BASE)


@pytest.mark.parametrize(
    "bad_assumptions",
    [
        {"rightsizing_factor": 0},
        {"rightsizing_factor": 1.5},
        {"retained_cost_fraction": -0.1},
        {"retained_cost_fraction": 1},
        {"aws_cost_per_server_year_usd": -1},
        {"aws_cost_per_tb_year_usd": -1},
        {"migration_cost_per_server_usd": -1},
    ],
)
def test_out_of_range_assumptions_raise_value_error(bad_assumptions):
    with pytest.raises(ValueError):
        roi(assumptions=bad_assumptions)
