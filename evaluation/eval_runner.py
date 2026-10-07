"""Planning a batch, estimating its cost, and judging one run. No AWS calls here."""

from eval_report import RunResult
from eval_rules import RULES, brief_check_map

# Rough all-in dollars per run (model tokens + guardrail + runtime), from the measured Phase 4 runs and
# the price list. Briefs make five model calls; refusals are one call or stopped before the model runs.
ALL_IN_ESTIMATE = {
    ("nova", "brief"): 0.05,
    ("nova", "refusal"): 0.003,
    ("haiku", "brief"): 0.10,
    ("haiku", "refusal"): 0.006,
}
# Cases whose outcome is normally a full brief (or a tool-using run), whatever the category.
BRIEF_LIKE = {"brief", "injection_tool"}
BRIEF_LIKE_IDS = {"pii-bait-in-brief", "fab-revenue", "fab-price"}


def _kind(case):
    return "brief" if case.category in BRIEF_LIKE or case.id in BRIEF_LIKE_IDS else "refusal"


def plan_runs(cases, models, repeats, only=None):
    """[(case, model, repeat number)] for every case, model and repeat; `only` filters by case id."""
    if only:
        unknown = set(only) - {c.id for c in cases}
        if unknown:
            raise ValueError(f"unknown case id(s): {', '.join(sorted(unknown))}")
        cases = [c for c in cases if c.id in only]
    return [(case, model, n) for case in cases for model in models for n in range(1, repeats + 1)]


def estimate_cost(runs):
    return round(sum(ALL_IN_ESTIMATE[(model, _kind(case))] for case, model, _ in runs), 4)


def judge(case, run, model, repeat=1):
    """Apply the case's rules to the run and build the result record."""
    rules = [(name, *RULES[name](run)) for name in case.rules]
    return RunResult(
        case_id=case.id,
        category=case.category,
        model=model,
        repeat=repeat,
        passed=all(ok for _, ok, _ in rules),
        rules=rules,
        checks=brief_check_map(run) if case.category == "brief" else {},
        guardrail_blocked=run.guardrail_intervened,
        input_tokens=run.input_tokens,
        output_tokens=run.output_tokens,
        stop_reasons=list(run.stop_reasons),
        tools=[name for name, _ in run.tool_calls],
        answer=run.answer,
    )
