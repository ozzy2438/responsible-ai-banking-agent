import json
import logging

from responsible_banking_agent.observability import JsonLogFormatter, route_group


def test_json_log_formatter_has_allowlisted_metadata_only() -> None:
    record = logging.LogRecord(
        name="responsible_banking_agent.http",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="http_request",
        args=(),
        exc_info=None,
    )
    record.request_id = "11111111-1111-4111-8111-111111111111"
    record.method = "POST"
    record.route_group = "/v1/assist"
    record.status_code = 200
    record.duration_ms = 1.5
    payload = json.loads(JsonLogFormatter().format(record))
    assert set(payload) == {
        "timestamp",
        "level",
        "event",
        "request_id",
        "method",
        "route_group",
        "status_code",
        "duration_ms",
    }
    assert "authorization" not in payload
    assert "message_body" not in payload


def test_route_group_removes_customer_supplied_identifiers() -> None:
    assert route_group("/v1/requests/customer-value") == "/v1/requests/{id}"
    assert route_group("/unknown/customer-value") == "/unmatched"
