"""Start a knowledge base ingestion job and wait for it to finish.

Terraform creates the knowledge base and uploads the documents, but "read the documents, embed
them and store the vectors" is a separate job that Terraform cannot start. This script starts it,
polls until it ends, and prints the counts. Exit code 0 only if every document was indexed.

Needs AWS credentials (AWS_PROFILE) and `make apply` to have run. Cost: embedding the whole corpus
(about 4,000 tokens) is a small fraction of a cent.
"""

import json
import os
import subprocess
import sys
import time

import boto3

REGION = os.environ.get("AWS_REGION", "us-east-1")
POLL_SECONDS = 5
TIMEOUT_SECONDS = 600


def terraform_output(name):
    result = subprocess.run(
        ["terraform", "-chdir=infra/main", "output", "-raw", name],
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout.strip()


def main():
    knowledge_base_id = terraform_output("knowledge_base_id")
    data_source_id = terraform_output("data_source_id")
    expected_documents = int(terraform_output("kb_documents"))

    client = boto3.client("bedrock-agent", region_name=REGION)
    job = client.start_ingestion_job(knowledgeBaseId=knowledge_base_id, dataSourceId=data_source_id)["ingestionJob"]
    job_id = job["ingestionJobId"]
    print(f"started ingestion job {job_id}")

    deadline = time.time() + TIMEOUT_SECONDS
    while True:
        job = client.get_ingestion_job(
            knowledgeBaseId=knowledge_base_id, dataSourceId=data_source_id, ingestionJobId=job_id
        )["ingestionJob"]
        status = job["status"]
        print(f"  status: {status}")
        if status in ("COMPLETE", "FAILED", "STOPPED"):
            break
        if time.time() > deadline:
            print("timed out waiting for the ingestion job")
            return 1
        time.sleep(POLL_SECONDS)

    stats = job.get("statistics", {})
    print(json.dumps(stats, indent=2))
    for reason in job.get("failureReasons", []):
        print("failure:", reason)

    scanned = stats.get("numberOfDocumentsScanned", 0)
    indexed = stats.get("numberOfNewDocumentsIndexed", 0) + stats.get("numberOfModifiedDocumentsIndexed", 0)
    failed = stats.get("numberOfDocumentsFailed", 0)
    ok = status == "COMPLETE" and failed == 0 and scanned >= expected_documents
    print(
        f"\n{'OK' if ok else 'PROBLEM'}: {status}; scanned {scanned} of {expected_documents} documents, "
        f"{indexed} newly indexed or changed, {failed} failed"
    )
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
