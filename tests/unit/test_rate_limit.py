from responsible_banking_agent.rate_limit import InMemoryRateLimiter, hash_rate_limit_subject


def test_in_memory_rate_limit_is_bounded_and_resets_by_window() -> None:
    now = [120.0]
    limiter = InMemoryRateLimiter(requests=2, window_seconds=60, clock=lambda: now[0])
    assert limiter.allow("a" * 64, "/v1/assist")
    assert limiter.allow("a" * 64, "/v1/assist")
    assert not limiter.allow("a" * 64, "/v1/assist")
    now[0] = 180.0
    assert limiter.allow("a" * 64, "/v1/assist")


def test_rate_limit_subject_is_keyed_and_does_not_expose_input() -> None:
    digest = hash_rate_limit_subject("k" * 32, "ip:203.0.113.7")
    assert len(digest) == 64
    assert "203.0.113.7" not in digest
    assert digest != hash_rate_limit_subject("z" * 32, "ip:203.0.113.7")
