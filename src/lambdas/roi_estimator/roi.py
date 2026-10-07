"""3-year ROI / TCO model: staying on-premises vs moving to AWS.

Pure Python, no AWS calls, so it is deterministic and easy to test. The numbers
it uses come in as `assumptions`; nothing is hard-coded here.

For each year t = 1, 2, 3:

    growth_multiplier(t)  = (1 + annual_growth_pct / 100) ** (t - 1)     # year 1 = today's size
    on_prem_cost(t)       = on_prem_annual_cost_usd * growth_multiplier(t)
    aws_run_cost(t)       = growth_multiplier(t) * (
                                servers * rightsizing_factor * aws_cost_per_server_year_usd
                                + storage_tb * aws_cost_per_tb_year_usd)
    retained_cost(t)      = on_prem_cost(t) * retained_cost_fraction   # staff, licences, network that stay
    migration_cost(t)     = servers * migration_cost_per_server_usd    if t == 1, else 0
    aws_total(t)          = aws_run_cost(t) + retained_cost(t) + migration_cost(t)
    savings(t)            = on_prem_cost(t) - aws_total(t)             # negative when AWS costs more
    cumulative_savings(t) = savings(1) + ... + savings(t)

Totals are sums over the three years. roi_pct = total savings / total AWS cost * 100.
breakeven_year is the first year whose cumulative savings is >= 0, or None.

Money is computed at full precision and rounded to cents only in the output.
A losing case is reported as it is (negative savings, no breakeven), never hidden.
"""

YEARS = 3

REQUIRED_ASSUMPTIONS = (
    "aws_cost_per_server_year_usd",
    "rightsizing_factor",
    "aws_cost_per_tb_year_usd",
    "migration_cost_per_server_usd",
    "retained_cost_fraction",
)
NON_NEGATIVE_COSTS = (
    "aws_cost_per_server_year_usd",
    "aws_cost_per_tb_year_usd",
    "migration_cost_per_server_usd",
)


def _number(name, value):
    # bool is a subclass of int, so it must be rejected explicitly.
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{name} must be a number, got {value!r}")
    return value


def _validate_assumptions(assumptions):
    for name in REQUIRED_ASSUMPTIONS:
        if name not in assumptions:
            raise ValueError(f"missing assumption: {name}")
        _number(name, assumptions[name])
    for name in NON_NEGATIVE_COSTS:
        if assumptions[name] < 0:
            raise ValueError(f"{name} must not be negative")
    if not 0 < assumptions["rightsizing_factor"] <= 1:
        raise ValueError("rightsizing_factor must be greater than 0 and at most 1")
    if not 0 <= assumptions["retained_cost_fraction"] < 1:
        raise ValueError("retained_cost_fraction must be at least 0 and less than 1")


def compute_roi(
    *,
    on_prem_annual_cost_usd,
    servers,
    storage_tb,
    annual_growth_pct,
    assumptions,
):
    cost = _number("on_prem_annual_cost_usd", on_prem_annual_cost_usd)
    server_count = _number("servers", servers)
    storage = _number("storage_tb", storage_tb)
    growth = _number("annual_growth_pct", annual_growth_pct)
    if cost <= 0:
        raise ValueError("on_prem_annual_cost_usd must be greater than 0")
    if server_count <= 0:
        raise ValueError("servers must be greater than 0")
    if storage < 0:
        raise ValueError("storage_tb must not be negative")
    if growth <= -100:
        raise ValueError("annual_growth_pct must be greater than -100")
    _validate_assumptions(assumptions)

    infrastructure_per_multiplier = (
        server_count * assumptions["rightsizing_factor"] * assumptions["aws_cost_per_server_year_usd"]
        + storage * assumptions["aws_cost_per_tb_year_usd"]
    )

    years = []
    totals = {"on_prem": 0.0, "aws": 0.0, "savings": 0.0}
    cumulative = 0.0
    breakeven_year = None
    for year in range(1, YEARS + 1):
        multiplier = (1 + growth / 100) ** (year - 1)
        on_prem = cost * multiplier
        run = infrastructure_per_multiplier * multiplier
        retained = on_prem * assumptions["retained_cost_fraction"]
        migration = server_count * assumptions["migration_cost_per_server_usd"] if year == 1 else 0.0
        aws_total = run + retained + migration
        savings = on_prem - aws_total
        cumulative += savings
        if breakeven_year is None and cumulative >= 0:
            breakeven_year = year

        totals["on_prem"] += on_prem
        totals["aws"] += aws_total
        totals["savings"] += savings
        years.append(
            {
                "year": year,
                "on_prem_cost_usd": round(on_prem, 2),
                "aws_run_cost_usd": round(run, 2),
                "retained_cost_usd": round(retained, 2),
                "migration_cost_usd": round(migration, 2),
                "aws_total_usd": round(aws_total, 2),
                "savings_usd": round(savings, 2),
                "cumulative_savings_usd": round(cumulative, 2),
            }
        )

    return {
        "years": years,
        "totals": {
            "on_prem_usd": round(totals["on_prem"], 2),
            "aws_usd": round(totals["aws"], 2),
            "savings_usd": round(totals["savings"], 2),
            "roi_pct": round(totals["savings"] / totals["aws"] * 100, 1),
        },
        "breakeven_year": breakeven_year,
    }
