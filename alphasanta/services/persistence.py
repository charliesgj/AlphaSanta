"""Lightweight persistence layer for AlphaSanta."""

from __future__ import annotations

import asyncio
import json
import sqlite3
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Iterable, Optional

from ..schema import UserLetter, CouncilResult, ElfReport, SantaDecision

_DEFAULT_SQLITE_PATH = Path("alphasanta.db")


class PersistenceService:
    """Stores submissions, elf reports, and Santa decisions."""

    def __init__(self, database_url: str) -> None:
        if database_url.startswith("sqlite:///"):
            self._path = Path(database_url.replace("sqlite:///", "", 1))
        else:
            raise ValueError("Only sqlite:/// URLs are supported in the reference implementation.")
        self._ensure_schema()

    def _ensure_schema(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self._path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS submissions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    token TEXT,
                    thesis TEXT,
                    source TEXT,
                    wallet_address TEXT,
                    user_id TEXT,
                    metadata TEXT,
                    created_at TEXT
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS elf_reports (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    submission_id INTEGER,
                    elf_id TEXT,
                    analysis TEXT,
                    confidence REAL,
                    rationale TEXT,
                    evidence TEXT,
                    meta TEXT,
                    FOREIGN KEY(submission_id) REFERENCES submissions(id)
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS santa_decisions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    submission_id INTEGER,
                    verdict TEXT,
                    publish INTEGER,
                    confidence REAL,
                    rationale TEXT,
                    neofs_object_id TEXT,
                    neofs_link TEXT,
                    meta TEXT,
                    source TEXT,
                    created_at TEXT,
                    FOREIGN KEY(submission_id) REFERENCES submissions(id)
                )
                """
            )

    async def record_council_and_decision(
        self,
        council_result: CouncilResult,
        decision: SantaDecision,
    ) -> None:
        await asyncio.to_thread(self._record_council_and_decision, council_result, decision)

    async def record_alpha_decision(
        self,
        letter: UserLetter,
        decision: SantaDecision,
    ) -> None:
        await asyncio.to_thread(self._record_alpha_decision, letter, decision)

    # ------- internal synchronous helpers -------

    def _record_council_and_decision(self, council_result: CouncilResult, decision: SantaDecision) -> None:
        with sqlite3.connect(self._path) as conn:
            cursor = conn.cursor()
            submission_id = self._insert_submission(cursor, council_result.user_letter)
            for report in council_result.reports:
                self._insert_report(cursor, submission_id, report)
            self._insert_decision(cursor, submission_id, decision)
            conn.commit()

    def _record_alpha_decision(self, letter: UserLetter, decision: SantaDecision) -> None:
        with sqlite3.connect(self._path) as conn:
            cursor = conn.cursor()
            submission_id = self._insert_submission(cursor, letter)
            self._insert_decision(cursor, submission_id, decision)
            conn.commit()

    # ------- insert helpers -------

    def _insert_submission(self, cursor: sqlite3.Cursor, letter: UserLetter) -> int:
        cursor.execute(
            """
            INSERT INTO submissions (token, thesis, source, wallet_address, user_id, metadata, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                letter.token,
                letter.thesis,
                letter.source,
                letter.wallet_address,
                letter.user_id,
                json.dumps(letter.metadata, ensure_ascii=False),
                datetime.utcnow().isoformat(),
            ),
        )
        return int(cursor.lastrowid)

    def _insert_report(self, cursor: sqlite3.Cursor, submission_id: int, report: ElfReport) -> None:
        cursor.execute(
            """
            INSERT INTO elf_reports (submission_id, elf_id, analysis, confidence, rationale, evidence, meta)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                submission_id,
                report.elf_id,
                report.analysis,
                report.confidence,
                report.rationale,
                json.dumps(report.evidence, ensure_ascii=False),
                json.dumps(report.meta, ensure_ascii=False),
            ),
        )

    def _insert_decision(self, cursor: sqlite3.Cursor, submission_id: int, decision: SantaDecision) -> None:
        cursor.execute(
            """
            INSERT INTO santa_decisions (
                submission_id, verdict, publish, confidence, rationale,
                neofs_object_id, neofs_link, meta, source, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                submission_id,
                decision.verdict,
                int(decision.publish),
                decision.confidence,
                decision.rationale,
                decision.neofs_object_id,
                decision.neofs_link,
                json.dumps(decision.meta, ensure_ascii=False),
                decision.source,
                datetime.utcnow().isoformat(),
            ),
        )
