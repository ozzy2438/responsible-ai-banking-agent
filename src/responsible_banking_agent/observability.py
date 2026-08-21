from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from typing import Any


class JsonLogFormatter(logging.Formatter):
    _FIELDS = ("request_id", "method", "route_group", "status_code", "duration_ms")

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "event": record.getMessage(),
        }
        for field in self._FIELDS:
            value = getattr(record, field, None)
            if value is not None:
                payload[field] = value
        return json.dumps(payload, separators=(",", ":"), sort_keys=True)


def configure_http_logger(log_format: str) -> logging.Logger:
    logger = logging.getLogger("responsible_banking_agent.http")
    formatter: logging.Formatter = (
        JsonLogFormatter()
        if log_format == "json"
        else logging.Formatter("%(levelname)s %(message)s request_id=%(request_id)s")
    )
    if not logger.handlers:
        handler = logging.StreamHandler()
        logger.addHandler(handler)
    for existing_handler in logger.handlers:
        existing_handler.setFormatter(formatter)
    logger.setLevel(logging.INFO)
    logger.propagate = False
    return logger


def route_group(path: str) -> str:
    if path.startswith("/v1/requests/"):
        return "/v1/requests/{id}"
    if path.startswith("/v1/reviewer/escalations/"):
        return "/v1/reviewer/escalations/{id}/actions"
    if path.startswith("/review/escalations/"):
        return "/review/escalations/{id}/actions"
    if path in {
        "/healthz",
        "/readyz",
        "/v1/assist",
        "/v1/reviewer/escalations",
        "/review/escalations",
        "/dev/login",
    }:
        return path
    return "/unmatched"
