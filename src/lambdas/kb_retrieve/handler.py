"""kb_retrieve Lambda: search the knowledge base and return passages with their source links.

Called by the AgentCore Gateway; the event IS the tool's arguments, e.g.
{"query": "How should a hospital approach HIPAA on AWS?", "max_results": 3}.

Why a Lambda: the Gateway's built-in knowledge-base connector works only with Bedrock *Managed*
Knowledge Bases, a different (and dearer) product from the S3 Vectors knowledge base we use.

Its IAM role may call Retrieve on exactly one knowledge base and nothing else.
"""

import logging
import os
from functools import lru_cache

import boto3
from botocore.exceptions import BotoCoreError, ClientError

logger = logging.getLogger()
logger.setLevel(logging.INFO)

MAX_QUERY_LENGTH = 500
DEFAULT_RESULTS = 4
MAX_RESULTS = 8
# Metadata attributes we return; everything else Bedrock attaches (S3 locations, chunk IDs) stays internal.
PUBLIC_METADATA = ("title", "topic", "source_url", "checked_on")


@lru_cache(maxsize=1)
def _client():
    # Built once per warm container and reused.
    return boto3.client("bedrock-agent-runtime")


def _clamp_results(value):
    if isinstance(value, bool) or not isinstance(value, int):
        return DEFAULT_RESULTS
    return max(1, min(value, MAX_RESULTS))


def lambda_handler(event, context):
    event = event if isinstance(event, dict) else {}
    query = event.get("query")
    if not isinstance(query, str) or not query.strip() or len(query) > MAX_QUERY_LENGTH:
        logger.warning("rejected invalid query input")
        return {
            "found": False,
            "error": f"query must be a non-empty string of at most {MAX_QUERY_LENGTH} characters.",
        }

    try:
        response = _client().retrieve(
            knowledgeBaseId=os.environ["KNOWLEDGE_BASE_ID"],
            retrievalQuery={"text": query.strip()},
            retrievalConfiguration={
                "vectorSearchConfiguration": {"numberOfResults": _clamp_results(event.get("max_results"))}
            },
        )
    except (ClientError, BotoCoreError) as error:
        # The detail goes to the logs; the agent only needs to know the lookup failed.
        logger.error("knowledge base retrieve failed: %s", error)
        return {"found": False, "error": "The knowledge base lookup failed. Say so rather than guessing."}

    results = []
    for item in response.get("retrievalResults", []):
        metadata = item.get("metadata", {})
        results.append(
            {
                "text": item.get("content", {}).get("text", ""),
                "score": round(float(item.get("score", 0.0)), 4),
                **{key: metadata.get(key) for key in PUBLIC_METADATA},
            }
        )

    logger.info("kb retrieve returned %d passages", len(results))
    return {"found": bool(results), "results": results}
