# -*- coding: utf-8 -*-
"""jobs.py — persistent job store (SQLite).

States: queued → researching → awaiting_approval → rendering → completed
        (or failed / cancelled at any point)

Design notes
------------
* One short-lived SQLite connection per call → safe from multiple threads.
* WAL mode so a reader never blocks a writer.
* ``updates`` table de-duplicates Telegram updates so a repeated delivery can
  never launch a second render for the same job.
"""
import json
import os
import random
import sqlite3
import string
import time
from typing import Any, Dict, List, Optional

STATES = (
    "queued", "researching", "awaiting_research_review", "awaiting_concept_review",
    "awaiting_approval", "rendering", "completed", "failed", "cancelled",
)

# States where the *machine* is working. A service restart during one of these
# means the work did not finish, so they are the ones recovery marks failed.
WORKING_STATES = ("queued", "researching", "rendering")

# States where the job is waiting for a human decision. They survive a restart
# untouched (a paused job is not a crashed job) and are still "in flight" for
# duplicate-prevention purposes, exactly like the pre-existing approval gate.
PAUSED_STATES = ("awaiting_research_review", "awaiting_concept_review",
                 "awaiting_approval")

ACTIVE_STATES = WORKING_STATES + PAUSED_STATES
TERMINAL_STATES = ("completed", "failed", "cancelled")

# Statuses a staged job may legitimately be resumed from.
RESUMABLE_STATES = ("queued",) + PAUSED_STATES

_SCHEMA = """
CREATE TABLE IF NOT EXISTS jobs (
    id            TEXT PRIMARY KEY,
    user_id       INTEGER NOT NULL,
    chat_id       INTEGER,
    status        TEXT NOT NULL,
    style         TEXT NOT NULL,
    language      TEXT NOT NULL,
    duration_sec  INTEGER,
    firm_name     TEXT,
    params_json   TEXT NOT NULL DEFAULT '{}',
    progress      INTEGER NOT NULL DEFAULT 0,
    message       TEXT DEFAULT '',
    error         TEXT DEFAULT '',
    output_dir    TEXT,
    created_at    REAL NOT NULL,
    updated_at    REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_jobs_user ON jobs(user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status);

CREATE TABLE IF NOT EXISTS events (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id    TEXT NOT NULL,
    at        REAL NOT NULL,
    kind      TEXT NOT NULL,
    text      TEXT NOT NULL DEFAULT ''
);
CREATE INDEX IF NOT EXISTS idx_events_job ON events(job_id, id);

CREATE TABLE IF NOT EXISTS approvals (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id        TEXT NOT NULL,
    stage         TEXT NOT NULL,           -- 'research' | 'concept' | 'storyboard'
    decision      INTEGER NOT NULL,        -- 1=approved, 0=rejected
    actor_ref     TEXT NOT NULL,           -- Telegram user ID who decided
    timestamp     REAL NOT NULL,           -- when the decision was made
    artifact_hash TEXT NOT NULL DEFAULT '',  -- SHA-256 of the artifact at approval time
    idempotency_key TEXT NOT NULL DEFAULT '',  -- caller-generated token for dedupe
    UNIQUE(job_id, stage)
);

CREATE TABLE IF NOT EXISTS seen_updates (
    update_id  INTEGER PRIMARY KEY,
    job_id     TEXT,
    seen_at    REAL NOT NULL
);
"""


def new_job_id() -> str:
    """Human-friendly, collision-resistant job id, e.g. ``J7F3K2Q9``."""
    alphabet = string.ascii_uppercase + string.digits
    return "J" + "".join(random.choice(alphabet) for _ in range(8))


class JobStore(object):
    def __init__(self, db_path: str):
        self.db_path = db_path
        parent = os.path.dirname(os.path.abspath(db_path))
        if parent:
            os.makedirs(parent, exist_ok=True)
        self._init()

    # ------------------------------------------------------------------ plumbing
    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, timeout=30.0)
        conn.row_factory = sqlite3.Row
        try:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA busy_timeout=30000")
        except sqlite3.Error:
            pass
        return conn

    def _init(self) -> None:
        conn = self._connect()
        try:
            conn.executescript(_SCHEMA)
            conn.commit()
        finally:
            conn.close()

    # ------------------------------------------------------------------ create
    def create(self, user_id: int, style: str, language: str,
               firm_name: str = "", duration_sec: Optional[int] = None,
               chat_id: Optional[int] = None,
               params: Optional[Dict[str, Any]] = None) -> str:
        if style not in ("motion", "illustrated", "blender3d"):
            raise ValueError("unknown style: %r" % (style,))
        jid = new_job_id()
        now = time.time()
        conn = self._connect()
        try:
            conn.execute(
                "INSERT INTO jobs (id,user_id,chat_id,status,style,language,"
                "duration_sec,firm_name,params_json,progress,message,error,"
                "output_dir,created_at,updated_at) "
                "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (jid, int(user_id), chat_id, "queued", style, language,
                 duration_sec, firm_name, json.dumps(params or {}),
                 0, "queued", "", None, now, now),
            )
            conn.commit()
        finally:
            conn.close()
        self.log_event(jid, "created", "style=%s language=%s" % (style, language))
        return jid

    # ------------------------------------------------------------------ read
    def get(self, job_id: str) -> Optional[Dict[str, Any]]:
        conn = self._connect()
        try:
            row = conn.execute("SELECT * FROM jobs WHERE id=?", (job_id,)).fetchone()
        finally:
            conn.close()
        return dict(row) if row else None

    def list_for_user(self, user_id: int, limit: int = 10) -> List[Dict[str, Any]]:
        conn = self._connect()
        try:
            rows = conn.execute(
                "SELECT * FROM jobs WHERE user_id=? ORDER BY created_at DESC LIMIT ?",
                (int(user_id), int(limit)),
            ).fetchall()
        finally:
            conn.close()
        return [dict(r) for r in rows]

    def list_by_status(self, status: str, limit: int = 50) -> List[Dict[str, Any]]:
        conn = self._connect()
        try:
            rows = conn.execute(
                "SELECT * FROM jobs WHERE status = ? ORDER BY updated_at ASC LIMIT ?",
                (status, int(limit))).fetchall()
        finally:
            conn.close()
        return [dict(r) for r in rows]

    def list_active(self, limit: int = 20) -> List[Dict[str, Any]]:
        marks = ",".join("?" for _ in ACTIVE_STATES)
        conn = self._connect()
        try:
            rows = conn.execute(
                "SELECT * FROM jobs WHERE status IN (%s) "
                "ORDER BY created_at ASC LIMIT ?" % marks,
                list(ACTIVE_STATES) + [int(limit)],
            ).fetchall()
        finally:
            conn.close()
        return [dict(r) for r in rows]

    def active_count(self) -> int:
        marks = ",".join("?" for _ in ACTIVE_STATES)
        conn = self._connect()
        try:
            row = conn.execute(
                "SELECT COUNT(*) AS n FROM jobs WHERE status IN (%s)" % marks,
                list(ACTIVE_STATES),
            ).fetchone()
        finally:
            conn.close()
        return int(row["n"]) if row else 0

    def rendering_count(self) -> int:
        conn = self._connect()
        try:
            row = conn.execute(
                "SELECT COUNT(*) AS n FROM jobs WHERE status='rendering'").fetchone()
        finally:
            conn.close()
        return int(row["n"]) if row else 0

    def find_active_for_user(self, user_id: int) -> Optional[Dict[str, Any]]:
        marks = ",".join("?" for _ in ACTIVE_STATES)
        conn = self._connect()
        try:
            row = conn.execute(
                "SELECT * FROM jobs WHERE user_id=? AND status IN (%s) "
                "ORDER BY created_at DESC LIMIT 1" % marks,
                [int(user_id)] + list(ACTIVE_STATES),
            ).fetchone()
        finally:
            conn.close()
        return dict(row) if row else None

    # ------------------------------------------------------------------ update
    def update(self, job_id: str, **fields: Any) -> None:
        allowed = {"status", "progress", "message", "error", "output_dir",
                   "chat_id", "duration_sec", "firm_name", "params_json"}
        sets, vals = [], []
        for k, v in fields.items():
            if k not in allowed:
                continue
            if k == "params_json" and not isinstance(v, str):
                v = json.dumps(v)
            sets.append("%s=?" % k)
            vals.append(v)
        if not sets:
            return
        sets.append("updated_at=?")
        vals.append(time.time())
        vals.append(job_id)
        conn = self._connect()
        try:
            conn.execute("UPDATE jobs SET %s WHERE id=?" % ",".join(sets), vals)
            conn.commit()
        finally:
            conn.close()

    def set_status(self, job_id: str, status: str, message: str = "",
                   progress: Optional[int] = None) -> None:
        if status not in STATES:
            raise ValueError("unknown status: %r" % (status,))
        fields = {"status": status, "message": message}
        if progress is not None:
            fields["progress"] = max(0, min(100, int(progress)))
        self.update(job_id, **fields)
        self.log_event(job_id, "status", "%s: %s" % (status, message))

    def claim_transition(self, job_id: str, expected: Any, to: str,
                         message: str = "",
                         progress: Optional[int] = None) -> bool:
        """Atomically move a job out of an expected status, at most once.

        This is the duplicate-execution guard. The check and the write are a
        single conditional ``UPDATE``, so if two callers (a retried Telegram
        delivery, a double-clicked resume, two threads) try to run the same
        phase for the same job, exactly one of them gets ``True`` and the other
        gets ``False`` and must stop. A read-then-write pair cannot guarantee
        that under SQLite's connection-per-call model.

        ``expected`` may be a single status or an iterable of acceptable ones.
        Returns ``True`` only for the caller that performed the transition.
        """
        if to not in STATES:
            raise ValueError("unknown status: %r" % (to,))
        if isinstance(expected, str):
            wanted = (expected,)
        else:
            wanted = tuple(expected)
        for want in wanted:
            if want not in STATES:
                raise ValueError("unknown status: %r" % (want,))
        if not wanted:
            return False

        marks = ",".join("?" for _ in wanted)
        sets = "status=?, message=?, updated_at=?"
        vals: List[Any] = [to, message, time.time()]
        if progress is not None:
            sets += ", progress=?"
            vals.append(max(0, min(100, int(progress))))
        # Placeholders appear in SQL order: the SET list, then ``id=?``, then the
        # IN (...) list. Binding these out of order silently matched no row.
        vals.append(job_id)
        vals.extend(wanted)

        conn = self._connect()
        try:
            cur = conn.execute(
                "UPDATE jobs SET %s WHERE id=? AND status IN (%s)" % (sets, marks),
                vals)
            conn.commit()
            won = cur.rowcount > 0
        finally:
            conn.close()
        if won:
            self.log_event(job_id, "status", "%s: %s" % (to, message))
        return won

    def request_cancel(self, job_id: str) -> bool:
        job = self.get(job_id)
        if not job or job["status"] in TERMINAL_STATES:
            return False
        self.set_status(job_id, "cancelled", "cancelled by user")
        return True

    def is_cancelled(self, job_id: str) -> bool:
        job = self.get(job_id)
        return bool(job and job["status"] == "cancelled")

    def fail(self, job_id: str, error: str) -> None:
        from .security import redact
        self.update(job_id, status="failed", error=redact(error)[:2000],
                    message="failed")
        self.log_event(job_id, "error", redact(error)[:2000])

    # ------------------------------------------------------------------ events
    def log_event(self, job_id: str, kind: str, text: str = "") -> None:
        from .security import redact
        conn = self._connect()
        try:
            conn.execute(
                "INSERT INTO events (job_id, at, kind, text) VALUES (?,?,?,?)",
                (job_id, time.time(), kind, redact(text)[:4000]),
            )
            conn.commit()
        finally:
            conn.close()

    def events(self, job_id: str, limit: int = 100) -> List[Dict[str, Any]]:
        conn = self._connect()
        try:
            rows = conn.execute(
                "SELECT at,kind,text FROM events WHERE job_id=? ORDER BY id ASC LIMIT ?",
                (job_id, int(limit)),
            ).fetchall()
        finally:
            conn.close()
        return [dict(r) for r in rows]

    # ------------------------------------------------------------------ dedupe
    def seen_update(self, update_id: int) -> bool:
        conn = self._connect()
        try:
            row = conn.execute(
                "SELECT 1 FROM seen_updates WHERE update_id=?", (int(update_id),)).fetchone()
        finally:
            conn.close()
        return row is not None

    def mark_update(self, update_id: int, job_id: Optional[str] = None) -> bool:
        """Record an update. Returns False if it was already seen (duplicate)."""
        conn = self._connect()
        try:
            cur = conn.execute(
                "INSERT OR IGNORE INTO seen_updates (update_id, job_id, seen_at) "
                "VALUES (?,?,?)", (int(update_id), job_id, time.time()))
            conn.commit()
            return cur.rowcount > 0
        finally:
            conn.close()

    # ------------------------------------------------------------------ approvals
    def record_approval(self, job_id: str, stage: str, decision: int,
                        actor_ref: str, artifact_hash: str = "",
                        idempotency_key: str = "") -> None:
        """Persist a human decision at a staged gate.

        ``decision`` is ``1`` for approved, ``0`` for rejected.
        The ``artifact_hash`` is used for fail-closed checking: the render
        step will only proceed if the current artifact hash matches the
        hash that was recorded when the approval was given.
        """
        conn = self._connect()
        try:
            conn.execute(
                """INSERT OR REPLACE INTO approvals (job_id, stage, decision, actor_ref,
                   timestamp, artifact_hash, idempotency_key)
                   VALUES (?,?,?,?,?,?,?)""",
                (job_id, stage, decision, actor_ref, time.time(),
                 artifact_hash, idempotency_key))
            conn.commit()
        finally:
            conn.close()

    def approval_exists(self, job_id: str, stage: str) -> bool:
        """Return True if an approval record exists for this stage."""
        conn = self._connect()
        try:
            row = conn.execute(
                "SELECT 1 FROM approvals WHERE job_id=? AND stage=? LIMIT 1",
                (job_id, stage)).fetchone()
        finally:
            conn.close()
        return row is not None

    def get_approval_hash(self, job_id: str, stage: str) -> str:
        """Return the artifact_hash recorded at approval time, or ''."""
        conn = self._connect()
        try:
            row = conn.execute(
                "SELECT artifact_hash FROM approvals WHERE job_id=? AND stage=? LIMIT 1",
                (job_id, stage)).fetchone()
        finally:
            conn.close()
        return row["artifact_hash"] if row else ""

    def delete_approval(self, job_id: str, stage: str) -> None:
        """Remove the approval record for one stage.

        Used when the artefact the approval covered changes: the old sign-off
        can no longer cover the new artefact, so it is withdrawn rather than
        left to look valid. Only the named stage is removed, so an approved
        research or concept decision is never thrown away by a later change.
        """
        conn = self._connect()
        try:
            conn.execute("DELETE FROM approvals WHERE job_id=? AND stage=?",
                         (job_id, stage))
            conn.commit()
        finally:
            conn.close()

    def approve_record(self, job_id: str, stage: str) -> Optional[Dict[str, Any]]:
        """Return the stored approval record for a stage, or ``None``."""
        conn = self._connect()
        try:
            row = conn.execute(
                "SELECT job_id, stage, decision, actor_ref, timestamp, "
                "artifact_hash, idempotency_key FROM approvals "
                "WHERE job_id=? AND stage=? LIMIT 1",
                (job_id, stage)).fetchone()
        finally:
            conn.close()
        return dict(row) if row else None

    # ------------------------------------------------------------------ recovery
    def recover_interrupted(self) -> List[str]:
        """Mark jobs left mid-flight by a crash/restart as failed (honest state)."""
        marks = ",".join("?" for _ in ("researching", "rendering"))
        conn = self._connect()
        try:
            rows = conn.execute(
                "SELECT id FROM jobs WHERE status IN (%s)" % marks,
                ("researching", "rendering"),
            ).fetchall()
            ids = [r["id"] for r in rows]
            for jid in ids:
                conn.execute(
                    "UPDATE jobs SET status='failed', "
                    "error='interrupted by service restart', message='failed', "
                    "updated_at=? WHERE id=?", (time.time(), jid))
            conn.commit()
        finally:
            conn.close()
        for jid in ids:
            self.log_event(jid, "recovery", "marked failed after restart")
        return ids

    def cleanup_old(self, keep_days: int = 30) -> int:
        """Delete *records* for old terminal jobs (never deletes output files)."""
        cutoff = time.time() - keep_days * 86400
        conn = self._connect()
        try:
            marks = ",".join("?" for _ in TERMINAL_STATES)
            cur = conn.execute(
                "DELETE FROM jobs WHERE status IN (%s) AND updated_at < ?" % marks,
                list(TERMINAL_STATES) + [cutoff])
            conn.commit()
            return cur.rowcount
        finally:
            conn.close()
