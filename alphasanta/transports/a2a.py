"""
A2A-based transport that invokes remote elves via their AgentCard endpoints.
"""

from __future__ import annotations

import json
import uuid
from typing import Any, Dict, Mapping, Sequence, Optional, TYPE_CHECKING

import httpx

from ..schema import UserLetter, ElfReport
from ..santa.tracing import WorkflowTracer
from .base import ElfTransport
import logging

if TYPE_CHECKING:
    from ..orchestrator.elf_runner import ElfRunner


class A2AElfTransport(ElfTransport):
    """
    Uses the Google A2A SDK to call remote elf AgentCards.
    """

    def __init__(
        self,
        endpoints: Mapping[str, str],
        *,
        timeout: float = 30.0,
        fallbacks: Optional[Mapping[str, "ElfRunner"]] = None,
    ) -> None:
        if not endpoints:
            raise ValueError("A2AElfTransport requires at least one endpoint.")
        try:
            from a2a.client import A2AClient, A2ACardResolver
            from a2a.types import MessageSendParams, SendMessageRequest
        except ImportError as exc:  # pragma: no cover - optional dependency
            raise RuntimeError(
                "A2A SDK not installed. Ensure the default installation succeeded or install `google-a2a`."
            ) from exc

        self._A2AClient = A2AClient
        self._A2ACardResolver = A2ACardResolver
        self._MessageSendParams = MessageSendParams
        self._SendMessageRequest = SendMessageRequest
        self._endpoints: Dict[str, str] = {elf_id: url.rstrip("/") for elf_id, url in endpoints.items() if url}
        self._timeout = timeout
        self._card_cache: Dict[str, Any] = {}
        self._logger = logging.getLogger(__name__)
        self._fallbacks: Dict[str, "ElfRunner"] = dict(fallbacks or {})

    @property
    def elf_ids(self) -> Sequence[str]:
        return tuple(self._endpoints.keys())

    async def fetch_report(self, elf_id: str, letter: UserLetter, tracer: WorkflowTracer) -> ElfReport:
        endpoint = self._endpoints.get(elf_id)
        if not endpoint:
            raise ValueError(f"No A2A endpoint configured for elf_id={elf_id}")

        async with httpx.AsyncClient(timeout=self._timeout) as client:
            card = await self._resolve_agent_card(elf_id, endpoint, client, tracer)
            a2a_client = self._A2AClient(client, card, url=endpoint)

            message_payload = self._build_message_payload(letter)
            params = self._MessageSendParams.model_validate(message_payload)
            request = self._SendMessageRequest(id=str(uuid.uuid4()), params=params)

            if self._logger.isEnabledFor(logging.INFO):
                try:
                    payload_preview = json.dumps(message_payload, ensure_ascii=False)
                except Exception:
                    payload_preview = "<unserializable payload>"
                self._logger.info("A2A[%s] payload: %s", elf_id, payload_preview)
            tracer.emit(f"{elf_id}.a2a.payload", "ready")

            tracer.emit(f"{elf_id}.a2a.send", "start", detail=endpoint)
            try:
                response = await a2a_client.send_message(request)
            except Exception as exc:  # pragma: no cover - network failure
                tracer.emit(f"{elf_id}.a2a.send", "error", detail=str(exc))
                raise
        tracer.emit(f"{elf_id}.a2a.send", "success")

        try:
            response_preview = response.model_dump_json(exclude_none=True)
        except Exception:
            response_preview = "<unserializable response>"
        if self._logger.isEnabledFor(logging.INFO):
            self._logger.info("A2A[%s] response: %s", elf_id, response_preview)
        tracer.emit(f"{elf_id}.a2a.receive", "raw", detail=response_preview[:512])

        try:
            return self._parse_report_from_response(elf_id, response, tracer)
        except Exception as exc:
            tracer.emit(f"{elf_id}.a2a.parse", "error", detail=str(exc))
            fallback = self._fallbacks.get(elf_id)
            if fallback:
                tracer.emit(f"{elf_id}.a2a.fallback", "start", detail="local_runner")
                try:
                    report = await fallback.run(letter)
                except Exception as fallback_exc:
                    tracer.emit(f"{elf_id}.a2a.fallback", "error", detail=str(fallback_exc))
                    raise
                tracer.emit(f"{elf_id}.a2a.fallback", "success")
                return report
            raise

    async def _resolve_agent_card(
        self,
        elf_id: str,
        endpoint: str,
        client: httpx.AsyncClient,
        tracer: WorkflowTracer,
    ):
        cached = self._card_cache.get(elf_id)
        if cached is not None:
            return cached

        tracer.emit(f"{elf_id}.a2a.card", "start", detail=endpoint)
        resolver = self._A2ACardResolver(client, endpoint)
        try:
            card = await resolver.get_agent_card()
        except Exception as exc:  # pragma: no cover - network failure
            tracer.emit(f"{elf_id}.a2a.card", "error", detail=str(exc))
            raise
        tracer.emit(f"{elf_id}.a2a.card", "success")
        self._card_cache[elf_id] = card
        return card

    def _build_message_payload(self, letter: UserLetter) -> Dict[str, Any]:
        body = {
            "token": letter.token,
            "thesis": letter.thesis,
            "source": letter.source,
            "user_id": letter.user_id,
            "metadata": letter.metadata or {},
        }
        payload_text = json.dumps(body, ensure_ascii=False)
        uuid_str = str(uuid.uuid4())
        return {
            "message": {
                "role": "user",
                "parts": [{"type": "text", "text": payload_text}],
                "messageId": uuid_str,
            }
        }

    def _parse_report_from_response(self, elf_id: str, response: Any, tracer: WorkflowTracer) -> ElfReport:
        try:
            response_json = json.loads(response.model_dump_json(exclude_none=True))
        except Exception as exc:  # pragma: no cover - defensive
            raise RuntimeError(f"A2A response parsing failed for elf_id={elf_id}: {exc}") from exc

        result_block = (response_json.get("root") or {}).get("result") or {}

        def _collect_textual_parts(nodes):
            collected = []
            if not isinstance(nodes, list):
                return collected
            for node in nodes:
                if not isinstance(node, dict):
                    continue
                parts = node.get("parts") or node.get("content")
                if isinstance(parts, str):
                    collected.append(parts)
                    continue
                if isinstance(parts, list):
                    for part in parts:
                        if isinstance(part, dict):
                            text = part.get("text") or part.get("content")
                            if isinstance(text, str):
                                collected.append(text)
                        elif isinstance(part, str):
                            collected.append(part)
                text_field = node.get("text") or node.get("message") or node.get("content")
                if isinstance(text_field, str):
                    collected.append(text_field)
            return collected

        text_payloads = []
        text_payloads.extend(_collect_textual_parts(result_block.get("artifacts", [])))

        if not text_payloads:
            text_payloads.extend(_collect_textual_parts(result_block.get("messages", [])))

        if not text_payloads:
            outputs = result_block.get("output") or result_block.get("outputs")
            text_payloads.extend(_collect_textual_parts(outputs))

        if not text_payloads and isinstance(result_block.get("response"), dict):
            response_section = result_block["response"]
            text_payloads.extend(_collect_textual_parts(response_section.get("messages", [])))
            if not text_payloads:
                resp_outputs = response_section.get("output") or response_section.get("outputs")
                text_payloads.extend(_collect_textual_parts(resp_outputs))

        if not text_payloads and isinstance(result_block, dict):
            for key in ("text", "content", "message", "payload"):
                value = result_block.get(key)
                if isinstance(value, str):
                    text_payloads.append(value)
                elif isinstance(value, list):
                    text_payloads.extend(_collect_textual_parts(value))
                elif isinstance(value, dict):
                    text_payloads.extend(_collect_textual_parts([value]))

        if not text_payloads:
            try:
                snippet = json.dumps(result_block, ensure_ascii=False)[:512]
            except Exception:
                snippet = "<unserializable result payload>"
            tracer.emit(f"{elf_id}.a2a.receive", "error", detail=f"no_textual_artifacts snippet={snippet}")
            raise RuntimeError(
                f"Elf {elf_id} returned no textual artifacts via A2A. "
                f"Result snippet: {snippet}"
            )

        tracer.emit(f"{elf_id}.a2a.receive", "success", detail=f"chars={len(text_payloads[0])}")
        try:
            payload = json.loads(text_payloads[0])
        except json.JSONDecodeError as exc:
            raise RuntimeError(f"Elf {elf_id} returned invalid JSON payload: {exc}") from exc

        return ElfReport(
            elf_id=payload.get("elf_id", elf_id),
            analysis=payload.get("analysis", ""),
            confidence=payload.get("confidence"),
            rationale=payload.get("rationale"),
            evidence=payload.get("evidence", {}),
            meta=payload.get("meta", {}),
        )
