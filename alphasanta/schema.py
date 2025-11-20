"""
Shared data structures for AlphaSanta agents.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class ElfReport:
    """
    Standardized payload each elf returns to Santa and AgentCard.

    Attributes:
        elf_id: Identifier for the producing elf (e.g., "micro", "mood").
        analysis: Human-readable summary or recommendation.
        confidence: Float in [0, 1] indicating the elf's confidence.
        rationale: Optional structured reasoning or bullet list.
        evidence: Tool outputs, chart data, citations, etc.
        meta: Additional metadata (timestamps, run configs, token symbol).
    """

    elf_id: str
    analysis: str
    confidence: Optional[float] = None
    rationale: Optional[str] = None
    evidence: Dict[str, Any] = field(default_factory=dict)
    meta: Dict[str, Any] = field(default_factory=dict)

    def to_agentcard_payload(self) -> Dict[str, Any]:
        """Format the report for the AgentCard SDK."""
        payload: Dict[str, Any] = {
            "elf_id": self.elf_id,
            "analysis": self.analysis,
            "evidence": self.evidence,
            "meta": self.meta,
        }

        if self.confidence is not None:
            payload["confidence"] = float(self.confidence)
        if self.rationale:
            payload["rationale"] = self.rationale
        return payload

    def to_response_payload(self, mission: str | None = None) -> Dict[str, Any]:
        """Produce the canonical Elf's response JSON."""
        confidence = None
        if isinstance(self.confidence, (int, float)):
            confidence = float(self.confidence)

        formatted_insight = self.analysis.strip()
        formatted = f"{self.elf_id.title()}Elf insight: {formatted_insight}"

        return {
            "summary": {
                "insight": formatted_insight,
                "formatted": formatted,
                "confidence": confidence,
            },
            "report": {
                "analysis": self.analysis,
                "evidence": self.evidence,
                "meta": self.meta,
                "confidence": confidence,
            },
        }

    def brief(self) -> str:
        """Return a one-line summary for Santa."""
        confidence_txt = (
            f" (confidence={self.confidence:.2f})"
            if isinstance(self.confidence, (int, float))
            else ""
        )
        if not self.analysis:
            headline = ""
        else:
            lines = [line.strip() for line in self.analysis.splitlines() if line.strip()]
            if not lines:
                headline = ""
            else:
                snippet = lines[0]
                for line in lines[1:]:
                    candidate = f"{snippet} {line}"
                    if len(candidate) > 200:
                        break
                    snippet = candidate
                headline = snippet
                if len(self.analysis) > len(headline):
                    headline = headline.rstrip() + " …"

        return f"{self.elf_id.upper()}: {headline}{confidence_txt}"


@dataclass
class UserLetter:
    """
    Normalized "letter" submitted by a user to Santa.
    """

    token: str
    thesis: str
    user_id: str
    source: str = "community"  # community, alpha, automation, etc.
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SantaDecision:
    """
    Final decision produced by Santa after digesting elf reports.
    """

    verdict: str
    publish: bool
    confidence: Optional[float] = None
    rationale: Optional[str] = None
    neofs_object_id: Optional[str] = None
    neofs_link: Optional[str] = None
    meta: Dict[str, Any] = field(default_factory=dict)
    source: str = "community"

    def to_dict(self) -> Dict[str, Any]:
        """Serialize decision for logging or AgentCard."""
        payload: Dict[str, Any] = {
            "verdict": self.verdict,
            "publish": self.publish,
            "meta": self.meta,
            "source": self.source,
        }
        if self.confidence is not None:
            payload["confidence"] = float(self.confidence)
        if self.rationale:
            payload["rationale"] = self.rationale
        if self.neofs_object_id:
            payload["neofs_object_id"] = self.neofs_object_id
        if self.neofs_link:
            payload["neofs_link"] = self.neofs_link
        return payload
