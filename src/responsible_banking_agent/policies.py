from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .models import Citation, VerifiedFact


@dataclass(frozen=True)
class PolicySection:
    policy_id: str
    version: str
    section_id: str
    title: str
    text: str
    keywords: tuple[str, ...]

    def as_fact(self) -> VerifiedFact:
        return VerifiedFact(
            label=self.title,
            value=self.text,
            citation=Citation(
                source_type="policy",
                source_id=self.policy_id,
                version=self.version,
                section=self.section_id,
            ),
        )


class PolicyIntegrityError(RuntimeError):
    pass


class PolicyStore:
    def __init__(self, root: Path) -> None:
        self.root = root
        manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
        self.sections: list[PolicySection] = []
        for filename, expected_hash in manifest["files"].items():
            raw = (root / filename).read_bytes()
            if hashlib.sha256(raw).hexdigest() != expected_hash:
                raise PolicyIntegrityError(f"Policy hash mismatch: {filename}")
            document: dict[str, Any] = json.loads(raw)
            self.sections.extend(
                PolicySection(
                    policy_id=document["policy_id"],
                    version=document["version"],
                    section_id=section["section_id"],
                    title=section["title"],
                    text=section["text"],
                    keywords=tuple(section["keywords"]),
                )
                for section in document["sections"]
            )

    def lookup(self, query: str) -> list[VerifiedFact]:
        lowered = query.lower()
        scored = [
            (sum(keyword in lowered for keyword in section.keywords), section)
            for section in self.sections
        ]
        matches = [section.as_fact() for score, section in scored if score > 0]
        return matches[:3]
