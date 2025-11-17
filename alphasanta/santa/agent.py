"""
SantaAgent – final decision-maker that consumes elf reports.
"""

from __future__ import annotations

import asyncio
from typing import List, Optional, Sequence

from pydantic import ConfigDict

from spoon_ai.agents.toolcall import ToolCallAgent
from spoon_ai.chat import ChatBot
from spoon_ai.tools import ToolManager

from ..agents.alpha import AlphaElf
from ..schema import UserLetter, CouncilResult, ElfReport, SantaDecision
from ..services import DisseminationService, PersistenceService, TurnkeyService
from ..transports import ElfTransport
from .tracing import WorkflowTracer
class SantaAgent(ToolCallAgent):
    """
    Santa digests reports, requests clarifications, and publishes final verdicts.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True, extra="allow")

    name: str = "SantaAgent"
    description: str = "Jolly arbiter synthesizing elf intel into alpha gifts."
    system_prompt: str = (
        "You are Santa, the benevolent but discerning leader of AlphaSanta.\n"
        "You receive analyses from MicroElf (technical), MoodElf (sentiment), "
        "MacroElf (macro trends), and optionally AlphaElf (proprietary scouts).\n"
        "Your job is to:\n"
        "1. Synthesize their perspectives into a cohesive verdict.\n"
        "2. Assign a final confidence score [0-1].\n"
        "3. Decide whether the community should receive this alpha (Publish: yes/no).\n"
        "4. Provide a playful but professional summary referencing each elf.\n"
        "\n"
        "Output format (strict):\n"
        "Verdict: <one sentence>\n"
        "Confidence: <float>\n"
        "Publish: <yes/no>\n"
        "Rationale:\n"
        "- point 1\n"
        "- point 2\n"
    )

    def __init__(
        self,
        *,
        dissemination: DisseminationService,
        persistence: PersistenceService,
        elf_transport: ElfTransport,
        elf_order: Optional[Sequence[str]] = None,
        turnkey_service: Optional[TurnkeyService] = None,
        alpha_elf: Optional[AlphaElf] = None,
        llm: Optional[ChatBot] = None,
    ) -> None:
        super().__init__(
            llm=llm or ChatBot(llm_provider="anthropic", model_name="claude-haiku-4-5-20251001"),
            avaliable_tools=ToolManager([]),
            max_steps=4,
        )
        object.__setattr__(self, "dissemination", dissemination)
        object.__setattr__(self, "persistence", persistence)
        object.__setattr__(self, "turnkey_service", turnkey_service)
        object.__setattr__(self, "alpha_elf", alpha_elf)
        object.__setattr__(self, "elf_transport", elf_transport)
        elf_ids = tuple(elf_order or getattr(elf_transport, "elf_ids", ()))
        object.__setattr__(self, "elf_ids", elf_ids)

    async def process_letter(
        self,
        letter: UserLetter,
        *,
        alpha_signal: Optional[str] = None,
    ) -> SantaDecision:
        """
        Primary workflow: receive a UserLetter, dispatch elves, and synthesize Santa's verdict.
        """
        tracer = WorkflowTracer()
        tracer.emit("letter.received", "start", detail=f"token={letter.token}")

        reports = await self._gather_reports(letter, tracer)

        if alpha_signal and self.alpha_elf:
            tracer.emit("alpha.dispatch", "start", detail="alpha_signal_attached")
            try:
                alpha_report = await self.alpha_elf.from_signal(
                    token=letter.token,
                    thesis=letter.thesis,
                    signal_payload=alpha_signal,
                )
            except Exception as exc:  # pragma: no cover - defensive
                tracer.emit("alpha.dispatch", "error", detail=str(exc))
                raise
            tracer.emit(
                "alpha.dispatch",
                "success",
                detail=f"confidence={alpha_report.confidence}" if alpha_report.confidence is not None else None,
            )
            reports.append(alpha_report)

        council_result = CouncilResult(
            user_letter=letter,
            reports=reports,
            summary=self._summarize_reports(reports),
        )

        tracer.emit("santa.synthesizing", "start")
        decision = await self._llm_decide(letter, reports)
        decision.source = letter.source
        await self._finalize_decision(letter, reports, decision)
        decision.meta.setdefault("timeline", tracer.serialize())
        decision.meta.setdefault("council_summary", council_result.summary)
        await self.persistence.record_council_and_decision(council_result, decision)
        tracer.emit("santa.synthesizing", "success", detail=decision.verdict)
        return decision

    async def process_alpha_only(
        self,
        letter: UserLetter,
        *,
        alpha_signal: Optional[str] = None,
    ) -> SantaDecision:
        """
        Handle AlphaElf-only submissions, bypassing the standard elf council.
        """
        tracer = WorkflowTracer()
        tracer.emit("letter.received", "start", detail=f"token={letter.token}")

        reports: List[ElfReport] = []
        if alpha_signal and self.alpha_elf:
            tracer.emit("alpha.dispatch", "start", detail="alpha_signal_attached")
            try:
                alpha_report = await self.alpha_elf.from_signal(
                    token=letter.token,
                    thesis=letter.thesis,
                    signal_payload=alpha_signal,
                )
            except Exception as exc:  # pragma: no cover - defensive
                tracer.emit("alpha.dispatch", "error", detail=str(exc))
                raise
            tracer.emit(
                "alpha.dispatch",
                "success",
                detail=f"confidence={alpha_report.confidence}" if alpha_report.confidence is not None else None,
            )
            reports.append(alpha_report)

        if not reports:
            tracer.emit("alpha.dispatch", "start", detail="alpha_placeholder")
            reports.append(
                ElfReport(
                    elf_id="alpha",
                    analysis=letter.thesis,
                    confidence=None,
                    meta={"token": letter.token, "source": letter.source},
                )
            )
            tracer.emit("alpha.dispatch", "success", detail="placeholder_generated")

        tracer.emit("santa.synthesizing", "start")
        decision = await self._llm_decide(letter, reports)
        decision.source = letter.source
        await self._finalize_decision(letter, reports, decision)
        decision.meta.setdefault("timeline", tracer.serialize())
        await self.persistence.record_alpha_decision(letter, decision)
        tracer.emit("santa.synthesizing", "success", detail=decision.verdict)
        return decision

    async def _gather_reports(self, letter: UserLetter, tracer: WorkflowTracer) -> List[ElfReport]:
        if not self.elf_ids:
            tracer.emit("elves.dispatch_all", "success", detail="no_elves_configured")
            return []

        tracer.emit("elves.dispatch_all", "start", detail=",".join(self.elf_ids))
        reports: List[ElfReport] = []
        for elf_id in self.elf_ids:
            tracer.emit(f"{elf_id}.dispatch", "start")
            try:
                report = await self.elf_transport.fetch_report(elf_id, letter, tracer)
            except Exception as exc:
                tracer.emit(f"{elf_id}.dispatch", "error", detail=str(exc))
                tracer.emit("elves.dispatch_all", "error", detail=str(exc))
                raise
            tracer.emit(
                f"{elf_id}.dispatch",
                "success",
                detail=report.brief() if hasattr(report, "brief") else None,
            )
            reports.append(report)

        tracer.emit("elves.dispatch_all", "success", detail=",".join(report.elf_id for report in reports))
        return reports

    @staticmethod
    def _summarize_reports(reports: Sequence[ElfReport]) -> str:
        lines = [report.brief() for report in reports]
        return "\n".join(lines)

    async def _finalize_decision(
        self,
        letter: UserLetter,
        reports: List[ElfReport],
        decision: SantaDecision,
    ) -> None:
        if decision.publish:
            neofs_meta = await self.dissemination.store_reports(
                user_letter=letter,
                decision=decision,
                reports=reports,
            )
            if neofs_meta:
                decision.neofs_object_id = neofs_meta.get("object_id")
                decision.neofs_link = neofs_meta.get("public_url")

            await self.dissemination.broadcast(decision)

        # Enrich decision meta with wallet/user info
        decision.meta.setdefault("wallet_address", letter.wallet_address)
        decision.meta.setdefault("user_id", letter.user_id)
        if self.turnkey_service and self.turnkey_service.enabled():
            decision.meta.setdefault("turnkey_enabled", True)

    async def _llm_decide(self, letter: UserLetter, reports: List[ElfReport]) -> SantaDecision:
        score = self._compute_outcome_score(letter, reports)
        publish_threshold = 60
        publish = score >= publish_threshold
        rounded_conf = round(min(max(score / 100.0, 0.0), 1.0), 2)

        report_map = {report.elf_id: report for report in reports}
        reason_lines: List[str] = []
        for elf_id in self.elf_ids:
            report = report_map.get(elf_id)
            if report:
                reason_lines.append(f"{elf_id}: {report.brief()}")

        reasons_block = "\n".join(reason_lines)

        if publish:
            verdict = "I love it! Santa is sharing this alpha."
            rationale = (
                "I love it, Let's give the alpha to community, check TG and X for your ideas!\n"
                "Santa is giving the precious gift to everyone, thank you for your generosity!\n"
                f"{reasons_block}"
            )
        else:
            verdict = "Hold on to this alpha for now."
            rationale = (
                "Good call but this alpha is not good enough for community sharing reason如下:\n"
                f"{reasons_block}\n"
                "your love is received, Merry Christmas!"
            )

        decision = SantaDecision(
            verdict=verdict,
            publish=publish,
            confidence=rounded_conf,
            rationale=rationale,
            meta={
                "elf_reports": [report.to_agentcard_payload() for report in reports],
                "outcome_score": score,
                "publish_threshold": publish_threshold,
            },
        )
        return decision

    def _compute_outcome_score(self, letter: UserLetter, reports: List[ElfReport]) -> float:
        confidences = [
            float(report.confidence)
            for report in reports
            if isinstance(report.confidence, (int, float))
        ]
        base_score = (sum(confidences) / len(confidences) * 100.0) if confidences else 50.0

        thesis = letter.thesis or ""
        thesis_length = len(thesis)
        length_bonus = min(thesis_length / 5.0, 15.0)

        enthusiasm_words = ["love", "bull", "bullish", "moon", "pump", "moonshot"]
        lower_thesis = thesis.lower()
        enthusiasm_hits = sum(lower_thesis.count(word) for word in enthusiasm_words if word)
        emoji_hits = sum(thesis.count(symbol) for symbol in ["🔥", "🚀"])
        exclamation_hits = thesis.count("!")

        enthusiasm_bonus = min(enthusiasm_hits * 5.0, 15.0)
        emoji_bonus = min(emoji_hits * 5.0, 10.0)
        exclamation_bonus = min(exclamation_hits * 2.5, 10.0)

        total = base_score + length_bonus + enthusiasm_bonus + emoji_bonus + exclamation_bonus
        return max(0.0, min(100.0, total))
