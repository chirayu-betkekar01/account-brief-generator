"""account_profile Lambda: return one synthetic company profile.

Called by the AgentCore Gateway. For a Lambda target the event IS the tool's
arguments, so the agent calling account_profile(company_name="...") arrives
here as {"company_name": "..."}. Whatever we return goes back to the model as
the tool result.
"""

import logging
import os
import re
from decimal import Decimal
from functools import lru_cache

import boto3

logger = logging.getLogger()
logger.setLevel(logging.INFO)

MAX_NAME_LENGTH = 100


def normalise(name: str) -> str:
    """Turn what the user typed into the table's partition key."""
    return re.sub(r"\s+", " ", name.strip()).lower()


@lru_cache(maxsize=1)
def _table():
    # Built once per Lambda container and reused by later invocations,
    # which is faster than reconnecting on every call.
    return boto3.resource("dynamodb").Table(os.environ["TABLE_NAME"])


def _jsonable(value):
    """boto3 returns DynamoDB numbers as Decimal, which json.dumps rejects."""
    if isinstance(value, Decimal):
        return int(value) if value == value.to_integral_value() else float(value)
    if isinstance(value, list):
        return [_jsonable(v) for v in value]
    if isinstance(value, dict):
        return {k: _jsonable(v) for k, v in value.items()}
    return value


def lambda_handler(event, context):
    name = event.get("company_name") if isinstance(event, dict) else None
    if not isinstance(name, str) or not name.strip() or len(name) > MAX_NAME_LENGTH:
        logger.warning("rejected invalid company_name input")
        return {
            "found": False,
            "error": f"company_name must be a non-empty string of at most {MAX_NAME_LENGTH} characters.",
        }

    key = normalise(name)
    item = _table().get_item(Key={"company": key}).get("Item")
    logger.info("account lookup key=%r found=%s", key, item is not None)

    # An explicit "not found" matters: with no answer to read, a model may invent one.
    if item is None:
        return {"found": False, "message": "No account profile exists for that company name."}

    item.pop("company")  # the partition key is plumbing, not part of the profile
    return {"found": True, "profile": _jsonable(item)}
