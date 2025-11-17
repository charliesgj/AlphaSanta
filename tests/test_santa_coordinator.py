import asyncio
from dataclasses import dataclass

from alphasanta.orchestrator.elf_runner import ElfRunner
from alphasanta.schema import UserLetter, ElfReport
from alphasanta.santa.tracing import WorkflowTracer
from alphasanta.transports import LocalElfTransport


@dataclass
class StubElf:
    elf_id: str
    response: str
    confidence: float

    async def analyze_input(self, letter: UserLetter) -> ElfReport:
        return ElfReport(
            elf_id=self.elf_id,
            analysis=f"{self.elf_id}:{self.response}",
            confidence=self.confidence,
            meta={"token": letter.token},
        )

    def clear(self) -> None:
        pass


def test_local_transport_runs_elves():
    runners = {
        "micro": ElfRunner(lambda: StubElf("micro", "bullish", 0.8)),  # type: ignore[arg-type]
        "mood": ElfRunner(lambda: StubElf("mood", "neutral", 0.6)),  # type: ignore[arg-type]
    }
    transport = LocalElfTransport(runners)
    letter = UserLetter(token="BTC/USDT", thesis="ETF narrative")
    tracer = WorkflowTracer()

    async def gather_reports():
        return await asyncio.gather(
            *[transport.fetch_report(elf_id, letter, tracer) for elf_id in transport.elf_ids]
        )

    reports = asyncio.run(gather_reports())
    assert {report.elf_id for report in reports} == {"micro", "mood"}
    assert any(event.stage == "micro.dispatch" and event.status == "success" for event in tracer.events)
