"""A2A persistence — SQLite store for submitted requests (and their approvals).

Design principle: keep ALL database access in this module. The rest of the app
calls create_request() / get_request() / list_requests() and never sees SQL, so
moving to a server DB (Postgres / SQL Server) later is a contained job — only
this file changes. The full answer set is stored as a JSON blob, so the schema
does not churn as the wizard evolves.

The DB path defaults to a2a.db beside this file; override with the A2A_DB env var
(set per-environment, e.g. /opt/trackon/A2A/a2a.db on the VM). The a2a_approvals
table is created now but only populated in Phase 3 (the approval workflow).
"""
import json
import os
import sqlite3
from datetime import datetime, timezone

DB_PATH = os.environ.get(
    "A2A_DB",
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "a2a.db"))


def get_db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db() -> None:
    with get_db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS a2a_requests (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                ref           TEXT UNIQUE,
                status        TEXT NOT NULL DEFAULT 'Submitted',
                purpose       TEXT,
                requester     TEXT,
                created_at    TEXT NOT NULL,
                answers_json  TEXT NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS a2a_approvals (
                id             INTEGER PRIMARY KEY AUTOINCREMENT,
                request_id     INTEGER NOT NULL,
                stage          TEXT NOT NULL,
                role           TEXT,
                approver_email TEXT,
                token          TEXT UNIQUE,
                decision       TEXT,
                comments       TEXT,
                decided_at     TEXT,
                FOREIGN KEY (request_id) REFERENCES a2a_requests(id)
            )
        """)
        # Phase-3 columns added after the table first shipped — add any missing
        # ones so existing dev DBs migrate without a drop/recreate.
        _add_column(conn, "a2a_approvals", "phase", "TEXT")
        _add_column(conn, "a2a_approvals", "status", "TEXT NOT NULL DEFAULT 'pending'")
        _add_column(conn, "a2a_approvals", "notified_at", "TEXT")


def _add_column(conn, table: str, column: str, decl: str) -> None:
    """Add `column` to `table` if it isn't already present (SQLite has no
    ADD COLUMN IF NOT EXISTS)."""
    existing = {r["name"] for r in conn.execute(f"PRAGMA table_info({table})")}
    if column not in existing:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {decl}")


def create_request(answers: dict) -> str:
    """Persist a submitted A2A and return its reference (e.g. 'A2A-0042')."""
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    with get_db() as conn:
        cur = conn.execute(
            "INSERT INTO a2a_requests (status, purpose, requester, created_at, "
            "answers_json) VALUES (?,?,?,?,?)",
            ("Submitted", answers.get("purpose", ""),
             answers.get("current_user", ""), now, json.dumps(answers)))
        rid = cur.lastrowid
        ref = f"A2A-{rid:04d}"
        conn.execute("UPDATE a2a_requests SET ref = ? WHERE id = ?", (ref, rid))
    return ref


def get_request(ref: str) -> dict | None:
    """Return a request as a dict (with answers parsed), or None if not found."""
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM a2a_requests WHERE ref = ?", (ref,)).fetchone()
    if not row:
        return None
    rec = dict(row)
    rec["answers"] = json.loads(rec.get("answers_json") or "{}")
    return rec


def list_requests(requester: str = "") -> list[dict]:
    """All requests (newest first), optionally filtered to one requester."""
    sql = "SELECT id, ref, status, purpose, requester, created_at FROM a2a_requests"
    params: tuple = ()
    if requester:
        sql += " WHERE requester = ?"
        params = (requester,)
    sql += " ORDER BY id DESC"
    with get_db() as conn:
        return [dict(r) for r in conn.execute(sql, params).fetchall()]


def set_request_status(request_id: int, status: str) -> None:
    with get_db() as conn:
        conn.execute("UPDATE a2a_requests SET status = ? WHERE id = ?",
                     (status, request_id))


def get_request_by_id(request_id: int) -> dict | None:
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM a2a_requests WHERE id = ?", (request_id,)).fetchone()
    if not row:
        return None
    rec = dict(row)
    rec["answers"] = json.loads(rec.get("answers_json") or "{}")
    return rec


# ---------------------------------------------------------------------------
# Approvals (Phase 3)
# ---------------------------------------------------------------------------
def create_approval(request_id: int, stage: str, role: str, phase: str,
                    approver_email: str, token: str) -> None:
    """Insert one pending approval row for a stage of a request."""
    with get_db() as conn:
        conn.execute(
            "INSERT INTO a2a_approvals (request_id, stage, role, phase, "
            "approver_email, token, status) VALUES (?,?,?,?,?,?, 'pending')",
            (request_id, stage, role, phase, approver_email, token))


def get_approval_by_token(token: str) -> dict | None:
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM a2a_approvals WHERE token = ?", (token,)).fetchone()
    return dict(row) if row else None


def list_approvals(request_id: int) -> list[dict]:
    with get_db() as conn:
        return [dict(r) for r in conn.execute(
            "SELECT * FROM a2a_approvals WHERE request_id = ? ORDER BY id",
            (request_id,)).fetchall()]


def record_decision(token: str, status: str, decision: str,
                    comments: str) -> None:
    """Set an approval's outcome (status: approved / rejected / referred)."""
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    with get_db() as conn:
        conn.execute(
            "UPDATE a2a_approvals SET status = ?, decision = ?, comments = ?, "
            "decided_at = ? WHERE token = ?",
            (status, decision, comments, now, token))


def mark_notified(approval_id: int) -> None:
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    with get_db() as conn:
        conn.execute("UPDATE a2a_approvals SET notified_at = ? WHERE id = ?",
                     (now, approval_id))


def phase_status(request_id: int, phase: str) -> dict:
    """Counts for a phase: {'total', 'approved', 'pending', 'blocked'} where
    blocked = rejected or referred."""
    rows = [a for a in list_approvals(request_id) if a["phase"] == phase]
    approved = sum(1 for a in rows if a["status"] == "approved")
    blocked = sum(1 for a in rows if a["status"] in ("rejected", "referred"))
    return {"total": len(rows), "approved": approved,
            "pending": len(rows) - approved - blocked, "blocked": blocked}
