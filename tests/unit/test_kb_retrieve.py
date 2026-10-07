import json

import boto3
import pytest
from botocore.stub import Stubber

from kb_retrieve import handler

KB_ID = "ABCDE12345"


def result(text, score, **metadata):
    return {
        "content": {"type": "TEXT", "text": text},
        "location": {"type": "S3", "s3Location": {"uri": "s3://some-bucket/docs/secret-internal-name.md"}},
        "metadata": {"x-amz-bedrock-kb-chunk-id": "internal", **metadata},
        "score": score,
    }


@pytest.fixture
def stubbed(monkeypatch):
    """The real bedrock-agent-runtime client, with its network replaced by canned answers."""
    monkeypatch.setenv("KNOWLEDGE_BASE_ID", KB_ID)
    client = boto3.client("bedrock-agent-runtime", region_name="us-east-1")
    monkeypatch.setattr(handler, "_client", lambda: client)
    with Stubber(client) as stub:
        yield stub


def call(event):
    return handler.lambda_handler(event, None)  # the handler does not use the Lambda context


def expected_request(query, count=handler.DEFAULT_RESULTS):
    return {
        "knowledgeBaseId": KB_ID,
        "retrievalQuery": {"text": query},
        "retrievalConfiguration": {"vectorSearchConfiguration": {"numberOfResults": count}},
    }


def test_returns_passages_with_source_links(stubbed):
    stubbed.add_response(
        "retrieve",
        {
            "retrievalResults": [
                result(
                    "HIPAA summary text",
                    0.8123456,
                    title="Using AWS for HIPAA workloads",
                    topic="compliance",
                    source_url="https://aws.amazon.com/compliance/hipaa-compliance/",
                    checked_on="2026-10-07",
                )
            ]
        },
        expected_request("hipaa"),
    )

    out = call({"query": "hipaa"})

    assert out["found"] is True
    assert out["results"] == [
        {
            "text": "HIPAA summary text",
            "score": 0.8123,
            "title": "Using AWS for HIPAA workloads",
            "topic": "compliance",
            "source_url": "https://aws.amazon.com/compliance/hipaa-compliance/",
            "checked_on": "2026-10-07",
        }
    ]


def test_internal_locations_and_ids_are_not_leaked(stubbed):
    stubbed.add_response("retrieve", {"retrievalResults": [result("text", 0.5, title="T")]}, expected_request("q"))

    serialised = json.dumps(call({"query": "q"}))

    assert "secret-internal-name" not in serialised
    assert "s3://" not in serialised
    assert "chunk-id" not in serialised


def test_missing_metadata_becomes_none_not_a_crash(stubbed):
    stubbed.add_response("retrieve", {"retrievalResults": [result("text", 0.5)]}, expected_request("q"))

    passage = call({"query": "q"})["results"][0]

    assert passage["source_url"] is None
    assert passage["title"] is None


def test_no_matches_is_an_explicit_not_found(stubbed):
    stubbed.add_response("retrieve", {"retrievalResults": []}, expected_request("q"))

    assert call({"query": "q"}) == {"found": False, "results": []}


def test_query_is_trimmed_before_it_is_sent(stubbed):
    stubbed.add_response("retrieve", {"retrievalResults": []}, expected_request("disaster recovery"))

    call({"query": "  disaster recovery \n"})

    stubbed.assert_no_pending_responses()


@pytest.mark.parametrize(
    "max_results, sent",
    [(None, handler.DEFAULT_RESULTS), (1, 1), (3, 3), (0, 1), (-5, 1), (100, handler.MAX_RESULTS), ("3", handler.DEFAULT_RESULTS), (True, handler.DEFAULT_RESULTS)],
)
def test_result_count_is_clamped_to_a_safe_range(stubbed, max_results, sent):
    stubbed.add_response("retrieve", {"retrievalResults": []}, expected_request("q", sent))

    call({"query": "q", "max_results": max_results})

    stubbed.assert_no_pending_responses()


@pytest.mark.parametrize(
    "event",
    [None, {}, {"query": ""}, {"query": "   "}, {"query": 42}, {"query": "x" * (handler.MAX_QUERY_LENGTH + 1)}],
)
def test_invalid_input_is_rejected_before_any_aws_call(stubbed, event):
    out = call(event)  # the stubber has no queued response, so any AWS call would raise

    assert out["found"] is False
    assert "error" in out


def test_an_aws_error_becomes_a_clean_message_without_details(stubbed):
    stubbed.add_client_error("retrieve", service_error_code="ThrottlingException", http_status_code=429)

    out = call({"query": "q"})

    assert out["found"] is False
    assert "lookup failed" in out["error"]
    assert "Throttling" not in out["error"]
