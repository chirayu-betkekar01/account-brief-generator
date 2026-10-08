"""Ask the discovery brief agent for a brief on one company.

    python client/brief.py "Northwind Logistics"
    python client/brief.py "Northwind Logistics" --ground --strict --save brief.md

The brief goes to standard output, progress and warnings to standard error, so the output can be
piped or saved. After the brief it prints the deterministic checks (links, services, numbers,
structure). Exit codes: 0 done, 2 error or cut off, 3 withheld by the guardrail, 4 a check failed
(only with --strict).

Needs AWS credentials (for example AWS_PROFILE=discovery-sandbox) allowed to call the harness. The
harness ARN comes from HARNESS_ARN or from `terraform output`.
"""

import argparse
import json
import os
import re
import subprocess
import sys
import uuid
from pathlib import Path

import boto3

from brief_checks import run_checks, split_sections
from brief_ground import build_source, ground_section
from brief_stream import collect

REGION = os.environ.get("AWS_REGION", "us-east-1")
MAX_COMPANY_LENGTH = 100  # same limit the account_profile Lambda enforces
# Nova 2 Lite, US geo profile, $ per million tokens (docs/costs.md, verified 2026-10-07).
PRICE_IN_PER_M, PRICE_OUT_PER_M = 0.33, 2.75
ROOT = Path(__file__).resolve().parents[1]
ACCOUNTS_FILE = ROOT / "data" / "accounts.json"  # the demo companies; the red-team records are in eval_accounts.json


def terraform_output(name):
    result = subprocess.run(
        ["terraform", "-chdir=infra/main", "output", "-raw", name],
        capture_output=True, text=True, cwd=ROOT,
    )
    if result.returncode != 0:
        sys.exit(f"Could not read terraform output {name!r}. Is the stack deployed? {result.stderr.strip()[:200]}")
    return result.stdout.strip()


def demo_companies(path=None):
    """Company names in data/accounts.json, in file order; [] if the file is missing or unusable.

    Read on every call and never cached, so a company added to the file shows up on the web page's
    next run. (It can be chosen before it is loaded into DynamoDB; the agent then says it is not in
    the database, which is a harmless failure.)"""
    try:
        accounts = json.loads(Path(path or ACCOUNTS_FILE).read_text(encoding="utf-8"))["accounts"]
        return [
            a["company_name"]
            for a in accounts
            if isinstance(a, dict) and isinstance(a.get("company_name"), str) and a["company_name"].strip()
        ]
    except (OSError, ValueError, KeyError, TypeError):
        return []


def company_error(name):
    """Why this is not a usable company name, or None if it is. Shared by the CLI and the web page."""
    name = name.strip()
    if not name or len(name) > MAX_COMPANY_LENGTH or re.search(r"[\x00-\x1f\x7f]", name):
        return f"Give a company name of 1 to {MAX_COMPANY_LENGTH} characters, on one line."
    return None


def clean_company(name):
    problem = company_error(name)
    if problem:
        sys.exit(problem)
    return name.strip()


def with_progress(events):
    """Pass events through unchanged, telling the person what the agent is doing."""
    for event in events:
        if "contentBlockStart" in event:
            start = event["contentBlockStart"].get("start", {})
            if "toolUse" in start:
                print(f"  - calling {start['toolUse']['name']}", file=sys.stderr)
        yield event


def invoke(harness_arn, company):
    client = boto3.client("bedrock-agentcore", region_name=REGION)
    response = client.invoke_harness(
        harnessArn=harness_arn,
        runtimeSessionId=str(uuid.uuid4()),  # 36 characters; the API wants at least 33
        # Quoted so a full stop after an abbreviation ("Acme Inc.") is not read as part of the name.
        messages=[{"role": "user", "content": [{"text": f'Prepare a discovery brief for "{company}".'}]}],
    )
    print(f"Asking the agent about {company} ...", file=sys.stderr)
    return collect(with_progress(response["stream"]))


def print_checks(checks):
    print("\n--- Checks (deterministic, against the tool results) ---")
    for check in checks:
        print(f"{'PASS' if check.passed else 'FAIL'}  {check.name}: {check.detail}")
    failed = sum(1 for c in checks if not c.passed)
    print(f"{len(checks) - failed} of {len(checks)} passed.")
    return failed


def print_grounding(run, company):
    guardrail_id = os.environ.get("GUARDRAIL_ID") or terraform_output("guardrail_id")
    version = os.environ.get("GUARDRAIL_VERSION") or terraform_output("guardrail_version")
    runtime = boto3.client("bedrock-runtime", region_name=REGION)
    source = build_source(run.tool_results)
    query = f"Prepare a discovery brief for {company}, using only the profile, passages and ROI result."
    sections = split_sections(run.answer)
    print("\n--- Grounding scores (informational only, see client/brief_ground.py) ---")
    for number in (4, 5):
        if number in sections:
            scores = ground_section(runtime, guardrail_id, version, source, query, sections[number])
            print(f"section {number}: " + ", ".join(f"{k.lower()} {v}" for k, v in scores.items()))


def main(argv=None):
    parser = argparse.ArgumentParser(description="Ask the discovery brief agent for a brief.")
    parser.add_argument("company", help='company name, for example "Northwind Logistics"')
    parser.add_argument("--no-checks", action="store_true", help="skip the deterministic checks")
    parser.add_argument("--ground", action="store_true", help="also show contextual grounding scores (informational)")
    parser.add_argument("--strict", action="store_true", help="exit with code 4 if any check fails")
    parser.add_argument("--save", metavar="PATH", help="also write the brief to this file")
    args = parser.parse_args(argv)

    company = clean_company(args.company)
    harness_arn = os.environ.get("HARNESS_ARN") or terraform_output("harness_arn")
    run = invoke(harness_arn, company)

    if run.guardrail_intervened:
        print("The guardrail withheld the answer (stop reason: guardrail_intervened).", file=sys.stderr)
        return 3

    print(run.answer)
    if args.save and run.answer:
        Path(args.save).write_text(run.answer + "\n", encoding="utf-8")

    cost = run.input_tokens / 1e6 * PRICE_IN_PER_M + run.output_tokens / 1e6 * PRICE_OUT_PER_M
    print(
        f"\n[{run.input_tokens} input / {run.output_tokens} output tokens, about ${cost:.3f} of model "
        f"cost; excludes guardrail and runtime charges]",
        file=sys.stderr,
    )

    if run.error or run.truncated:
        reason = run.error or f"stopped early ({', '.join(r for r in run.stop_reasons if r)})"
        print(f"WARNING: the brief may be incomplete: {reason}", file=sys.stderr)

    failed = 0
    if not args.no_checks and run.answer:
        names = [name for name, _ in run.tool_calls]
        failed = print_checks(run_checks(run.answer, run.tool_results, names))
    if args.ground and run.answer:
        print_grounding(run, company)

    if run.error or run.truncated:
        return 2
    return 4 if (args.strict and failed) else 0


if __name__ == "__main__":
    sys.exit(main())
