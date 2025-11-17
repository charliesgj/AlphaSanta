import pytest

pytest.importorskip("pydantic")

from alphasanta.schema import SantaDecision
from alphasanta.services.dissemination import DisseminationService


def test_broadcast_formatting_includes_confidence_and_link():
    decision = SantaDecision(
        verdict="Share alpha with the elves!",
        publish=True,
        confidence=0.66,
        rationale="- Strong confluence",
        neofs_link="https://gateway/object",
    )
    message = DisseminationService._format_broadcast(decision)
    assert "0.66" in message
    assert "gateway/object" in message
    assert "Share alpha" in message
