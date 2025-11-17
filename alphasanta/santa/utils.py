"""Utility helpers for Santa agent logic."""

from __future__ import annotations

from typing import List, Optional

from alphasanta.schema import UserLetter, ElfReport, SantaDecision


def parse_santa_response(
    assistant_response: str,
    user_letter: UserLetter,
    reports: List[ElfReport],
) -> SantaDecision:
    """Parse Santa's formatted LLM response into a structured decision."""
    verdict = ""
    confidence: Optional[float] = None
    publish = False
    rationale_lines: List[str] = []

    for line in assistant_response.splitlines():
        normalized = line.strip()
        if not normalized:
            continue
        lower = normalized.lower()
        if lower.startswith("verdict:"):
            verdict = normalized.split(":", 1)[1].strip()
        elif lower.startswith("confidence:"):
            try:
                confidence = float(normalized.split(":", 1)[1].strip())
            except Exception:
                confidence = None
        elif lower.startswith("publish:"):
            publish_value = normalized.split(":", 1)[1].strip().lower()
            publish = publish_value in {"yes", "true", "y"}
        elif lower.startswith("-"):
            rationale_lines.append(normalized[1:].strip())

    rationale = "\n".join(rationale_lines) if rationale_lines else None
    meta = {
        "token": user_letter.token,
        "source": user_letter.source,
        "elf_reports": [report.to_agentcard_payload() for report in reports],
    }

    return SantaDecision(
        verdict=verdict or assistant_response,
        confidence=confidence,
        publish=publish,
        rationale=rationale,
        meta=meta,
    )
