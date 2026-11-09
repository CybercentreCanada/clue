"""CWE-862 (Missing Authorization) regression harness for query results."""

import pytest
from clue.models.network import QueryResult


@pytest.mark.parametrize(
    "context", [None, {}, {"other": True}, {"user": None}, {"user": {}}]
)
def test_cwe_862_query_result_requires_authorized_clearance(context):
    """Deny missing clearance and filter results above an authenticated user's clearance."""
    payload = {
        "type": "ipv4",
        "value": "1.1.1.1",
        "source": "test",
        "items": [
            {"classification": "TLP:CLEAR"},
            {
                "classification": "TLP:AMBER+STRICT",
                "raw_data": "RESTRICTED_TEST_MARKER",
            },
        ],
    }

    assert QueryResult.model_validate(payload).items == []
    assert QueryResult(**payload).items == []
    assert QueryResult.model_validate(payload, context=context).items == []

    result = QueryResult.model_validate(
        payload, context={"user": {"classification": "TLP:CLEAR"}}
    )

    assert [item.classification for item in result.items] == ["TLP:CLEAR"]
    assert "RESTRICTED_TEST_MARKER" not in result.model_dump_json()
