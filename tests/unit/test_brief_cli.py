"""The command-line client: input validation and exit codes. The AWS call is replaced by a stub."""

import json
from pathlib import Path

import pytest

import brief
from brief_stream import BriefRun

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "briefs"


def northwind_run(**overrides):
    answer = (FIXTURES / "northwind.answer.md").read_text(encoding="utf-8")
    tools = list(json.loads((FIXTURES / "northwind.tools.json").read_text(encoding="utf-8")).values())
    calls = [("profile___get_account_profile", {}), ("kb___search_knowledge_base", {}),
             ("kb___search_knowledge_base", {}), ("roi___estimate_roi", {})]
    run = BriefRun(answer=answer, tool_calls=calls, tool_results=tools, stop_reasons=["tool_use", "end_turn"],
                   input_tokens=20000, output_tokens=1500)
    for key, value in overrides.items():
        setattr(run, key, value)
    return run


@pytest.fixture
def stub(monkeypatch):
    """Replace the AWS call; returns a dict the test can set 'run' on."""
    state = {"run": northwind_run(), "asked": []}
    monkeypatch.setenv("HARNESS_ARN", "arn:aws:bedrock-agentcore:us-east-1:ACCOUNT:harness/test")

    def fake_invoke(harness_arn, company):
        state["asked"].append((harness_arn, company))
        return state["run"]

    monkeypatch.setattr(brief, "invoke", fake_invoke)
    return state


def test_a_clean_brief_prints_the_answer_and_exits_zero(stub, capsys):
    assert brief.main(["Northwind Logistics"]) == 0
    out = capsys.readouterr().out
    assert "## 1. Account summary" in out
    assert "Checks (deterministic" in out
    assert stub["asked"][0][1] == "Northwind Logistics"


def test_a_guardrail_intervention_exits_three_and_prints_no_answer(stub, capsys):
    stub["run"] = BriefRun(answer="", stop_reasons=["tool_use", "tool_result", "guardrail_intervened"])
    assert brief.main(["Northwind Logistics"]) == 3
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "guardrail" in captured.err.lower()


@pytest.mark.parametrize("overrides", [{"stop_reasons": ["max_tokens"]}, {"error": "stream broke"}])
def test_a_cut_off_or_failed_run_exits_two_with_a_warning(stub, capsys, overrides):
    stub["run"] = northwind_run(**overrides)
    assert brief.main(["Northwind Logistics"]) == 2
    assert "incomplete" in capsys.readouterr().err


def test_strict_turns_a_failed_check_into_exit_four(stub):
    broken = northwind_run()
    broken.answer = broken.answer.replace("5,391,484", "5,391,485")
    stub["run"] = broken
    assert brief.main(["Northwind Logistics"]) == 0  # reported but not fatal by default
    assert brief.main(["Northwind Logistics", "--strict"]) == 4


def test_no_checks_skips_the_check_report(stub, capsys):
    brief.main(["Northwind Logistics", "--no-checks"])
    assert "Checks (deterministic" not in capsys.readouterr().out


def test_save_writes_the_brief_to_a_file(stub, tmp_path):
    target = tmp_path / "brief.md"
    brief.main(["Northwind Logistics", "--save", str(target)])
    assert target.read_text(encoding="utf-8").startswith("## 1. Account summary")


@pytest.mark.parametrize("name", ["", "   ", "x" * 101, "two\nlines", "tab\there"])
def test_bad_company_names_are_rejected_before_any_aws_call(stub, name):
    with pytest.raises(SystemExit):
        brief.main([name])
    assert stub["asked"] == []


@pytest.mark.parametrize("name", ["Northwind Logistics", "  Acme Inc.  "])
def test_company_error_accepts_good_names(name):
    assert brief.company_error(name) is None


@pytest.mark.parametrize("name", ["", "   ", "x" * 101, "two\nlines"])
def test_company_error_explains_what_is_wrong(name):
    assert "company name" in brief.company_error(name)


def test_the_company_name_is_trimmed(stub):
    brief.main(["  Northwind Logistics  "])
    assert stub["asked"][0][1] == "Northwind Logistics"
