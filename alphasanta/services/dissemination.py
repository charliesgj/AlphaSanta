"""
Dissemination layer: persist Santa's decisions and notify channels.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
from typing import Dict, Optional, Sequence

from spoon_ai.neofs import NeoFSClient, NeoFSException

try:
    from spoon_toolkits.social_media.telegram_tool import TelegramTool
    from spoon_toolkits.social_media.twitter_tool import TwitterTool
except ImportError:  # Optional dependency
    TelegramTool = None  # type: ignore
    TwitterTool = None  # type: ignore

from ..schema import UserLetter, ElfReport, SantaDecision

logger = logging.getLogger(__name__)


class DisseminationService:
    """
    Handles persistence (NeoFS) and outreach (X/Telegram) for Santa's decisions.
    """

    def __init__(
        self,
        *,
        neofs_enabled: bool = True,
        neofs_container_id: Optional[str] = None,
        twitter_enabled: bool = False,
        telegram_enabled: bool = False,
    ) -> None:
        self.neofs_enabled = neofs_enabled
        self.neofs_container_id = neofs_container_id or os.getenv("NEOFS_CONTAINER_ID")
        self.twitter_enabled = twitter_enabled
        self.telegram_enabled = telegram_enabled

        self._neofs_client: Optional[NeoFSClient] = None
        self._twitter_tool: Optional[TwitterTool] = TwitterTool() if (twitter_enabled and TwitterTool) else None
        self._telegram_tool: Optional[TelegramTool] = TelegramTool() if (telegram_enabled and TelegramTool) else None

        gateway_url = os.getenv("NEOFS_GATEWAY_URL")
        self._neofs_gateway_url = gateway_url.rstrip("/") if gateway_url else None

    def _ensure_neofs_client(self) -> NeoFSClient:
        if self._neofs_client:
            return self._neofs_client
        if not self.neofs_enabled:
            raise RuntimeError("NeoFS storage is disabled.")
        self._neofs_client = NeoFSClient()
        return self._neofs_client

    async def store_reports(
        self,
        *,
        user_letter: UserLetter,
        decision: SantaDecision,
        reports: Sequence[ElfReport],
        max_retries: int = 3,
    ) -> Optional[Dict[str, str]]:
        """
        Persist the decision and supporting evidence to NeoFS.
        """
        if not self.neofs_enabled:
            return None
        container_id = self.neofs_container_id
        if not container_id:
            logger.warning("NEOFS_CONTAINER_ID not set; skipping NeoFS upload.")
            return None

        payload = {
            "decision": decision.to_dict(),
            "user_letter": {
                "token": user_letter.token,
                "thesis": user_letter.thesis,
                "source": user_letter.source,
            },
            "reports": [report.to_agentcard_payload() for report in reports],
        }
        client = self._ensure_neofs_client()
        attempt = 0
        while attempt < max_retries:
            try:
                upload_result = client.upload_object(
                    container_id=container_id,
                    content=json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8"),
                    attributes={"token": user_letter.token, "source": user_letter.source},
                )
                logger.info(
                    "Stored decision in NeoFS container=%s object=%s",
                    upload_result.container_id,
                    upload_result.object_id,
                )
                link = None
                if self._neofs_gateway_url:
                    link = f"{self._neofs_gateway_url}/{upload_result.container_id}/{upload_result.object_id}"
                return {
                    "container_id": upload_result.container_id,
                    "object_id": upload_result.object_id,
                    "public_url": link or "",
                }
            except (NeoFSException, ValueError) as exc:
                attempt += 1
                logger.warning("NeoFS upload failed (attempt %s/%s): %s", attempt, max_retries, exc)
                if attempt >= max_retries:
                    logger.error("Giving up on NeoFS upload after %s attempts", attempt)
                    return None
                await asyncio.sleep(1.5 * attempt)

    async def broadcast(self, decision: SantaDecision) -> None:
        """
        Post Santa's decision to configured social channels.
        """
        if not decision.publish:
            logger.info("Decision marked as non-public; skipping social broadcast.")
            return

        message = self._format_broadcast(decision)
        tasks = []

        if self.twitter_enabled and self._twitter_tool:
            tasks.append(self._send_tweet(message))
        if self.telegram_enabled and self._telegram_tool:
            tasks.append(self._send_telegram(message))

        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    async def _send_tweet(self, message: str) -> None:
        assert self._twitter_tool is not None
        max_attempts = 3
        for attempt in range(1, max_attempts + 1):
            try:
                self._twitter_tool.post_tweet(message)
                logger.info("Posted decision to X/Twitter.")
                return
            except Exception as exc:
                logger.warning("Failed to post tweet (attempt %s/%s): %s", attempt, max_attempts, exc)
                await asyncio.sleep(1.5 * attempt)

    async def _send_telegram(self, message: str) -> None:
        assert self._telegram_tool is not None
        max_attempts = 3
        for attempt in range(1, max_attempts + 1):
            try:
                await self._telegram_tool.send_message(message=message)
                logger.info("Sent decision to Telegram.")
                return
            except Exception as exc:
                logger.warning("Failed to send Telegram message (attempt %s/%s): %s", attempt, max_attempts, exc)
                await asyncio.sleep(1.5 * attempt)

    @staticmethod
    def _format_broadcast(decision: SantaDecision) -> str:
        base = f"🎅 Santa's verdict: {decision.verdict}"
        if decision.confidence is not None:
            base += f" (confidence {decision.confidence:.2f})"
        if decision.neofs_link:
            base += f"\n📦 NeoFS: {decision.neofs_link}"
        if decision.rationale:
            base += f"\n\n{decision.rationale}"
        return base
