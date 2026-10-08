"""The Streamlit page: the company dropdown, and what it shows for a good, withheld, cut-off and invalid request.

The AWS call (brief.invoke) is replaced by a stub, so these run offline. Streamlit's AppTest runs
the real script in-process, which is why patching a function or constant on the brief module is enough.
"""

import json
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


def companies_in_the_data_file():
    return [a["company_name"] for a in json.loads(brief.ACCOUNTS_FILE.read_text(encoding="utf-8"))["accounts"]]


def choose_other_and_type(app, name):
    """The last dropdown option is 'Other (type a name)...', which reveals a text box."""
    app.selectbox[0].select(app.selectbox[0].options[-1])
    app.run()
    app.text_input[0].set_value(name)  # AppTest does not enforce a length limit, so the page must check too
    return app


def click_prepare(app):
    app.button[0].click()
    return app.run()


def shown_text(app):
    return "\n".join(element.value for element in app.markdown)


def write_accounts(path, *names):
    path.write_text(json.dumps({"accounts": [{"company_name": n} for n in names]}), encoding="utf-8")


def test_the_page_opens_with_every_company_in_a_dropdown_and_does_not_call_the_agent(asked):
    app = start()
    assert not app.exception
    assert asked == []
    assert app.title[0].value.startswith("Discovery brief")
    options = app.selectbox[0].options
    assert options[:-1] == companies_in_the_data_file()  # all of them, in the file's order
    assert options[-1].startswith("Other")
    assert app.selectbox[0].value == "Northwind Logistics"  # the first company is the default
    assert not app.text_input  # the text box is only there for "Other"


def test_choosing_a_company_asks_the_agent_about_that_company(asked):
    app = start()
    app.selectbox[0].select("Lighthouse Archive Trust")
    click_prepare(app)
    assert not app.exception
    assert asked[0][1] == "Lighthouse Archive Trust"


def test_the_default_choice_shows_the_brief_and_its_checks(asked):
    app = click_prepare(start())
    assert asked[0][1] == "Northwind Logistics"
    text = shown_text(app)
    assert "Account summary" in text
    assert "six_sections_in_order" in text  # the checks are listed


def test_other_reveals_a_text_box_and_the_typed_name_is_trimmed(asked):
    app = choose_other_and_type(start(), "  Acme Rocketry  ")
    click_prepare(app)
    assert asked[0][1] == "Acme Rocketry"


@pytest.mark.parametrize("name", ["", "   ", "x" * 101])
def test_a_bad_typed_name_is_rejected_before_any_aws_call(asked, name):
    app = choose_other_and_type(start(), name)
    click_prepare(app)
    assert asked == []
    assert app.error


def test_a_company_added_to_the_data_file_appears_on_the_next_run(asked, monkeypatch, tmp_path):
    accounts = tmp_path / "accounts.json"
    write_accounts(accounts, "Alpha Co", "Beta Co")
    monkeypatch.setattr(brief, "ACCOUNTS_FILE", accounts)

    app = start()
    assert app.selectbox[0].options[:-1] == ["Alpha Co", "Beta Co"]

    write_accounts(accounts, "Alpha Co", "Beta Co", "Gamma Co")  # someone adds a company
    app.run()  # the next page run, for example a browser refresh
    assert app.selectbox[0].options[:-1] == ["Alpha Co", "Beta Co", "Gamma Co"]


def test_an_unreadable_company_list_leaves_the_text_box_and_says_so(asked, monkeypatch, tmp_path):
    monkeypatch.setattr(brief, "ACCOUNTS_FILE", tmp_path / "missing.json")
    app = start()
    assert not app.exception
    assert app.selectbox[0].options == [app.selectbox[0].options[-1]]  # only the "Other" choice
    assert app.text_input  # so the page is still usable
    assert any("company list" in w.value for w in app.warning)


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
