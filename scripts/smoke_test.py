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

KB_RETRIEVE_FN = f"{PROJECT}-kb-retrieve"
# (question, title of the document that should be among the top three answers)
KB_QUESTIONS = [
    ("How should a hospital think about HIPAA when moving patient data to AWS?", "Using AWS for HIPAA workloads"),
    ("What are the options for disaster recovery in the cloud?", "Disaster recovery strategies on AWS"),
    ("Which storage class suits a huge media archive that is rarely read?", "Amazon S3 storage classes and lifecycle"),
    ("Can we migrate our mainframe applications to AWS?", "Mainframe modernization on AWS: patterns and availability"),
    ("How do we move a large VMware estate without rewriting applications?", "Amazon Elastic VMware Service (Amazon EVS)"),
]

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

    print(f"kb_retrieve ({KB_RETRIEVE_FN})")
    for question, expected_title in KB_QUESTIONS:
        # No max_results: the agent will get the Lambda's default number of passages and read them all,
        # so that is the honest thing to test. (Semantic search can rank a close second-best document higher.)
        answer = invoke(client, KB_RETRIEVE_FN, {"query": question})
        titles = [r.get("title") for r in answer.get("results", [])]
        check(f"default passages for '{question[:48]}' include '{expected_title[:34]}'", expected_title in titles, titles)
    sample = invoke(client, KB_RETRIEVE_FN, {"query": KB_QUESTIONS[0][0], "max_results": 1})
    top = (sample.get("results") or [{}])[0]
    check("passage carries a source link on an official AWS host", str(top.get("source_url", "")).startswith("https://") and "aws.amazon.com" in str(top.get("source_url")), top)
    check("passage carries a relevance score", isinstance(top.get("score"), float), top)
    serialised = json.dumps(sample)
    check("no S3 locations or bucket names leak into the answer", "s3://" not in serialised and "kb-docs" not in serialised)
    off_topic = invoke(client, KB_RETRIEVE_FN, {"query": "What is the best pizza topping?", "max_results": 1})
    off_score = (off_topic.get("results") or [{"score": 0.0}])[0]["score"]
    on_score = top.get("score", 0.0)
    check(f"an off-topic question scores below an on-topic one ({off_score} < {on_score})", off_score < on_score)
    check("empty query is rejected with an error", invoke(client, KB_RETRIEVE_FN, {"query": " "}).get("found") is False)

    failed = [name for name, ok in results if not ok]
    print(f"\n{len(results) - len(failed)}/{len(results)} checks passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
