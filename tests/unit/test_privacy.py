from responsible_banking_agent.privacy import redact_sensitive


def test_redacts_labelled_secrets_and_valid_card() -> None:
    result = redact_sensitive("password is hunter2, PIN: 1234, CVV=999, card 4111 1111 1111 1111")
    assert "hunter2" not in result.text
    assert "1234" not in result.text
    assert "999" not in result.text
    assert "4111" not in result.text
    assert set(result.categories) == {"PASSWORD", "PIN", "CVV", "CARD"}


def test_does_not_redact_non_card_numeric_fact() -> None:
    result = redact_sensitive("The synthetic balance is 1234 dollars")
    assert result.text == "The synthetic balance is 1234 dollars"
    assert not result.redacted
