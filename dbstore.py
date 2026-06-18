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
