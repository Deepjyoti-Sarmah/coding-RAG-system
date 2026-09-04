from __future__ import annotations

import json
import sqlite3
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, cast
from urllib.parse import parse_qs, urlparse

from session_memory import session_db_path
from symbolgraph.cli import (  # pyright: ignore[reportImportCycles]
    cmd_search,
    cmd_status,
    default_db_path,
)

from .page import PAGE


def _candidate_dict(candidate: Any) -> dict[str, Any]:
    return {"symbol_name": candidate.symbol_name, "qualified_name": candidate.qualified_name,
            "kind": candidate.symbol_kind, "relative_path": candidate.relative_path,
            "score": candidate.score, "sources": list(candidate.sources)}

DEFAULT_PORT = 8765

class DashboardServer(ThreadingHTTPServer):
    allow_reuse_address = True
    project: str
    def __init__(self, address: tuple[str, int], project: str | Path):
        self.project = str(Path(project).resolve())
        super().__init__(address, DashboardHandler)

class DashboardHandler(BaseHTTPRequestHandler):  # pyright: ignore[reportIncompatibleVariableOverride]
    server: Any  # type: ignore[assignment]  # pyright: ignore[reportIncompatibleVariableOverride]
    server_version = "SymbolgraphDashboard/1.0"
    def _check_auth(self) -> bool:
        import hmac
        import os

        token = os.environ.get("SG_DASHBOARD_TOKEN")
        if token:
            auth = self.headers.get("Authorization", "")
            if not hmac.compare_digest(f"Bearer {token}", auth):
                self._send({"error":"unauthorized"},401)
                return False
        site = self.headers.get("Sec-Fetch-Site", "")
        if site and site not in ("same-origin", "same-site", "none"):
            self._send({"error":"csrf"},403)
            return False
        return True

    def _send(self, data: Any, status: int = 200, content_type: str = "application/json") -> None:
        raw = data.encode() if isinstance(data, str) else json.dumps(data, separators=(",", ":")).encode()
        if len(raw) > 2_000_000: raw = b'{"error":"response too large"}'; status=500
        self.send_response(status); self.send_header("Content-Type", content_type+"; charset=utf-8"); self.send_header("Content-Length",str(len(raw))); self.end_headers(); self.wfile.write(raw)
    def do_GET(self) -> None:
        if not self._check_auth():
            return
        try:
            parsed=urlparse(self.path); path=parsed.path
            if ".." in path or "\\" in path: return self._send({"error":"invalid path"},400)
            if path=="/": return self._send(PAGE, content_type="text/html")
            if path=="/api/health": return self._health()
            if path=="/api/status": return self._status()
            if path=="/api/sessions": return self._sessions()
            if path.startswith("/api/sessions/"): return self._detail(path.rsplit("/",1)[1])
            if path=="/api/metrics": return self._metrics()
            if path=="/api/search": return self._search(parse_qs(parsed.query))
            return self._send({"error":"not found"},404)
        except Exception as e:
            return self._send({"error":str(e)},500)
    def do_POST(self) -> None:
        if not self._check_auth():
            return
        parsed = urlparse(self.path)
        if parsed.path == "/api/reindex":
            try:
                import subprocess
                import sys

                subprocess.Popen([sys.executable, "-m", "symbolgraph.cli", "index", cast(DashboardServer, self.server).project], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                return self._send({"status": "reindex started"})
            except Exception as e:
                return self._send({"error": str(e)}, 500)
        self._send({"error":"not found"},404)

    def do_DELETE(self) -> None:
        if not self._check_auth():
            return
        parsed = urlparse(self.path)
        if parsed.path.startswith("/api/files/"):
            rel = parsed.path[len("/api/files/"):]
            if ".." in rel or "\\" in rel or rel.startswith("/"):
                return self._send({"error":"invalid path"},400)
            # guard within project
            project = cast(DashboardServer, self.server).project
            try:
                target = (Path(project) / rel).resolve()
                target.relative_to(Path(project).resolve())
            except ValueError:
                return self._send({"error":"invalid path"},400)
            # purge from index
            db = default_db_path(project)
            if Path(db).exists():
                try:
                    from storage import db as sdb

                    conn = sdb.connect(db)
                    try:
                        from storage.index_store import _purge_paths  # type: ignore

                        with sdb.transaction(conn):
                            _purge_paths(conn, {rel})
                        conn.commit()
                    finally:
                        conn.close()
                except Exception:
                    pass
            fp = Path(project) / rel
            if fp.exists():
                try:
                    fp.unlink()
                except OSError:
                    pass
            return self._send({"status":"deleted","path":rel})
        self._send({"error":"not found"},404)
    def _health(self) -> None:
        project = cast(DashboardServer, self.server).project
        db=Path(project)/".sg"/"index.sqlite"; sdb=Path(session_db_path(project))
        return self._send({"status":"ok","project_path":project,"index_present":db.exists(),"session_database_present":sdb.exists(),"schema_version":"session-v1"})
    def _status(self) -> None:
        project = cast(DashboardServer, self.server).project
        db=default_db_path(project); out: dict[str, Any]={"project":Path(project).name,"project_path":project,"index_generation":None,"document_count":0,"symbol_count":0,"chunk_count":0,"relationship_count":0,"active_sessions":0,"completed_sessions":0,"retrieval_events":0,"context_tokens":0,"baseline_tokens":0,"savings_percentage":None}
        if Path(db).exists():
            x=cmd_status(db); out.update(index_generation=x.get("generation"),document_count=x.get("documents",0),symbol_count=x.get("symbols",0),chunk_count=x.get("chunks",0))
            with sqlite3.connect(db) as c: out["relationship_count"]=c.execute("select count(*) from relationships").fetchone()[0]
        sdb=Path(session_db_path(project))
        if sdb.exists():
            with sqlite3.connect(sdb) as c:
                out["active_sessions"]=c.execute("select count(*) from sessions where status='active'").fetchone()[0]; out["completed_sessions"]=c.execute("select count(*) from sessions where status='completed'").fetchone()[0]
                out["retrieval_events"],out["context_tokens"],out["baseline_tokens"]=c.execute("select count(*),coalesce(sum(context_tokens),0),coalesce(sum(baseline_tokens),0) from retrieval_events").fetchone()
        if out["baseline_tokens"]:  # type: ignore[truthy-function]
            ct = int(out["context_tokens"])  # type: ignore[arg-type]
            bt = int(out["baseline_tokens"])  # type: ignore[arg-type]
            if bt:
                out["savings_percentage"]=round((1-ct/bt)*100,2)
        return self._send(out)
    def _sessions(self) -> None:
        project = cast(DashboardServer, self.server).project
        rows: list[dict[str, Any]]=[]; p=Path(session_db_path(project))
        if p.exists():
            with sqlite3.connect(p) as c:
                c.row_factory=sqlite3.Row
                for r in c.execute("select s.*, (select count(*) from session_events e where e.session_id=s.id) event_count,(select count(*) from decisions d where d.session_id=s.id) decision_count,(select count(*) from code_areas a where a.session_id=s.id) code_area_count,(select count(*) from retrieval_events v where v.session_id=s.id) retrieval_event_count from sessions s order by started_at desc limit 100"): rows.append(dict(r))
        return self._send({"sessions":rows})
    def _detail(self,sid: str) -> None:
        project = cast(DashboardServer, self.server).project
        p=Path(session_db_path(project))
        if not p.exists(): return self._send({"error":"session not found"},404)
        with sqlite3.connect(p) as c:
            c.row_factory=sqlite3.Row; s=c.execute("select * from sessions where id=? and project_path=?",(sid,project)).fetchone()
            if not s:return self._send({"error":"session not found"},404)
            def all_(table: str) -> list[dict[str, Any]]: return [dict(x) for x in c.execute(f"select * from {table} where session_id=? order by timestamp,id",(sid,))]
            out: dict[str, Any]={"session":dict(s),"decisions":all_("decisions"),"code_areas":all_("code_areas"),"retrieval_events":all_("retrieval_events")}
            out["token_totals"]={"context_tokens":sum(x["context_tokens"] for x in out["retrieval_events"]),"baseline_tokens":sum(x["baseline_tokens"] for x in out["retrieval_events"])}
        return self._send(out)
    def _metrics(self) -> None:
        import sqlite3
        import time
        project = cast(DashboardServer, self.server).project
        db = default_db_path(project)
        out: dict[str, Any] = {"merkle_root": None, "generation": None, "timestamp": int(time.time())}
        if Path(db).exists():
            try:
                with sqlite3.connect(db) as c:
                    row = c.execute("SELECT value FROM index_metadata WHERE key='merkle_root'").fetchone()
                    if row:
                        out["merkle_root"] = row[0]
                    row = c.execute("SELECT value FROM index_metadata WHERE key='generation'").fetchone()
                    if row:
                        out["generation"] = row[0]
            except Exception:
                pass
        return self._send(out)

    def _search(self,q: dict[str, list[str]]) -> None:
        project = cast(DashboardServer, self.server).project
        query=(q.get("q") or [""])[0][:500]
        if not query:return self._send({"results":[]})
        db=default_db_path(project)
        if not Path(db).exists():return self._send({"error":"index not found"},404)
        r=cmd_search(db,query,top_k=10); out: list[dict[str, Any]]=[]
        for c in r.candidates: x=_candidate_dict(c); x["location"]=getattr(c,"location",None); out.append(x)
        return self._send({"results":out})
    def log_message(self, format: str, *args: Any) -> None: pass

def create_server(project: str | Path,host: str ="127.0.0.1",port: int =DEFAULT_PORT) -> DashboardServer: return DashboardServer((host,port),project)
