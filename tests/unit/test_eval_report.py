"""Turning many run results into the numbers and the markdown report."""

from eval_report import RunResult, aggregate, flagged_services, layer_breakdown, model_cost, per_check_rates, render_markdown

PRICES = {"nova": (0.33, 2.75), "haiku": (1.10, 5.50)}


def result(case_id="c1", category="pii", model="nova", passed=True, repeat=1, guardrail_blocked=False,
           in_tokens=0, out_tokens=0, checks=None, rules=None):
    return RunResult(case_id=case_id, category=category, model=model, repeat=repeat, passed=passed,
                     rules=rules or [("r", passed, "detail")], checks=checks or {}, guardrail_blocked=guardrail_blocked,
                     input_tokens=in_tokens, output_tokens=out_tokens, stop_reasons=["end_turn"], tools=[], answer="")


def test_aggregate_counts_passes_per_category_and_model():
    results = [
        result(category="pii", model="nova", passed=True),
        result(category="pii", model="nova", passed=False, repeat=2),
        result(category="pii", model="haiku", passed=True),
        result(category="off_topic", model="nova", passed=True),
    ]
    table = aggregate(results)
    assert table["pii"]["nova"] == (1, 2)
    assert table["pii"]["haiku"] == (1, 1)
    assert table["off_topic"]["nova"] == (1, 1)
    assert "haiku" not in table["off_topic"]


def test_model_cost_uses_per_million_token_prices():
    r = result(model="nova", in_tokens=1_000_000, out_tokens=1_000_000)
    assert model_cost(r, PRICES) == 0.33 + 2.75
    haiku = result(model="haiku", in_tokens=21_950, out_tokens=1_317)
    assert model_cost(haiku, PRICES) == round(21_950 / 1e6 * 1.10 + 1_317 / 1e6 * 5.50, 6)  # 0.031388


def test_per_check_rates_cover_only_brief_runs_and_group_by_model():
    results = [
        result(category="brief", model="nova", checks={"services_supported": True, "links_from_passages": True}),
        result(category="brief", model="nova", checks={"services_supported": False, "links_from_passages": True}, repeat=2),
        result(category="pii", model="nova", checks={"services_supported": False}),
    ]
    rates = per_check_rates(results)
    assert rates["nova"]["services_supported"] == (1, 2)
    assert rates["nova"]["links_from_passages"] == (2, 2)


def test_layer_breakdown_separates_guardrail_blocks_from_model_refusals():
    results = [
        result(category="pii", model="nova", guardrail_blocked=True),
        result(category="pii", model="nova", guardrail_blocked=True, repeat=2),
        result(category="off_topic", model="nova", guardrail_blocked=False),
        result(category="off_topic", model="nova", passed=False, repeat=2),
        result(category="brief", model="nova"),
    ]
    layers = layer_breakdown(results)
    assert layers["nova"] == {"guardrail": 2, "model_or_tools": 1, "failed": 1}


def test_flagged_services_are_counted_by_name_across_brief_runs():
    a = "not found word for word in any retrieved passage: AWS Lambda, Amazon RDS"
    b = "not found word for word in any retrieved passage: Amazon RDS"
    results = [
        result(category="brief", model="nova", checks={"services_supported": False}),
        result(category="brief", model="nova", checks={"services_supported": False}, repeat=2),
        result(category="brief", model="nova", checks={"services_supported": True}, repeat=3),
    ]
    results[0].check_details = {"services_supported": a}
    results[1].check_details = {"services_supported": b}
    assert flagged_services(results)["nova"] == {"Amazon RDS": 2, "AWS Lambda": 1}


def test_markdown_report_shows_the_counts_failures_and_cost():
    results = [
        result(case_id="pii-ceo", category="pii", model="nova", passed=True, in_tokens=2000, out_tokens=50),
        result(case_id="off-code", category="off_topic", model="nova", passed=False,
               rules=[("no_code_block", False, "answer contains a code block")], in_tokens=2000, out_tokens=300),
    ]
    md = render_markdown(results, PRICES, title="Evaluation", generated="2026-10-08")
    assert "# Evaluation" in md
    assert "| pii | 1/1" in md
    assert "| off_topic | 0/1" in md
    assert "off-code" in md and "answer contains a code block" in md  # failures are listed with the reason
    assert "$" in md  # cost is reported
