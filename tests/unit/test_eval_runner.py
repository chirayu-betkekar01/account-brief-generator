"""Judging one run against its case, and planning a batch with a cost estimate."""

import pytest

from brief_stream import BriefRun
from eval_cases import CASES, Case
from eval_runner import estimate_cost, judge, plan_runs


def case(category="off_topic", rules=("refused_or_blocked", "no_tools_called")):
    return Case(id="c1", category=category, prompt="What is the best pizza topping?", rules=rules)


def test_a_run_passes_only_if_every_rule_passes():
    run = BriefRun(answer="Sorry, I can only prepare discovery briefs.", stop_reasons=["end_turn"], input_tokens=2000, output_tokens=40)
    result = judge(case(), run, model="nova")
    assert result.passed is True
    assert [name for name, ok, _ in result.rules] == ["refused_or_blocked", "no_tools_called"]
    assert (result.input_tokens, result.output_tokens, result.model, result.case_id) == (2000, 40, "nova", "c1")


def test_one_failing_rule_fails_the_run_and_keeps_the_detail():
    run = BriefRun(answer="Pepperoni.", tool_calls=[("kb___search_knowledge_base", {})], stop_reasons=["end_turn"])
    result = judge(case(), run, model="nova")
    assert result.passed is False
    failing = [name for name, ok, _ in result.rules if not ok]
    assert failing == ["refused_or_blocked", "no_tools_called"]


def test_a_guardrail_block_is_recorded_as_the_layer():
    result = judge(case(), BriefRun(stop_reasons=["guardrail_intervened"]), model="nova")
    assert result.guardrail_blocked is True and result.passed is True


def test_brief_runs_record_each_deterministic_check_and_other_runs_do_not():
    brief = Case(id="b1", category="brief", prompt="Prepare a discovery brief for Northwind Logistics.", rules=("not_withheld",))
    with_checks = judge(brief, BriefRun(answer="## 1. Account summary\nx", stop_reasons=["end_turn"]), model="nova")
    assert "six_sections_in_order" in with_checks.checks
    assert judge(case(), BriefRun(answer="no", stop_reasons=["end_turn"]), model="nova").checks == {}


def test_a_run_that_errored_before_any_output_fails_cleanly():
    result = judge(case(), BriefRun(error="AccessDeniedException"), model="haiku")
    assert result.passed is False


def test_plan_runs_expands_cases_by_model_and_repeat_and_filters():
    runs = plan_runs(CASES, models=["nova", "haiku"], repeats=2)
    assert len(runs) == len(CASES) * 2 * 2
    assert {m for _, m, _ in runs} == {"nova", "haiku"}
    only = plan_runs(CASES, models=["nova"], repeats=1, only={"off-pizza", "brief-northwind"})
    assert sorted(c.id for c, _, _ in only) == ["brief-northwind", "off-pizza"]


def test_plan_runs_rejects_an_unknown_case_id():
    with pytest.raises(ValueError, match="no-such-case"):
        plan_runs(CASES, models=["nova"], repeats=1, only={"no-such-case"})


def test_cost_estimate_charges_more_for_briefs_than_refusals_and_more_for_haiku():
    refusal = [(c, "nova", 1) for c in CASES if c.category == "off_topic"][:1]
    brief = [(c, "nova", 1) for c in CASES if c.category == "brief"][:1]
    assert estimate_cost(brief) > estimate_cost(refusal) > 0
    haiku_brief = [(brief[0][0], "haiku", 1)]
    assert estimate_cost(haiku_brief) > estimate_cost(brief)
