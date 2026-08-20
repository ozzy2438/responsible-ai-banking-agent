from pathlib import Path

import pytest

from responsible_banking_agent.policies import PolicyIntegrityError, PolicyStore


def test_policy_lookup_has_versioned_citation() -> None:
    store = PolicyStore(Path("policies"))
    facts = store.lookup("What are the branch opening hours?")
    assert facts
    assert facts[0].citation.source_id == "POL-GENERAL-001"
    assert facts[0].citation.version == "1.0.0"


def test_policy_manifest_detects_change(tmp_path: Path) -> None:
    (tmp_path / "manifest.json").write_text('{"files":{"bad.json":"0000"}}', encoding="utf-8")
    (tmp_path / "bad.json").write_text("{}", encoding="utf-8")
    with pytest.raises(PolicyIntegrityError):
        PolicyStore(tmp_path)
