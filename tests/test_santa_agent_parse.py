from alphasanta.schema import UserLetter, ElfReport
from alphasanta.santa import parse_santa_response


def test_parse_santa_response():
    response = """Verdict: Gift the alpha to the community.
Confidence: 0.91
Publish: yes
Rationale:
- MicroElf sees strong trend
- MoodElf reports positive buzz
"""
    letter = UserLetter(token="BTC/USDT", thesis="ETF narrative")
    reports = [
        ElfReport(elf_id="micro", analysis="Strong trend", confidence=0.8),
        ElfReport(elf_id="mood", analysis="Positive sentiment", confidence=0.7),
    ]

    decision = parse_santa_response(response, letter, reports)
    assert decision.publish is True
    assert decision.confidence == 0.91
    assert "Gift the alpha" in decision.verdict
    assert decision.meta["elf_reports"][0]["elf_id"] == "micro"
