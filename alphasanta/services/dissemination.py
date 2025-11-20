"""
Dissemination layer: persist Santa's decisions and notify channels.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
from typing import Dict, Optional, Sequence

from spoon_ai.neofs import NeoFSClient, NeoFSException  # leaving NeoFS untouchd

import tweepy
from telegram import Bot
from telegram.error import TelegramError

from ..schema import UserLetter, ElfReport, SantaDecision

logger = logging.getLogger(__name__)


class DisseminationService:
    """
    Handles persistence (NeoFS) and outreach (Twitter / Telegram) for Santa's decisions.
    """

    def __init__(
        self,
        *,
        neofs_enabled: bool = False,
        neofs_container_id: Optional[str] = None,
        twitter_enabled: bool = True,
        telegram_enabled: bool = True,
    ) -> None:

        self.neofs_enabled = neofs_enabled
        self.neofs_container_id = neofs_container_id or os.getenv("NEOFS_CONTAINER_ID")

        self.twitter_enabled = twitter_enabled
        self.telegram_enabled = telegram_enabled

        self._neofs_client: Optional[NeoFSClient] = None

        # --------------------------
        # Twitter (official API via tweepy)
        # --------------------------
        if twitter_enabled:
            api_key = os.getenv("TWITTER_API_KEY")
            api_secret = os.getenv("TWITTER_API_SECRET")
            access = os.getenv("TWITTER_ACCESS_TOKEN")
            access_secret = os.getenv("TWITTER_ACCESS_SECRET")

            if not all([api_key, api_secret, access, access_secret]):
                raise RuntimeError("Twitter credentials missing in .env")

            self._twitter_client = tweepy.Client(
                consumer_key=api_key,
                consumer_secret=api_secret,
                access_token=access,
                access_token_secret=access_secret,
            )
        else:
            self._twitter_client = None

        # --------------------------
        # Telegram (official bot api)
        # --------------------------
        if telegram_enabled:
            bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
            if not bot_token:
                raise RuntimeError("TELEGRAM_BOT_TOKEN missing in .env")

            self._telegram_bot = Bot(token=bot_token)
            self._telegram_chat_id = os.getenv("TELEGRAM_CHAT_ID") or "-1003444413940"
        else:
            self._telegram_bot = None
            self._telegram_chat_id = None

        gateway_url = os.getenv("NEOFS_GATEWAY_URL")
        self._neofs_gateway_url = gateway_url.rstrip("/") if gateway_url else None

    # --------------------------
    # NeoFS (unchanged)
    # --------------------------

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
        # unchanged body
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
            "reports": [r.to_agentcard_payload() for r in reports],
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
                logger.info("Stored decision in NeoFS container=%s object=%s",
                            upload_result.container_id,
                            upload_result.object_id)

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
                    logger.error("Giving up NeoFS upload after %s attempts", attempt)
                    return None
                await asyncio.sleep(1.5 * attempt)

    # --------------------------
    # Social broadcast
    # --------------------------

    async def broadcast(self, decision: SantaDecision) -> None:
        if not decision.publish:
            logger.info("Decision marked non-public; skipping social broadcast.")
            return

        long_message = self._format_broadcast(decision)
        tasks = []

        if self.twitter_enabled and self._twitter_client:
            tasks.append(self._send_tweet(long_message))

        if self.telegram_enabled and self._telegram_bot:
            tasks.append(self._send_telegram(long_message))

        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    # --------------------------
    # Twitter send
    # --------------------------

    async def _send_tweet(self, message: str) -> None:
        assert self._twitter_client is not None
        max_attempts = 3
        text = self._shorten_for_twitter(message, limit=280)

        for attempt in range(1, max_attempts + 1):
            try:
                self._twitter_client.create_tweet(text=text)
                logger.info("Posted decision to Twitter.")
                return
            except Exception as exc:
                logger.warning("Tweet failed (%s/%s): %s", attempt, max_attempts, exc)
                await asyncio.sleep(1.5 * attempt)

    # --------------------------
    # Telegram send
    # --------------------------

    async def _send_telegram(self, message: str) -> None:
        assert self._telegram_bot is not None
        max_attempts = 3

        for attempt in range(1, max_attempts + 1):
            try:
                await self._telegram_bot.send_message(
                chat_id=self._telegram_chat_id,
                text=message,
            )
                logger.info("Sent decision to Telegram.")
                return
            except TelegramError as exc:
                logger.warning("Telegram send failed (%s/%s): %s", attempt, max_attempts, exc)
                await asyncio.sleep(1.5 * attempt)

    # --------------------------
    # Formatting helpers (unchanged)
    # --------------------------

    @staticmethod
    def _format_broadcast(decision: SantaDecision) -> str:
        meta = decision.meta or {}
        token = meta.get("token") or meta.get("result", {}).get("token") or "this token"
        thesis = meta.get("thesis") or "(no thesis provided)"
        user_name = meta.get("user_name") or meta.get("result", {}).get("metadata", {}).get("user_name")
        wallet = meta.get("wallet_address")

        contributor = user_name or wallet or "a community member"

        santa_idea = (decision.verdict or "Santa opted to hold this signal.").strip()
        if decision.rationale:
            rationale = decision.rationale.strip()
            if len(rationale) < 160:
                santa_idea = f"{santa_idea} {rationale}"

        message = (
            "AlphaSanta has got a new Signal to Share with you! "
            f"From {contributor}, who's idea is: for {token}, {thesis}. "
            f"Santa's idea is: {santa_idea} #AlphaSanta"
        )
        return " ".join(message.split())

    @staticmethod
    def _shorten_for_twitter(message: str, limit: int = 275) -> str:
        if len(message) <= limit:
            return message
        return message[: limit - 1].rstrip() + "…"
