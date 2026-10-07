"""3-year ROI / TCO model: on-premises vs AWS.

YOUR EXERCISE. Replace the body of compute_roi so that
    .venv\\Scripts\\python.exe -m pytest tests/unit/test_roi.py
passes. Read the tests: they are the specification.

The model, for each year t = 1, 2, 3:

    growth_multiplier(t)  = (1 + annual_growth_pct / 100) ** (t - 1)     # year 1 = today's size
    on_prem_cost(t)       = on_prem_annual_cost_usd * growth_multiplier(t)
    aws_run_cost(t)       = growth_multiplier(t) * (
                                servers * rightsizing_factor * aws_cost_per_server_year_usd
                                + storage_tb * aws_cost_per_tb_year_usd)
    migration_cost(t)     = servers * migration_cost_per_server_usd   if t == 1, else 0
    aws_total(t)          = aws_run_cost(t) + migration_cost(t)
    savings(t)            = on_prem_cost(t) - aws_total(t)             # may be negative
    cumulative_savings(t) = savings(1) + ... + savings(t)

Totals are the sums over the three years:
    roi_pct = total savings / total AWS cost * 100        (rounded to 1 decimal)
    breakeven_year = first year whose cumulative savings is >= 0, or None if there is none

Return shape (all money in USD, rounded to 2 decimals only at the end):

    {
        "years": [
            {"year": 1, "on_prem_cost_usd": ..., "aws_run_cost_usd": ..., "migration_cost_usd": ...,
             "aws_total_usd": ..., "savings_usd": ..., "cumulative_savings_usd": ...},
            ...                                                          # years 2 and 3
        ],
        "totals": {"on_prem_usd": ..., "aws_usd": ..., "savings_usd": ..., "roi_pct": ...},
        "breakeven_year": 1,
    }

Validation: raise ValueError (with a message that names the bad field) when
  - on_prem_annual_cost_usd <= 0, servers <= 0, storage_tb < 0, or annual_growth_pct <= -100
  - any of those is not a number
  - an assumption is missing, or is negative, or rightsizing_factor is not in (0, 1]
Do not modify the dicts you are given.

Hints: write the validation first (the tests for it are quick wins), then the loop over years.
A ValueError here becomes a clean error message for the agent in the Lambda handler.
"""

YEARS = 3


def compute_roi(
    *,
    on_prem_annual_cost_usd,
    servers,
    storage_tb,
    annual_growth_pct,
    assumptions,
):
    raise NotImplementedError("Your turn: see the module docstring and tests/unit/test_roi.py")
