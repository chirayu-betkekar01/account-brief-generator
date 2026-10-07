import json
from decimal import Decimal
from pathlib import Path

import boto3
import pytest
from moto import mock_aws

from account_profile import handler as account_profile_handler

ACCOUNTS_FILE = Path(__file__).resolve().parents[1] / "data" / "accounts.json"


@pytest.fixture(autouse=True)
def isolated_aws_env(monkeypatch):
    """Make it impossible for a unit test to reach the real AWS account."""
    monkeypatch.delenv("AWS_PROFILE", raising=False)
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "testing")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "testing")
    monkeypatch.setenv("AWS_DEFAULT_REGION", "us-east-1")
    monkeypatch.setenv("AWS_EC2_METADATA_DISABLED", "true")


@pytest.fixture(scope="session")
def accounts_text() -> str:
    return ACCOUNTS_FILE.read_text(encoding="utf-8")


@pytest.fixture(scope="session")
def accounts(accounts_text) -> list[dict]:
    # parse_float=Decimal because boto3 refuses Python floats when writing to DynamoDB.
    return json.loads(accounts_text, parse_float=Decimal)["accounts"]


@pytest.fixture
def accounts_table(monkeypatch, accounts):
    """A pretend DynamoDB table (moto) seeded with the same data Terraform will load."""
    with mock_aws():
        table = boto3.resource("dynamodb").create_table(
            TableName="test-accounts",
            KeySchema=[{"AttributeName": "company", "KeyType": "HASH"}],
            AttributeDefinitions=[{"AttributeName": "company", "AttributeType": "S"}],
            BillingMode="PAY_PER_REQUEST",
        )
        for account in accounts:
            key = account_profile_handler.normalise(account["company_name"])
            table.put_item(Item={"company": key, **account})
        monkeypatch.setenv("TABLE_NAME", "test-accounts")
        account_profile_handler._table.cache_clear()
        yield table
        account_profile_handler._table.cache_clear()
