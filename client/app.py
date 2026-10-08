"""A small web page for the discovery brief agent.

    make ui

It calls the same code as the command line (client/brief.py), so it needs the same things: AWS
credentials allowed to call the harness (for example AWS_PROFILE=discovery-sandbox) and the harness
ARN, from HARNESS_ARN or from `terraform output`. Everything runs on your machine; the page is not
published anywhere. `make ui` binds to localhost because Streamlit's default listens on every
network interface, and anyone who could open the page could run briefs on your AWS credentials.
"""

import json
import os
from pathlib import Path

import streamlit as st

import brief
from brief_checks import run_checks

ACCOUNTS = Path(__file__).resolve().parents[1] / "data" / "accounts.json"


def demo_companies():
    accounts = json.loads(ACCOUNTS.read_text(encoding="utf-8"))["accounts"]
    return [account["company_name"] for account in accounts]


def harness_arn():
    arn = os.environ.get("HARNESS_ARN")
    if arn:
        return arn
    try:
        return brief.terraform_output("harness_arn")
    except SystemExit as exc:  # terraform_output exits with a message; a web page should show it instead
        st.error(str(exc.code))
        st.stop()


def show_checks(run):
    names = [name for name, _ in run.tool_calls]
    checks = run_checks(run.answer, run.tool_results, names)
    failed = [c for c in checks if not c.passed]
    with st.expander(f"Checks against the tool results: {len(checks) - len(failed)} of {len(checks)} passed", expanded=bool(failed)):
        for check in checks:
            st.markdown(f"{'✅' if check.passed else '❌'} **{check.name}**: {check.detail}")
        st.caption(
            "Deterministic string and number comparisons. A failed check means the brief says something the "
            "retrieved passages or the ROI tool did not (for example an AWS service no passage mentions)."
        )


def show_run(company, run):
    if run.guardrail_intervened:
        st.warning("The guardrail withheld the answer (stop reason: guardrail_intervened).")
        return
    if run.error or run.truncated:
        reason = run.error or f"stopped early ({', '.join(r for r in run.stop_reasons if r)})"
        st.warning(f"The brief may be incomplete: {reason}")
    if not run.answer:
        return

    # Streamlit typesets text between two dollar signs as a formula, and a brief is full of prices.
    st.markdown(run.answer.replace("$", r"\$"))

    cost = run.input_tokens / 1e6 * brief.PRICE_IN_PER_M + run.output_tokens / 1e6 * brief.PRICE_OUT_PER_M
    st.caption(
        f"{run.input_tokens:,} input and {run.output_tokens:,} output tokens, about ${cost:.3f} of model cost "
        "(excludes guardrail and runtime charges)."
    )
    show_checks(run)
    with st.expander("What the agent called"):
        for name, arguments in run.tool_calls:
            st.markdown(f"**{name}**")
            st.json(arguments if isinstance(arguments, dict) else {"unparseable input": arguments})


st.set_page_config(page_title="Discovery Brief Agent", page_icon="📝")
st.title("Discovery brief & ROI agent")
st.caption("Fictional companies only. Try: " + ", ".join(demo_companies()) + ".")

company = st.text_input("Company name", value="Northwind Logistics")
if st.button("Prepare brief", type="primary"):
    problem = brief.company_error(company)
    if problem:
        st.error(problem)
    else:
        with st.spinner("The agent is looking up the account, searching best practice and estimating the ROI (about a minute)..."):
            st.session_state["result"] = (company.strip(), brief.invoke(harness_arn(), company.strip()))

if "result" in st.session_state:
    show_run(*st.session_state["result"])
