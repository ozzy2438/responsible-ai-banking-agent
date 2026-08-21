#!/usr/bin/env python3
"""Exercise the packaged Docker Compose demo through its loopback HTTP surface."""

from __future__ import annotations

import argparse
import json
import re
from http.cookiejar import CookieJar
from typing import Any
from urllib.parse import urlencode
from urllib.request import HTTPCookieProcessor, Request, build_opener
from uuid import uuid4

ALICE_ACCOUNT = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"


class Session:
    def __init__(self, base_url: str) -> None:
        self.base_url = base_url.rstrip("/")
        self.cookies = CookieJar()
        self.opener = build_opener(HTTPCookieProcessor(self.cookies))

    def request(
        self,
        path: str,
        *,
        method: str = "GET",
        json_body: dict[str, Any] | None = None,
        form: dict[str, str] | None = None,
        headers: dict[str, str] | None = None,
    ) -> tuple[int, str]:
        request_headers = dict(headers or {})
        body: bytes | None = None
        if json_body is not None:
            body = json.dumps(json_body).encode()
            request_headers["Content-Type"] = "application/json"
        elif form is not None:
            body = urlencode(form).encode()
            request_headers["Content-Type"] = "application/x-www-form-urlencoded"
        response = self.opener.open(
            Request(
                f"{self.base_url}{path}",
                data=body,
                headers=request_headers,
                method=method,
            ),
            timeout=10,
        )
        return response.status, response.read().decode()

    def json_request(self, path: str, **kwargs: Any) -> dict[str, Any]:
        status, body = self.request(path, **kwargs)
        assert status == 200, f"{path} returned {status}: {body}"
        parsed = json.loads(body)
        assert isinstance(parsed, dict)
        return parsed


def login(session: Session, alias: str) -> None:
    status, _ = session.request(
        "/dev/login",
        method="POST",
        json_body={"alias": alias},
    )
    assert status == 204, f"local demo login for {alias} returned {status}"


def csrf_from(html: str) -> str:
    match = re.search(r'name="csrf" value="([^"]+)"', html)
    assert match, "review page did not contain a CSRF token"
    return match.group(1)


def run(base_url: str) -> None:
    public = Session(base_url)
    assert public.json_request("/healthz") == {"status": "ok"}
    assert public.json_request("/readyz") == {"status": "ready"}
    landing_status, landing = public.request("/")
    assert landing_status == 200
    assert "Alice Example" in landing and "/static/landing.js" in landing
    script_status, script = public.request("/static/landing.js")
    assert script_status == 200 and "/dev/login" in script

    customer = Session(base_url)
    login(customer, "alice")
    demo_status, demo_page = customer.request("/demo")
    assert demo_status == 200
    assert ALICE_ACCOUNT in demo_page and "/static/demo.js" in demo_page
    demo_script_status, demo_script = customer.request("/static/demo.js")
    assert demo_script_status == 200 and "/v1/assist" in demo_script
    medium = customer.json_request(
        "/v1/assist",
        method="POST",
        headers={"Idempotency-Key": f"compose-medium-{uuid4()}"},
        json_body={"message": "What is my balance?", "account_id": ALICE_ACCOUNT},
    )
    assert medium["risk_level"] == "MEDIUM"
    assert medium["disposition"] == "answered"
    assert medium["citations"]

    high = customer.json_request(
        "/v1/assist",
        method="POST",
        headers={"Idempotency-Key": f"compose-high-{uuid4()}"},
        json_body={
            "message": "I am in financial hardship and cannot pay this month.",
            "account_id": None,
        },
    )
    assert high["risk_level"] == "HIGH"
    assert high["disposition"] == "escalated"
    escalation_id = str(high["escalation_id"])

    reviewer = Session(base_url)
    login(reviewer, "reviewer")
    queue_status, queue = reviewer.request("/review/escalations")
    assert queue_status == 200 and escalation_id in queue
    reviewer.request(
        f"/review/escalations/{escalation_id}/actions",
        method="POST",
        form={
            "action": "route",
            "route": "hardship",
            "reason": "Route synthetic demo case to hardship",
            "csrf": csrf_from(queue),
        },
    )
    routed = reviewer.request("/v1/reviewer/escalations")[1]
    routed_items = json.loads(routed)
    routed_case = next(item for item in routed_items if item["id"] == escalation_id)
    assert routed_case["status"] == "routed"
    assert routed_case["route"] == "hardship"

    _, routed_queue = reviewer.request("/review/escalations")
    reviewer.request(
        f"/review/escalations/{escalation_id}/actions",
        method="POST",
        form={
            "action": "close",
            "route": "",
            "reason": "Close completed synthetic demo review",
            "csrf": csrf_from(routed_queue),
        },
    )
    _, closed_queue = reviewer.request("/review/escalations")
    assert escalation_id not in closed_queue


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    args = parser.parse_args()
    run(args.base_url)
    print("Compose demo smoke passed: customer answer, escalation, route, and close")


if __name__ == "__main__":
    main()
