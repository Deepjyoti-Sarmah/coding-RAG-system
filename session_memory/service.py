"""Small, local-only, bounded session memory for CKG projects."""

from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any
from uuid import uuid4

MAX_TEXT = 2000
MAX_JSON = 4000


def session_db_path(project_path: str) -> str:
    return str(Path(project_path).resolve() / ".ckg" / "session.sqlite")


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _bounded(value: str | None, limit: int = MAX_TEXT) -> str:
    return (value or "")[:limit]


class SessionService:
    def __init__(self, project_path: str):
        self.project_path = str(Path(project_path).resolve())
        self.db_path = session_db_path(self.project_path)
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, timeout=10)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys=ON")
        conn.execute("PRAGMA busy_timeout=10000")
        return conn

    def _init_schema(self) -> None:
        with self._connect() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS sessions (
                    id TEXT PRIMARY KEY, project_path TEXT NOT NULL,
                    started_at TEXT NOT NULL, ended_at TEXT,
                    status TEXT NOT NULL CHECK(status IN ('active','completed','failed'))
                );
                CREATE INDEX IF NOT EXISTS idx_sessions_project ON sessions(project_path, started_at DESC);
                CREATE TABLE IF NOT EXISTS session_events (
                    id TEXT PRIMARY KEY, session_id TEXT NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
                    event_type TEXT NOT NULL, timestamp TEXT NOT NULL, metadata_json TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS decisions (
                    id TEXT PRIMARY KEY, session_id TEXT NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
                    decision TEXT NOT NULL, reason TEXT NOT NULL, timestamp TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS code_areas (
                    id TEXT PRIMARY KEY, session_id TEXT NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
                    file_path TEXT NOT NULL, description TEXT NOT NULL, timestamp TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS retrieval_events (
                    id TEXT PRIMARY KEY, session_id TEXT NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
                    query TEXT NOT NULL, selected_identifiers_json TEXT NOT NULL,
                    context_tokens INTEGER NOT NULL, baseline_tokens INTEGER NOT NULL,
                    latency_ms REAL NOT NULL, timestamp TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_events_session ON session_events(session_id, timestamp);
                CREATE INDEX IF NOT EXISTS idx_decisions_session ON decisions(session_id, timestamp);
                CREATE INDEX IF NOT EXISTS idx_areas_session ON code_areas(session_id, timestamp);
            """)

    def _session(self, row: sqlite3.Row) -> dict[str, Any]:
        return dict(row)

    def start(self) -> dict[str, Any]:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM sessions WHERE project_path=? AND status='active' ORDER BY started_at DESC LIMIT 1",
                (self.project_path,),
            ).fetchone()
            if row:
                return self._session(row)
            session_id = str(uuid4())
            timestamp = _now()
            conn.execute("INSERT INTO sessions VALUES (?, ?, ?, NULL, 'active')",
                         (session_id, self.project_path, timestamp))
            return self._session(conn.execute("SELECT * FROM sessions WHERE id=?", (session_id,)).fetchone())

    def resume(self, session_id: str | None = None) -> dict[str, Any] | None:
        with self._connect() as conn:
            if session_id:
                row = conn.execute("SELECT * FROM sessions WHERE id=? AND project_path=?", (session_id, self.project_path)).fetchone()
            else:
                row = conn.execute("SELECT * FROM sessions WHERE project_path=? AND status='active' ORDER BY started_at DESC LIMIT 1", (self.project_path,)).fetchone()
            return self._session(row) if row else None

    def end(self, session_id: str, status: str = "completed") -> dict[str, Any] | None:
        if status not in {"completed", "failed"}:
            raise ValueError("status must be completed or failed")
        with self._connect() as conn:
            conn.execute("UPDATE sessions SET ended_at=?, status=? WHERE id=? AND project_path=? AND status='active'",
                         (_now(), status, session_id, self.project_path))
            row = conn.execute("SELECT * FROM sessions WHERE id=? AND project_path=?", (session_id, self.project_path)).fetchone()
            return self._session(row) if row else None

    def list(self) -> list[dict[str, Any]]:
        with self._connect() as conn:
            return [self._session(row) for row in conn.execute("SELECT * FROM sessions WHERE project_path=? ORDER BY started_at DESC", (self.project_path,))]

    def status(self, session_id: str | None = None) -> dict[str, Any] | None:
        return self.resume(session_id)

    def _require(self, session_id: str | None) -> str:
        session = self.resume(session_id)
        if session is None:
            session = self.start() if session_id is None else None
        if session is None:
            raise ValueError("session not found for project")
        return session["id"]

    def event(self, event_type: str, metadata: dict[str, Any] | None = None, session_id: str | None = None) -> dict[str, Any]:
        payload = json.dumps(metadata or {}, separators=(",", ":"))
        if len(payload) > MAX_JSON:
            payload = json.dumps({"truncated": True}, separators=(",", ":"))
        event = {"id": str(uuid4()), "session_id": self._require(session_id), "event_type": _bounded(event_type, 100), "timestamp": _now(), "metadata": json.loads(payload)}
        with self._connect() as conn:
            conn.execute("INSERT INTO session_events VALUES (?, ?, ?, ?, ?)", (event["id"], event["session_id"], event["event_type"], event["timestamp"], payload))
        return event

    def decision(self, decision: str, reason: str = "", session_id: str | None = None) -> dict[str, Any]:
        item = {"id": str(uuid4()), "session_id": self._require(session_id), "decision": _bounded(decision), "reason": _bounded(reason), "timestamp": _now()}
        with self._connect() as conn:
            conn.execute("INSERT INTO decisions VALUES (?, ?, ?, ?, ?)", (item["id"], item["session_id"], item["decision"], item["reason"], item["timestamp"]))
        self.event("decision_recorded", {"decision_id": item["id"]}, item["session_id"])
        return item

    def code_area(self, file_path: str, description: str = "", session_id: str | None = None) -> dict[str, Any]:
        item = {"id": str(uuid4()), "session_id": self._require(session_id), "file_path": _bounded(file_path, 500), "description": _bounded(description), "timestamp": _now()}
        with self._connect() as conn:
            conn.execute("INSERT INTO code_areas VALUES (?, ?, ?, ?, ?)", (item["id"], item["session_id"], item["file_path"], item["description"], item["timestamp"]))
        self.event("code_area_recorded", {"code_area_id": item["id"]}, item["session_id"])
        return item

    def retrieval(self, query: str, selected_identifiers: list[str], context_tokens: int, baseline_tokens: int, latency_ms: float, session_id: str | None = None) -> dict[str, Any]:
        item = {"id": str(uuid4()), "session_id": self._require(session_id), "query": _bounded(query), "selected_identifiers": [_bounded(str(x), 500) for x in selected_identifiers[:50]], "context_tokens": max(0, int(context_tokens)), "baseline_tokens": max(0, int(baseline_tokens)), "latency_ms": max(0.0, float(latency_ms)), "timestamp": _now()}
        selected = json.dumps(item["selected_identifiers"], separators=(",", ":"))[:MAX_JSON]
        with self._connect() as conn:
            conn.execute("INSERT INTO retrieval_events VALUES (?, ?, ?, ?, ?, ?, ?, ?)", (item["id"], item["session_id"], item["query"], selected, item["context_tokens"], item["baseline_tokens"], item["latency_ms"], item["timestamp"]))
        return item

    def timeline(self, session_id: str | None = None, limit: int = 50) -> list[dict[str, Any]]:
        sid = self._require(session_id)
        limit = max(1, min(int(limit), 500))
        with self._connect() as conn:
            rows = []
            for row in conn.execute("SELECT id, event_type, timestamp, metadata_json FROM session_events WHERE session_id=?", (sid,)):
                rows.append({"id": row["id"], "session_id": sid, "type": row["event_type"], "timestamp": row["timestamp"], "metadata": json.loads(row["metadata_json"])})
            for row in conn.execute("SELECT id, timestamp, decision, reason FROM decisions WHERE session_id=?", (sid,)):
                rows.append({"id": row["id"], "session_id": sid, "type": "decision", "timestamp": row["timestamp"], "decision": row["decision"], "reason": row["reason"]})
            for row in conn.execute("SELECT id, timestamp, file_path, description FROM code_areas WHERE session_id=?", (sid,)):
                rows.append({"id": row["id"], "session_id": sid, "type": "code_area", "timestamp": row["timestamp"], "file_path": row["file_path"], "description": row["description"]})
            for row in conn.execute("SELECT id, timestamp, query, selected_identifiers_json, context_tokens, baseline_tokens, latency_ms FROM retrieval_events WHERE session_id=?", (sid,)):
                rows.append({"id": row["id"], "session_id": sid, "type": "retrieval", "timestamp": row["timestamp"], "query": row["query"], "selected_identifiers": json.loads(row["selected_identifiers_json"]), "context_tokens": row["context_tokens"], "baseline_tokens": row["baseline_tokens"], "latency_ms": row["latency_ms"]})
        return sorted(rows, key=lambda item: (item["timestamp"], item["id"]))[-limit:]  # type: ignore[index]  # pyright: ignore[reportArgumentType]

    def recall(self, query: str, limit: int = 10, session_id: str | None = None) -> list[dict[str, Any]]:
        sid = self._require(session_id)
        terms = [term for term in query.lower().split() if term][:8]
        if not terms:
            return []
        like = "%" + "%".join(terms) + "%"
        with self._connect() as conn:
            decisions = [dict(row) | {"type": "decision"} for row in conn.execute("SELECT id, session_id, decision, reason, timestamp FROM decisions WHERE session_id=? AND lower(decision || ' ' || reason) LIKE ? ORDER BY timestamp DESC LIMIT ?", (sid, like, min(max(limit, 1), 100)))]
            areas = [dict(row) | {"type": "code_area"} for row in conn.execute("SELECT id, session_id, file_path, description, timestamp FROM code_areas WHERE session_id=? AND lower(file_path || ' ' || description) LIKE ? ORDER BY timestamp DESC LIMIT ?", (sid, like, min(max(limit, 1), 100)))]
        return sorted(decisions + areas, key=lambda item: (item["timestamp"], item["id"]), reverse=True)[:max(1, min(limit, 100))]  # type: ignore[index]  # pyright: ignore[reportArgumentType,reportAttributeAccessIssue]

    def prune(self, days: int) -> dict[str, int]:
        cutoff = (datetime.now(UTC) - timedelta(days=max(0, int(days)))).isoformat()
        with self._connect() as conn:
            ids = [row[0] for row in conn.execute("SELECT id FROM sessions WHERE project_path=? AND started_at < ? AND status != 'active'", (self.project_path, cutoff))]
            for table in ("session_events", "decisions", "code_areas", "retrieval_events"):
                conn.executemany(f"DELETE FROM {table} WHERE session_id=?", [(sid,) for sid in ids])
            conn.executemany("DELETE FROM sessions WHERE id=?", [(sid,) for sid in ids])
        return {"sessions": len(ids), "events": len(ids)}

    def export(self, session_id: str | None = None, format: str = "json") -> str:
        session = self.resume(session_id)
        if session is None:
            raise ValueError("session not found for project")
        data = {"session": session, "timeline": self.timeline(session["id"], 500)}
        if format == "json":
            return json.dumps(data, indent=2, sort_keys=True)
        if format != "markdown":
            raise ValueError("format must be json or markdown")
        lines = [f"# CKG session {session['id']}", "", f"- Project: `{session['project_path']}`", f"- Status: {session['status']}", "", "## Timeline", ""]
        for item in data["timeline"]:
            detail = item.get("decision") or item.get("description") or item.get("query") or item.get("type")  # type: ignore[attr-defined]  # pyright: ignore[reportAttributeAccessIssue]
            lines.append(f"- `{item['timestamp']}` **{item['type']}**: {detail}")  # pyright: ignore[reportArgumentType]
        return "\n".join(lines) + "\n"
