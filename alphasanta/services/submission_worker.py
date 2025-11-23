"""Background worker that drains pending submissions from Supabase."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from typing import Any, Dict, Optional

from supabase import Client as SupabaseClient, create_client as create_supabase_client  # type: ignore

from ..schema import UserLetter

logger = logging.getLogger(__name__)


class SubmissionWorker:
    """Polls the Supabase submissions table and runs Santa on pending rows."""

    def __init__(
        self,
        app,
        *,
        poll_interval: float = 3.0,
    ) -> None:
        if not app.settings.supabase_enabled():
            raise RuntimeError("Supabase is not configured; cannot start submission worker.")
        self.app = app
        self.poll_interval = poll_interval
        self._client: SupabaseClient = create_supabase_client(
            app.settings.supabase_url,
            app.settings.supabase_key,
        )
        self._stopping = asyncio.Event()

    async def run_forever(self) -> None:
        """Run until cancelled/stop() is called."""
        logger.info("Submission worker started.")
        try:
            while not self._stopping.is_set():
                processed = await self._process_next()
                if not processed:
                    try:
                        await asyncio.wait_for(self._stopping.wait(), timeout=self.poll_interval)
                    except asyncio.TimeoutError:
                        continue
        finally:
            await self.app.shutdown()
            logger.info("Submission worker stopped.")

    def stop(self) -> None:
        """Signal the run loop to exit."""
        self._stopping.set()

    async def _process_next(self) -> bool:
        row = await asyncio.to_thread(self._fetch_pending_row)
        if not row:
            return False

        submission_id = str(row["submission_id"])
        claimed = await asyncio.to_thread(self._claim_submission, submission_id)
        if not claimed:
            # Another worker may have taken it.
            return True

        try:
            letter = self._letter_from_row(claimed)
        except ValueError as exc:
            logger.error("Submission %s missing required fields: %s", submission_id, exc)
            await asyncio.to_thread(self._mark_failed, submission_id, str(exc))
            return True

        logger.info(
            "Processing submission %s for user %s token=%s",
            submission_id,
            letter.user_id,
            letter.token,
        )
        try:
            decision = await self.app.run_single_letter(letter)
        except Exception as exc:  # pragma: no cover - defensive
            logger.exception("Santa processing failed for submission %s: %s", submission_id, exc)
            await asyncio.to_thread(self._mark_failed, submission_id, "Santa processing failed")
            return True

        await self.app.persistence.finalize_submission(submission_id, letter, decision)
        # SantaAgent already handled dissemination; worker only updates persistence.
        logger.info("Submission %s completed.", submission_id)
        return True


    # ------------------------------------------------------------------
    # Supabase helpers (run in executor threads)
    # ------------------------------------------------------------------

    def _fetch_pending_row(self) -> Optional[Dict[str, Any]]:
        response = (
            self._client.table("submissions")
            .select("*")
            .eq("status", "pending")
            .order("created_at", desc=False)
            .limit(1)
            .execute()
        )
        data = getattr(response, "data", None) or []
        return data[0] if data else None

    def _claim_submission(self, submission_id: str) -> Optional[Dict[str, Any]]:
        response = (
            self._client.table("submissions")
            .update(
                {
                    "status": "processing",
                    "updated_at": datetime.utcnow().isoformat(),
                }
            )
            .eq("submission_id", submission_id)
            .eq("status", "pending")
            .execute()
        )
        data = getattr(response, "data", None) or []
        if data:
            return data[0]
        return None

    def _mark_failed(self, submission_id: str, reason: str) -> None:
        payload = {
            "status": "failed",
            "updated_at": datetime.utcnow().isoformat(),
        }
        self._client.table("submissions").update(payload).eq("submission_id", submission_id).execute()

    # ------------------------------------------------------------------
    # Data transforms
    # ------------------------------------------------------------------

    def _letter_from_row(self, row: Dict[str, Any]) -> UserLetter:
        token_pair = row.get("token_pair")
        thesis = row.get("thesis")
        user_id = row.get("user_id")
        if not (token_pair and thesis and user_id):
            raise ValueError("token_pair, thesis, and user_id are required")

        source = "community"
        metadata: Dict[str, Any] = {}
        result = row.get("result") or {}
        if isinstance(result, dict):
            source = result.get("source", source)
            metadata = dict(result.get("metadata") or {})

        return UserLetter(
            token=token_pair,
            thesis=thesis,
            user_id=str(user_id),
            source=source,
            metadata=metadata,
        )
