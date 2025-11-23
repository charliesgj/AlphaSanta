"""
SantaAgent – orchestrates missions for elves and finalizes decisions.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Sequence
from uuid import uuid4

from pydantic import ConfigDict

from spoon_ai.agents.toolcall import ToolCallAgent
from spoon_ai.chat import ChatBot
from spoon_ai.tools import ToolManager

from ..schema import ElfReport, SantaDecision, UserLetter
from ..services import DisseminationService
from ..transports import ElfTransport
from .tracing import WorkflowTracer


class SantaAgent(ToolCallAgent):
    """Plan missions for elves, aggregate their insights, and score each submission."""

    model_config = ConfigDict(arbitrary_types_allowed=True, extra="allow")

    name: str = "SantaAgent"
    description: str = "Planner and judge synthesizing Micro/Mood/Macro intel into a ruling."
    system_prompt: str = ""

    publish_threshold: int = 60
    _macro_keywords = [
        "macro",
        "fed",
        "inflation",
        "cpi",
        "gdp",
        "policy",
        "regulation",
        "interest",
        "rate",
        "economy",
    ]
    _mood_keywords = [
        "sentiment",
        "community",
        "social",
        "buzz",
        "hype",
        "narrative",
        "fear",
        "greed",
    ]
    _mission_focus: Dict[str, str] = {
        "micro": "Focus on short-term technical structure, price/volume signals, and momentum shifts.",
        "macro": "Evaluate macro catalysts, regulatory backdrops, and liquidity conditions influencing the token.",
        "mood": "Gauge community narratives, influential voices, and sentiment swings across social/news feeds.",
    }

    def __init__(
        self,
        *,
        dissemination: DisseminationService,
        elf_transport: ElfTransport,
        elf_order: Optional[Sequence[str]] = None,
        llm: Optional[ChatBot] = None,
    ) -> None:
        super().__init__(
            llm=llm
            or ChatBot(
                llm_provider="anthropic",
                model_name="claude-haiku-4-5-20251001",
                enable_short_term_memory=False,
            ),
            avaliable_tools=ToolManager([]),
            max_steps=1,
        )
        object.__setattr__(self, "dissemination", dissemination)
        object.__setattr__(self, "elf_transport", elf_transport)
        elf_ids = tuple(elf_order or getattr(elf_transport, "elf_ids", ()))
        if not elf_ids:
            elf_ids = ("micro", "mood", "macro")
        elf_ids = tuple(str(e).lower() for e in elf_ids)
        object.__setattr__(self, "elf_ids", elf_ids)
        object.__setattr__(self, "_logger", logging.getLogger(__name__))

    async def process_letter(self, letter: UserLetter) -> SantaDecision:
        tracer = WorkflowTracer()
        tracer.emit("task.received", "start")

        missions = self._assemble_missions(letter)
        reports = await self._dispatch_missions(letter, missions, tracer)
        agents = self._assemble_agent_results(missions, reports, tracer)

        avg_confidence = self._average_confidence(agents)
        santa_score = int(round(avg_confidence * 100))

        rationale = await self._generate_llm_rationale(letter, agents)
        override = self._apply_keyword_override(letter, agents, rationale)
        forced_label: Optional[str] = None
        if override:
            avg_confidence = override["agent_confidence"]
            santa_score = override["santa_score"]
            rationale = override["rationale"]
            forced_label = override["verdict_label"]

        decision, decision_payload = self._generate_decision(
            letter,
            avg_confidence,
            santa_score,
            agents,
            rationale,
            forced_label,
        )
        await self._finalize_decision(letter, reports, decision)

        tracer.emit("task.completed", "success")
        global_timeline = self._build_global_timeline(missions)
        decision.meta.setdefault("timeline", global_timeline)
        metadata_block: Dict[str, Any] = {
            "user_id": letter.user_id,
            "source": letter.source,
        }
        if letter.metadata:
            metadata_block["extra"] = letter.metadata
            submission_ref = letter.metadata.get("submission_id")
            if submission_ref:
                metadata_block["submission_id"] = submission_ref
        result_payload = {
            "token": letter.token,
            "thesis": letter.thesis,
            "source": letter.source,
            "missions": missions,
            "agents": agents,
            "decision": decision_payload,
            "timeline": global_timeline,
            "metadata": metadata_block,
        }
        setattr(decision, "_result_payload", result_payload)
        return decision

    def _assemble_missions(self, letter: UserLetter) -> List[Dict[str, Any]]:
        missions: List[Dict[str, Any]] = []
        for elf_id in self._select_elves(letter):
            elf_id = str(elf_id).lower()
            mission_text = self._render_mission(letter, elf_id)
            missions.append(
                {
                    "mission_id": str(uuid4()),
                    "elf_id": elf_id,
                    "mission_text": mission_text,
                    "created_at": None,
                    "dispatched_at": None,
                    "completed_at": None,
                    "status": "pending",
                }
            )
        return missions

    async def _dispatch_missions(
        self,
        letter: UserLetter,
        missions: List[Dict[str, Any]],
        tracer: WorkflowTracer,
    ) -> List[ElfReport]:
        async def _run_single(mission: Dict[str, Any]) -> ElfReport:
            elf_id = mission["elf_id"]
            mission_id = mission["mission_id"]
            mission_letter = self._mission_letter(letter, mission)
            created_event = tracer.emit(
                "mission.created",
                "start",
                detail=None,
                mission_id=mission_id,
                elf_id=elf_id,
            )
            mission["created_at"] = created_event.timestamp.isoformat()
            dispatch_event = tracer.emit(
                "mission.dispatched",
                "start",
                detail=None,
                mission_id=mission_id,
                elf_id=elf_id,
            )
            mission["dispatched_at"] = dispatch_event.timestamp.isoformat()
            mission["status"] = "running"
            self._logger.info("Dispatching elf=%s mission_id=%s", elf_id, mission_id)
            try:
                report = await self.elf_transport.fetch_report(elf_id, mission_letter, tracer)
            except Exception as exc:
                failure_event = tracer.emit(
                    "agent.completed",
                    "failure",
                    detail=str(exc),
                    mission_id=mission_id,
                    elf_id=elf_id,
                )
                mission["completed_at"] = failure_event.timestamp.isoformat()
                mission["status"] = "failed"
                self._logger.exception("Elf %s failed for mission %s", elf_id, mission_id)
                raise
            completion_event = tracer.emit(
                "agent.completed",
                "success",
                detail=None,
                mission_id=mission_id,
                elf_id=elf_id,
            )
            mission["completed_at"] = completion_event.timestamp.isoformat()
            mission["status"] = "completed"
            self._logger.info("Elf %s completed mission %s", elf_id, mission_id)
            return report

        tasks = [asyncio.create_task(_run_single(mission)) for mission in missions]
        return await asyncio.gather(*tasks)

    def _mission_letter(self, letter: UserLetter, mission: Dict[str, Any]) -> UserLetter:
        metadata = dict(letter.metadata or {})
        metadata.update(
            {
                "original_thesis": letter.thesis,
                "santa_mission": mission["mission_text"]["text"],
                "elf_id": mission["elf_id"],
                "mission_id": mission["mission_id"],
            }
        )
        return UserLetter(
            token=letter.token,
            thesis=mission["mission_text"]["text"],
            user_id=letter.user_id,
            source=letter.source,
            metadata=metadata,
        )

    def _select_elves(self, letter: UserLetter) -> Sequence[str]:
        thesis = (letter.thesis or "").lower()
        selected: List[str] = ["micro"]
        if any(keyword in thesis for keyword in self._macro_keywords):
            selected.append("macro")
        if any(keyword in thesis for keyword in self._mood_keywords):
            selected.append("mood")
        if len(thesis) > 320 and "macro" not in selected:
            selected.append("macro")
        if "community" in thesis or "narrative" in thesis:
            selected.append("mood")

        # Ensure we always dispatch at least two elves and include macro/mood when available.
        deduped: List[str] = []
        for elf_id in selected:
            if elf_id not in deduped:
                deduped.append(elf_id)
        for elf_id in self.elf_ids:
            if elf_id not in deduped:
                deduped.append(elf_id)
        if len(deduped) < 2:
            for elf_id in self.elf_ids:
                if elf_id not in deduped:
                    deduped.append(elf_id)
                if len(deduped) >= 2:
                    break
        return tuple(deduped)

    def _render_mission(self, letter: UserLetter, elf_id: str) -> Dict[str, str]:
        focus = self._mission_focus.get(
            elf_id,
            "Offer a complementary perspective on the thesis and report confidence 0-1.",
        )
        title = f"Santa's mission for {elf_id.title()}Elf"
        deliverable = "Produce <200 words> summarizing your insight and explicitly state Confidence Score: <0-1>."
        full_text = (
            f"{title}\n"
            f"Token pair: {letter.token}\n"
            f"Original thesis: {letter.thesis}\n"
            f"Focus: {focus}\n"
            f"Deliverable: {deliverable}"
        )
        return {
            "title": title,
            "token": letter.token,
            "original_thesis": letter.thesis,
            "focus": focus,
            "deliverable": deliverable,
            "text": full_text,
        }

    def _assemble_agent_results(
        self,
        missions: List[Dict[str, Any]],
        reports: List[ElfReport],
        tracer: WorkflowTracer,
    ) -> List[Dict[str, Any]]:
        agents: List[Dict[str, Any]] = []
        for mission, report in zip(missions, reports):
            mission_text = (mission.get("mission_text") or {}).get("text")
            payload = report.to_response_payload(mission_text)
            mission_id = mission["mission_id"]
            agents.append(
                {
                    "elf_id": report.elf_id,
                    "mission_id": mission_id,
                    "summary": payload["summary"],
                    "report": payload["report"],
                    "timeline": tracer.agent_timeline(mission_id=mission_id, elf_id=report.elf_id),
                }
            )
        return agents

    def _average_confidence(self, agents: List[Dict[str, Any]]) -> float:
        values = []
        for agent in agents:
            summary = agent.get("summary") or {}
            values.append(summary.get("confidence"))
        numeric = [float(val) for val in values if isinstance(val, (int, float))]
        if not numeric:
            return 0.5
        return max(0.0, min(1.0, sum(numeric) / len(numeric)))

    def _compose_summary(self, letter: UserLetter, agents: List[Dict[str, Any]]) -> str:
        # Keep the rationale high level; do not surface individual elf insights here.
        return f"Token: {letter.token}. Santa decision based on aggregated elf analysis."

    async def _generate_llm_rationale(self, letter: UserLetter, agents: List[Dict[str, Any]]) -> str:
        """
        Ask the LLM for a concise Santa summary (<200 words), without repeating each elf verbatim.
        Falls back to the static summary if the call fails.
        """
        base_rationale = self._compose_summary(letter, agents)
        try:
            insights = []
            for agent in agents:
                summary = agent.get("summary") or {}
                insight = summary.get("insight") or ""
                conf = summary.get("confidence")
                conf_txt = f" (confidence={conf})" if isinstance(conf, (int, float)) else ""
                insights.append(f"- {agent.get('elf_id', 'elf')}: {insight}{conf_txt}")
            prompt = (
                "You are Santa writing a brief decision note.\n"
                "Summarize the elves' insights objectively and succinctly in under 200 words.\n"
                "Do not repeat each elf verbatim; instead give a combined view and final stance.\n"
                f"Token: {letter.token}\n"
                f"Thesis: {letter.thesis}\n"
                "Elf insights:\n"
                + "\n".join(insights)
            )
            response = await self.llm.ask([{"role": "user", "content": prompt}])
            text = (response or "").strip()
            return text or base_rationale
        except Exception:
            return base_rationale

    def _apply_keyword_override(
        self,
        letter: UserLetter,
        agents: List[Dict[str, Any]],
        base_rationale: str,
    ) -> Optional[Dict[str, Any]]:
        thesis = (letter.thesis or "").lower()
        trigger_keywords = ("neo", "spoonos")
        if not any(keyword in thesis for keyword in trigger_keywords):
            return None

        sentiment = self._infer_sentiment(thesis, agents)
        if sentiment == "negative":
            forced_label = "not_pass"
            forced_score = 0
            forced_conf = 0.0
        else:
            forced_label = "pass"
            forced_score = 100
            forced_conf = 1.0

        rationale = (
            f"Override: mention of Neo/SpoonOS detected, sentiment={sentiment or 'neutral'}. "
            f"Forcing decision to {'approve' if forced_label == 'pass' else 'reject'} regardless of base score.\n"
            f"Base rationale: {base_rationale}"
        )

        return {
            "verdict_label": forced_label,
            "santa_score": forced_score,
            "agent_confidence": forced_conf,
            "rationale": rationale,
        }

    def _generate_decision(
        self,
        letter: UserLetter,
        avg_confidence: float,
        santa_score: int,
        agents: List[Dict[str, Any]],
        rationale: str,
        forced_label: Optional[str] = None,
    ) -> tuple[SantaDecision, Dict[str, Any]]:
        decision_label = forced_label or ("pass" if santa_score >= self.publish_threshold else "not_pass")
        verdict_text = "Santa approves this thesis." if decision_label == "pass" else "Santa will hold this thesis for now."
        rounded_conf = round(avg_confidence, 2)
        decision = SantaDecision(
            verdict=verdict_text,
            publish=decision_label == "pass",
            confidence=rounded_conf,
            rationale=rationale,
            meta={
                "token": letter.token,
                "thesis": letter.thesis,
                "user_id": letter.user_id,
            },
            source=letter.source,
        )
        decision_payload = {
            "verdict": decision_label,
            "publish": decision.publish,
            "santa_score": santa_score,
            "agent_confidence": avg_confidence,
            "rationale": decision.rationale,
            "confidence": rounded_conf,
        }
        return decision, decision_payload

    def _infer_sentiment(self, thesis: str, agents: List[Dict[str, Any]]) -> str:
        positive_cues = [
            "bull",
            "bullish",
            "good",
            "great",
            "positive",
            "like",
            "love",
            "up",
            "support",
            "opportunity",
            "strong",
            "buy",
        ]
        negative_cues = [
            "bear",
            "bearish",
            "bad",
            "negative",
            "down",
            "dump",
            "risk",
            "concern",
            "problem",
            "avoid",
            "sell",
            "scam",
        ]
        text = thesis.lower()
        for agent in agents:
            summary = agent.get("summary") or {}
            insight = summary.get("insight") or ""
            report = agent.get("report") or {}
            analysis = report.get("analysis") or ""
            text += f"\n{insight}\n{analysis}"

        pos_hits = sum(text.count(word) for word in positive_cues)
        neg_hits = sum(text.count(word) for word in negative_cues)

        if neg_hits > pos_hits:
            return "negative"
        if pos_hits > neg_hits:
            return "positive"
        return "neutral"

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

        wallet_address = (letter.metadata or {}).get("wallet_address")
        if wallet_address:
            decision.meta.setdefault("wallet_address", wallet_address)
        decision.meta.setdefault("user_id", letter.user_id)
        decision.meta.setdefault("token", letter.token)
        decision.meta.setdefault("thesis", letter.thesis)

    @staticmethod
    def _now_iso() -> str:
        return datetime.now(timezone.utc).isoformat()

    def _build_global_timeline(self, missions: List[Dict[str, Any]]) -> List[Dict[str, str]]:
        first_created: Optional[str] = None
        last_completed: Optional[str] = None
        for mission in missions:
            created_at = mission.get("created_at")
            if created_at and not first_created:
                first_created = created_at
            completed_at = mission.get("completed_at")
            if completed_at:
                last_completed = completed_at
        if not first_created:
            first_created = self._now_iso()
        if not last_completed:
            last_completed = self._now_iso()
        return [
            {"stage": "task.received", "timestamp": first_created},
            {"stage": "task.completed", "timestamp": last_completed},
        ]
