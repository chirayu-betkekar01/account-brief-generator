import json

import pytest

from account_profile.handler import MAX_NAME_LENGTH, lambda_handler


def call(event):
    return lambda_handler(event, None)  # the handler does not use the Lambda context


def test_known_company_returns_its_profile(accounts_table):
    result = call({"company_name": "Northwind Logistics"})

    assert result["found"] is True
    assert result["profile"]["industry"] == "Logistics and freight"
    assert "Customer tracking portal" in result["profile"]["workloads"]


def test_partition_key_is_not_leaked_into_the_profile(accounts_table):
    result = call({"company_name": "Northwind Logistics"})

    assert "company" not in result["profile"]
    assert result["profile"]["company_name"] == "Northwind Logistics"


def test_lookup_ignores_case_and_extra_whitespace(accounts_table):
    result = call({"company_name": "  northwind    LOGISTICS "})

    assert result["found"] is True
    assert result["profile"]["company_name"] == "Northwind Logistics"


def test_unknown_company_is_an_explicit_not_found(accounts_table):
    result = call({"company_name": "Acme Rocket Skates"})

    assert result["found"] is False
    assert "profile" not in result  # nothing the model could mistake for data


@pytest.mark.parametrize(
    "event",
    [
        None,
        {},
        {"company_name": ""},
        {"company_name": "   "},
        {"company_name": 42},
        {"company_name": "x" * (MAX_NAME_LENGTH + 1)},
    ],
)
def test_invalid_input_is_rejected_with_an_error(accounts_table, event):
    result = call(event)

    assert result["found"] is False
    assert "error" in result


def test_result_is_json_serialisable_with_plain_numbers(accounts_table):
    result = call({"company_name": "Harborview Health"})

    json.dumps(result)  # raises TypeError if a DynamoDB Decimal slipped through
    assert result["profile"]["employees"] == 6800
    assert isinstance(result["profile"]["employees"], int)
