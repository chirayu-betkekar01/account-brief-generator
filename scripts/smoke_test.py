"""Smoke test for the deployed action Lambdas (Phase 2).

Invokes the real functions in AWS and checks the answers. Unit tests prove the code is right;
this proves the DEPLOYMENT is right: the zip, the IAM role, the DynamoDB seed rows, the
environment variable and the log group all have to work together.

Needs AWS credentials (AWS_PROFILE) and `make apply` to have run. Cost: a handful of Lambda
invocations, far inside the free tier. Exit code 0 only if every check passes.
"""

import json
import os
import sys

import boto3

PROJECT = os.environ.get("PROJECT", "discovery-brief-agent")
REGION = os.environ.get("AWS_REGION", "us-east-1")
ACCOUNT_PROFILE_FN = f"{PROJECT}-account-profile"
ROI_ESTIMATOR_FN = f"{PROJECT}-roi-estimator"

ROI_EVENT = {
    "on_prem_annual_cost_usd": 3_900_000,
    "servers": 340,
    "storage_tb": 180,
    "annual_growth_pct": 12,
}


def invoke(client, function_name, event):
    response = client.invoke(FunctionName=function_name, Payload=json.dumps(event).encode())
    body = json.loads(response["Payload"].read())
    if "FunctionError" in response:
        raise RuntimeError(f"{function_name} crashed: {body}")
    return body


def main():
    client = boto3.client("lambda", region_name=REGION)
    results = []

    def check(name, condition, detail=""):
        results.append((name, bool(condition)))
        print(f"  {'PASS' if condition else 'FAIL'}  {name}" + (f"  ({detail})" if detail and not condition else ""))

    print(f"account_profile ({ACCOUNT_PROFILE_FN})")
    found = invoke(client, ACCOUNT_PROFILE_FN, {"company_name": "Northwind Logistics"})
    check("known company is found", found.get("found") is True, found)
    profile = found.get("profile", {})
    check("profile has plain-number employees (4200)", profile.get("employees") == 4200, profile.get("employees"))
    check("partition key is not leaked", "company" not in profile)
    check("workloads come back as a list", isinstance(profile.get("workloads"), list) and profile["workloads"])

    messy = invoke(client, ACCOUNT_PROFILE_FN, {"company_name": "  harborview   HEALTH "})
    check("lookup ignores case and extra spaces", messy.get("found") is True, messy)

    unknown = invoke(client, ACCOUNT_PROFILE_FN, {"company_name": "Acme Rocket Skates"})
    check("unknown company is an explicit not-found", unknown.get("found") is False and "profile" not in unknown, unknown)

    bad = invoke(client, ACCOUNT_PROFILE_FN, {})
    check("missing input is rejected with an error", bad.get("found") is False and "error" in bad, bad)

    print(f"roi_estimator ({ROI_ESTIMATOR_FN})")
    roi = invoke(client, ROI_ESTIMATOR_FN, ROI_EVENT)
    check("valid input is accepted", roi.get("ok") is True, roi)
    check("three yearly rows", len(roi.get("years", [])) == 3)
    check("assumptions are surfaced with a rationale", all(a.get("rationale") for a in roi.get("assumptions", {}).values()) and roi.get("assumptions"))
    check("totals include roi_pct", "roi_pct" in roi.get("totals", {}))

    invalid = invoke(client, ROI_ESTIMATOR_FN, {**ROI_EVENT, "servers": 0})
    check("invalid input is a clean error naming the field", invalid.get("ok") is False and "servers" in invalid.get("error", ""), invalid)

    failed = [name for name, ok in results if not ok]
    print(f"\n{len(results) - len(failed)}/{len(results)} checks passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
