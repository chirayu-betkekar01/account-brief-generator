"""The Streamlit page: what it shows for a good, withheld, cut-off and invalid request.

The AWS call (brief.invoke) is replaced by a stub, so these run offline. Streamlit's AppTest runs
the real script in-process, which is why patching the function on the brief module is enough.
"""

from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

import brief
from brief_stream import BriefRun
from test_brief_cli import northwind_run

APP = Path(__file__).resolve().parents[2] / "client" / "app.py"


class Asked(list):
    """Every (harness ARN, company) the stub was asked for; .state["run"] is what it answers with."""

    state = None


@pytest.fixture
def asked(monkeypatch):
    calls = Asked()
    state = {"run": northwind_run()}
    monkeypatch.setenv("HARNESS_ARN", "arn:aws:bedrock-agentcore:us-east-1:ACCOUNT:harness/test")
    monkeypatch.setattr(brief, "invoke", lambda arn, company: calls.append((arn, company)) or state["run"])
    calls.state = state
    return calls


def start():
    app = AppTest.from_file(str(APP), default_timeout=30)
    app.run()
    return app


def click_prepare(app, company=None):
    if company is not None:
        app.text_input[0].set_value(company)
    app.button[0].click()
    return app.run()


def shown_text(app):
    return "\n".join(element.value for element in app.markdown)


def test_the_page_opens_without_calling_the_agent(asked):
    app = start()
    assert not app.exception
    assert asked == []
    assert app.title[0].value.startswith("Discovery brief")
    assert "Northwind Logistics" in "".join(c.value for c in app.caption)  # the demo companies are listed


def test_a_request_shows_the_brief_and_its_checks(asked):
    app = click_prepare(start(), "  Northwind Logistics  ")
    assert not app.exception
    assert asked[0][1] == "Northwind Logistics"  # trimmed before it is sent
    text = shown_text(app)
    assert "Account summary" in text
    assert "six_sections_in_order" in text  # the checks are listed


def test_dollar_signs_are_escaped_so_they_are_not_rendered_as_maths(asked):
    # Two dollar signs in one paragraph make Streamlit typeset what is between them as a formula.
    app = click_prepare(start())
    brief_text = next(m.value for m in app.markdown if "Account summary" in m.value)
    assert "$" in brief_text
    assert "$" not in brief_text.replace(r"\$", "")


def test_a_withheld_answer_says_so_and_shows_no_brief(asked):
    asked.state["run"] = BriefRun(answer="", stop_reasons=["tool_use", "tool_result", "guardrail_intervened"])
    app = click_prepare(start())
    assert "guardrail" in app.warning[0].value.lower()
    assert "Account summary" not in shown_text(app)


def test_a_cut_off_brief_is_shown_with_a_warning(asked):
    asked.state["run"] = northwind_run(stop_reasons=["max_tokens"])
    app = click_prepare(start())
    assert "incomplete" in app.warning[0].value
    assert "Account summary" in shown_text(app)


@pytest.mark.parametrize("name", ["", "   ", "x" * 101])
def test_a_bad_name_is_rejected_before_any_aws_call(asked, name):
    app = start()
    app.text_input[0].set_value(name)  # AppTest does not enforce max_chars, so the page must check too
    app.button[0].click()
    app.run()
    assert asked == []
    assert app.error
