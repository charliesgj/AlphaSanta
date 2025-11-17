"""Turnkey helper for wallet-linked workflows."""

from __future__ import annotations

from typing import Optional

from spoon_ai.turnkey import Turnkey

from ..config import Settings


class TurnkeyService:
    """Lazy wrapper around spoon_ai Turnkey client."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._client: Optional[Turnkey] = None

    def enabled(self) -> bool:
        return self._settings.turnkey_enabled()

    def client(self) -> Turnkey:
        if not self.enabled():
            raise RuntimeError("Turnkey integration not configured")
        if self._client is None:
            self._client = Turnkey(
                base_url=self._settings.turnkey_base_url,
                api_public_key=self._settings.turnkey_public_key,
                api_private_key=self._settings.turnkey_private_key,
                org_id=self._settings.turnkey_org_id,
            )
        return self._client

    def whoami(self):  # pragma: no cover - simple passthrough
        return self.client().whoami()

    def sign_message(self, wallet_id: str, message: str):  # pragma: no cover
        return self.client().sign_message(sign_with=wallet_id, message=message)
