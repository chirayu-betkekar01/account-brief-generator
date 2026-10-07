"""Run the evaluation against the live agent and write a report.

    python scripts/eval_agent.py --dry-run                         # show the plan and cost estimate; no AWS calls
    python scripts/eval_agent.py --only off-pizza,brief-northwind  # a few cases
    python scripts/eval_agent.py --models nova --repeats 1         # the whole set on the deployed model
    python scripts/eval_agent.py --models nova,haiku --repeats 3   # the model comparison

Models: "nova" is the harness as deployed (Nova 2 Lite). "haiku" swaps the model for Claude Haiku 4.5
on each call with a per-call override. The override REPLACES the harness's model settings, so the
guardrail configuration is sent again; without it the guardrail would silently vanish and the
comparison would be unfair (that is the per-call override gap found in Phase 4).

Cost guard: the estimate must be under --max-usd to start, and the run stops launching new calls if the
measured model cost (doubled to allow for guardrail and runtime charges) passes the limit.
Needs AWS credentials, for example AWS_PROFILE=discovery-sandbox, and a deployed stack that includes
the red-team fixtures (include_eval_fixtures = true).
"""

import argparse
import datetime
import json
import subprocess
import sys
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict
from pathlib import Path

import boto3
from botocore.config import Config

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "client"), str(ROOT / "evaluation")]

from brief_stream import BriefRun, collect  # noqa: E402
from eval_cases import CASES  # noqa: E402
from eval_report import model_cost, render_markdown  # noqa: E402
from eval_runner import estimate_cost, judge, plan_runs  # noqa: E402

REGION = "us-east-1"
MODEL_IDS = {"nova": None, "haiku": "us.anthropic.claude-haiku-4-5-20251001-v1:0"}
PRICES = {"nova": (0.33, 2.75), "haiku": (1.10, 5.50)}  # $ per million tokens, US geo profiles (docs/costs.md)


def terraform_output(name):
    result = subprocess.run(
        ["terraform", "-chdir=infra/main", "output", "-raw", name], capture_output=True, text=True, cwd=ROOT
    )
    if result.returncode != 0:
        sys.exit(f"Could not read terraform output {name!r}. Is the stack deployed?")
    return result.stdout.strip()


def invoke_once(client, harness_arn, model_key, prompt, guardrail):
    kwargs = {}
    if MODEL_IDS[model_key]:
        kwargs["model"] = {
            "bedrockModelConfig": {
                "modelId": MODEL_IDS[model_key],
                "apiFormat": "converse_stream",
                "temperature": 0.2,
                "maxTokens": 3000,
                "additionalParams": {"guardrailConfig": guardrail},
            }
        }
    try:
        response = client.invoke_harness(
            harnessArn=harness_arn,
            runtimeSessionId=str(uuid.uuid4()),
            messages=[{"role": "user", "content": [{"text": prompt}]}],
            **kwargs,
        )
    except Exception as exc:  # noqa: BLE001 - a failed call is a result, not a crash
        return BriefRun(error=f"{type(exc).__name__}: {exc}"[:300])
    return collect(response["stream"])


def main(argv=None):
    parser = argparse.ArgumentParser(description="Evaluate the discovery brief agent.")
    parser.add_argument("--models", default="nova", help="comma list from: nova, haiku (default nova)")
    parser.add_argument("--repeats", type=int, default=1, help="runs per case per model (models are not deterministic)")
    parser.add_argument("--only", default="", help="comma list of case ids to run")
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--max-usd", type=float, default=3.0, help="cost limit for the whole run (default 3.00)")
    parser.add_argument("--dry-run", action="store_true", help="print the plan and estimate, call nothing")
    parser.add_argument("--report", help="where to write the markdown report (default evaluation/results/<time>.md)")
    args = parser.parse_args(argv)

    models = [m.strip() for m in args.models.split(",") if m.strip()]
    for m in models:
        if m not in MODEL_IDS:
            sys.exit(f"unknown model {m!r}; choose from {', '.join(MODEL_IDS)}")
    only = {c.strip() for c in args.only.split(",") if c.strip()}
    runs = plan_runs(CASES, models, args.repeats, only or None)
    estimate = estimate_cost(runs)

    print(f"{len(runs)} runs ({len(CASES) if not only else len(only)} cases x {len(models)} model(s) x {args.repeats} repeat(s)).")
    print(f"Estimated all-in cost: ${estimate:.2f}  (limit ${args.max_usd:.2f})")
    if args.dry_run:
        for case, model, n in runs[:40]:
            print(f"  {case.id:24s} {model:6s} #{n}  [{case.category}]")
        return 0
    if estimate > args.max_usd:
        sys.exit(f"The estimate ${estimate:.2f} is over --max-usd {args.max_usd:.2f}. Lower --repeats or raise the limit on purpose.")

    harness_arn = terraform_output("harness_arn")
    account = boto3.client("sts", region_name=REGION).get_caller_identity()["Account"]
    guardrail = {
        "guardrailIdentifier": f"arn:aws:bedrock:{REGION}:{account}:guardrail/{terraform_output('guardrail_id')}",
        "guardrailVersion": terraform_output("guardrail_version"),
        "trace": "enabled",
    }
    client = boto3.client(
        "bedrock-agentcore", region_name=REGION,
        config=Config(retries={"max_attempts": 6, "mode": "adaptive"}, read_timeout=300),
    )

    results, spent, stopped = [], 0.0, False
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = {}
        for case, model, n in runs:
            futures[pool.submit(invoke_once, client, harness_arn, model, case.prompt, guardrail)] = (case, model, n)
        for done, future in enumerate(as_completed(futures), 1):
            case, model, n = futures[future]
            result = judge(case, future.result(), model, n)
            results.append(result)
            spent += model_cost(result, PRICES)
            layer = "guardrail" if result.guardrail_blocked else "model/tools"
            print(f"[{done}/{len(runs)}] {'PASS' if result.passed else 'FAIL'}  {model:5s} {case.id:24s} #{n}  ({layer}, ${spent:.3f} model cost so far)")
            if spent * 2 > args.max_usd and not stopped:
                stopped = True
                print(f"STOPPING: measured model cost x2 passed ${args.max_usd:.2f}; cancelling the remaining runs.", file=sys.stderr)
                for pending in futures:
                    pending.cancel()

    now = datetime.datetime.now().strftime("%Y-%m-%d-%H%M%S")
    out_dir = ROOT / "evaluation" / "results"
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / f"{now}.json").write_text(json.dumps([asdict(r) for r in results], indent=1), encoding="utf-8")
    report = render_markdown(results, PRICES, title="Evaluation results", generated=now)
    report_path = Path(args.report) if args.report else out_dir / f"{now}.md"
    report_path.write_text(report, encoding="utf-8", newline="\n")
    print("\n" + report)
    print(f"Raw results: evaluation/results/{now}.json   Report: {report_path}")
    errored = sum(1 for r in results if any("error" in d for _, ok, d in r.rules if not ok))
    return 2 if results and errored == len(results) else 0


if __name__ == "__main__":
    sys.exit(main())
