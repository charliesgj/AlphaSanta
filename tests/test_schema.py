from alphasanta.schema import ElfReport, SantaDecision


def test_elf_report_payload_and_brief():
    report = ElfReport(
        elf_id="micro",
        analysis="BTC holding support at 60k.\nFurther upside likely.",
        confidence=0.72,
        evidence={"indicator": "EMA crossover"},
        meta={"token": "BTC/USDT"},
    )
    payload = report.to_agentcard_payload()
    assert payload["elf_id"] == "micro"
    assert "analysis" in payload
    assert payload["confidence"] == 0.72
    assert "indicator" in payload["evidence"]

    brief = report.brief()
    assert "MICRO" in brief
    assert "0.72" in brief

    mission = "Analyze BTC micro structure"
    response_payload = report.to_response_payload(mission)
    assert response_payload["elf_id"] == "micro"
    assert response_payload["mission"] == mission
    assert response_payload["confidence_score"] == 0.72
    assert response_payload["formatted"].startswith("Micro Elf's insight")


def test_santa_decision_serialization():
    decision = SantaDecision(
        verdict="Proceed to share with community.",
        publish=True,
        confidence=0.88,
        rationale=" - Multiple elves confirm momentum.",
        neofs_object_id="abc123",
        neofs_link="https://gateway.neofs.example/abc123",
        meta={"token": "BTC/USDT"},
    )
    payload = decision.to_dict()
    assert payload["publish"] is True
    assert payload["confidence"] == 0.88
    assert payload["neofs_object_id"] == "abc123"
    assert payload["neofs_link"].endswith("abc123")
