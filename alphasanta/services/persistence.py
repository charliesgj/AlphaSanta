"""Persistence layer that writes submissions and agent outputs to Supabase."""

from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import datetime
from typing import Any, Dict, List

from supabase import Client as SupabaseClient, create_client as create_supabase_client  # type: ignore

from ..config import Settings
from ..schema import SantaDecision, UserLetter

logger = logging.getLogger(__name__)


class PersistenceService:
    """Stores submission states plus per-agent outputs."""

    def __init__(self, settings: Settings) -> None:
        if not settings.supabase_enabled():
            raise RuntimeError("Supabase is not configured. Set SUPABASE_URL and SUPABASE_ANON_KEY.")
        self._client: SupabaseClient = create_supabase_client(settings.supabase_url, settings.supabase_key)
        self._agent_id_map: Dict[str, str] = {k.lower(): v for k, v in (settings.agent_id_map or {}).items()}

    async def create_submission(self, letter: UserLetter) -> str:
        return await asyncio.to_thread(self._create_submission_sync, letter)

    async def finalize_submission(
        self,
        submission_id: str,
        letter: UserLetter,
        decision: SantaDecision,
    ) -> None:
        await asyncio.to_thread(self._finalize_submission_sync, submission_id, letter, decision)

    # ------------------------------------------------------------------
    # Internal helpers (sync, executed via to_thread)
    # ------------------------------------------------------------------

    def _create_submission_sync(self, letter: UserLetter) -> str:
        submission_id = str(uuid.uuid4())
        now = datetime.utcnow().isoformat()
        payload = {
            "submission_id": submission_id,
            "user_id": letter.user_id,
            "token_pair": letter.token,
            "thesis": letter.thesis,
            "status": "pending",
            "agent_confidence": None,
            "santa_score": None,
            "santa_decision": None,
            "result": {
                "source": letter.source,
                "metadata": letter.metadata or {},
            },
            "created_at": now,
            "updated_at": now,
        }
        self._client.table("submissions").insert(payload).execute()
        return submission_id

    def _finalize_submission_sync(
        self,
        submission_id: str,
        letter: UserLetter,
        decision: SantaDecision,
    ) -> None:
        result_payload: Dict[str, Any] = getattr(decision, "_result_payload", {}) or {}
        meta = decision.meta or {}
        if not result_payload:
            fallback_decision = {
                "verdict": "pass" if decision.publish else "not_pass",
                "publish": decision.publish,
                "santa_score": int(float(decision.confidence or 0) * 100) if decision.confidence is not None else None,
                "agent_confidence": decision.confidence,
                "rationale": decision.rationale,
                "confidence": decision.confidence,
            }
            metadata_block = {
                "user_id": letter.user_id,
                "source": letter.source,
                "submission_id": submission_id,
            }
            if letter.metadata:
                metadata_block["extra"] = letter.metadata
            result_payload = {
                "token": letter.token,
                "thesis": letter.thesis,
                "source": letter.source,
                "missions": [],
                "agents": [],
                "decision": fallback_decision,
                "timeline": meta.get("timeline", []),
                "metadata": metadata_block,
            }
        result_payload.setdefault("token", letter.token)
        result_payload.setdefault("thesis", letter.thesis)
        result_payload.setdefault("source", letter.source)
        metadata_block = result_payload.get("metadata")
        if not isinstance(metadata_block, dict):
            metadata_block = {}
        metadata_block.setdefault("user_id", letter.user_id)
        metadata_block.setdefault("source", letter.source)
        if letter.metadata:
            metadata_block.setdefault("extra", letter.metadata)
        metadata_block["submission_id"] = submission_id
        result_payload["metadata"] = metadata_block

        decision_block = result_payload.get("decision", {}) or {}
        avg_confidence = decision_block.get("agent_confidence")
        santa_score = decision_block.get("santa_score")
        santa_decision = decision_block.get("verdict") or ("pass" if decision.publish else "not_pass")
        if santa_score is None and isinstance(decision.confidence, (int, float)):
            santa_score = int(float(decision.confidence) * 100)

        update_payload = {
            "status": "completed",
            "agent_confidence": avg_confidence,
            "santa_score": santa_score,
            "santa_decision": santa_decision,
            "result": result_payload,
            "updated_at": datetime.utcnow().isoformat(),
        }
        self._client.table("submissions").update(update_payload).eq("submission_id", submission_id).execute()

        agents = list(result_payload.get("agents") or [])
        self._insert_agent_rows(submission_id, agents, santa_score, santa_decision)
        self._insert_santa_row(submission_id, decision, santa_score, santa_decision)

    # ------------------------------------------------------------------
    # Row builders
    # ------------------------------------------------------------------

    def _insert_agent_rows(
        self,
        submission_id: str,
        agents: List[Dict[str, Any]],
        santa_score: Any,
        santa_decision: Any,
    ) -> None:
        for agent in agents:
            elf_id = str(agent.get("elf_id", "")).lower()
            agent_id = self._agent_id_map.get(elf_id)
            if not agent_id:
                logger.warning("No agent_id configured for elf_id=%s; skipping submission_agents insert.", elf_id)
                continue
            summary = agent.get("summary") or {}
            record = {
                "id": str(uuid.uuid4()),
                "submission_id": submission_id,
                "agent_id": agent_id,
                "agent_confidence": summary.get("confidence"),
                "santa_score": santa_score,
                "santa_decision": santa_decision,
                "agent_output": agent,
                "processed_at": datetime.utcnow().isoformat(),
            }
            self._client.table("submission_agents").insert(record).execute()

    def _insert_santa_row(
        self,
        submission_id: str,
        decision: SantaDecision,
        santa_score: Any,
        santa_decision: Any,
    ) -> None:
        santa_agent_id = self._agent_id_map.get("santa")
        if not santa_agent_id:
            return
        record = {
            "id": str(uuid.uuid4()),
            "submission_id": submission_id,
            "agent_id": santa_agent_id,
            "agent_confidence": decision.confidence,
            "santa_score": santa_score,
            "santa_decision": santa_decision,
            "agent_output": decision.to_dict(),
            "processed_at": datetime.utcnow().isoformat(),
        }
        self._client.table("submission_agents").insert(record).execute()
