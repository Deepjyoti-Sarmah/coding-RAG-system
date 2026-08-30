from __future__ import annotations
import json, sqlite3
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse
from ckg.cli import cmd_search, cmd_status, default_db_path
from session_memory import session_db_path
from .page import PAGE

def _candidate_dict(candidate):
    return {"symbol_name": candidate.symbol_name, "qualified_name": candidate.qualified_name,
            "kind": candidate.symbol_kind, "relative_path": candidate.relative_path,
            "score": candidate.score, "sources": list(candidate.sources)}

DEFAULT_PORT = 8765

class DashboardHandler(BaseHTTPRequestHandler):
    server_version = "CKGDashboard/1.0"
    def _send(self, data, status=200, content_type="application/json"):
        raw = data.encode() if isinstance(data, str) else json.dumps(data, separators=(",", ":")).encode()
        if len(raw) > 2_000_000: raw = b'{"error":"response too large"}'; status=500
        self.send_response(status); self.send_header("Content-Type", content_type+"; charset=utf-8"); self.send_header("Content-Length",str(len(raw))); self.end_headers(); self.wfile.write(raw)
    def do_GET(self):
        try:
            parsed=urlparse(self.path); path=parsed.path
            if ".." in path or "\\" in path: return self._send({"error":"invalid path"},400)
            if path=="/": return self._send(PAGE, content_type="text/html")
            if path=="/api/health": return self._health()
            if path=="/api/status": return self._status()
            if path=="/api/sessions": return self._sessions()
            if path.startswith("/api/sessions/"): return self._detail(path.rsplit("/",1)[1])
            if path=="/api/search": return self._search(parse_qs(parsed.query))
            return self._send({"error":"not found"},404)
        except Exception as e: return self._send({"error":str(e)},500)
    def _health(self):
        db=Path(self.server.project)/".ckg"/"index.sqlite"; sdb=Path(session_db_path(self.server.project))
        return self._send({"status":"ok","project_path":self.server.project,"index_present":db.exists(),"session_database_present":sdb.exists(),"schema_version":"session-v1"})
    def _status(self):
        db=default_db_path(self.server.project); out={"project":Path(self.server.project).name,"project_path":self.server.project,"index_generation":None,"document_count":0,"symbol_count":0,"chunk_count":0,"relationship_count":0,"active_sessions":0,"completed_sessions":0,"retrieval_events":0,"context_tokens":0,"baseline_tokens":0,"savings_percentage":None}
        if Path(db).exists():
            x=cmd_status(db); out.update(index_generation=x.get("generation"),document_count=x.get("documents",0),symbol_count=x.get("symbols",0),chunk_count=x.get("chunks",0))
            with sqlite3.connect(db) as c: out["relationship_count"]=c.execute("select count(*) from relationships").fetchone()[0]
        sdb=Path(session_db_path(self.server.project))
        if sdb.exists():
            with sqlite3.connect(sdb) as c:
                out["active_sessions"]=c.execute("select count(*) from sessions where status='active'").fetchone()[0]; out["completed_sessions"]=c.execute("select count(*) from sessions where status='completed'").fetchone()[0]
                out["retrieval_events"],out["context_tokens"],out["baseline_tokens"]=c.execute("select count(*),coalesce(sum(context_tokens),0),coalesce(sum(baseline_tokens),0) from retrieval_events").fetchone()
        if out["baseline_tokens"]: out["savings_percentage"]=round((1-out["context_tokens"]/out["baseline_tokens"])*100,2)
        return self._send(out)
    def _sessions(self):
        rows=[]; p=Path(session_db_path(self.server.project))
        if p.exists():
            with sqlite3.connect(p) as c:
                c.row_factory=sqlite3.Row
                for r in c.execute("select s.*, (select count(*) from session_events e where e.session_id=s.id) event_count,(select count(*) from decisions d where d.session_id=s.id) decision_count,(select count(*) from code_areas a where a.session_id=s.id) code_area_count,(select count(*) from retrieval_events v where v.session_id=s.id) retrieval_event_count from sessions s order by started_at desc limit 100"): rows.append(dict(r))
        return self._send({"sessions":rows})
    def _detail(self,sid):
        p=Path(session_db_path(self.server.project))
        if not p.exists(): return self._send({"error":"session not found"},404)
        with sqlite3.connect(p) as c:
            c.row_factory=sqlite3.Row; s=c.execute("select * from sessions where id=? and project_path=?",(sid,self.server.project)).fetchone()
            if not s:return self._send({"error":"session not found"},404)
            def all_(table): return [dict(x) for x in c.execute(f"select * from {table} where session_id=? order by timestamp,id",(sid,))]
            out={"session":dict(s),"decisions":all_("decisions"),"code_areas":all_("code_areas"),"retrieval_events":all_("retrieval_events")}
            out["token_totals"]={"context_tokens":sum(x["context_tokens"] for x in out["retrieval_events"]),"baseline_tokens":sum(x["baseline_tokens"] for x in out["retrieval_events"])}
        return self._send(out)
    def _search(self,q):
        query=(q.get("q") or [""])[0][:500]
        if not query:return self._send({"results":[]})
        db=default_db_path(self.server.project)
        if not Path(db).exists():return self._send({"error":"index not found"},404)
        r=cmd_search(db,query,top_k=10); out=[]
        for c in r.candidates: x=_candidate_dict(c); x["location"]=getattr(c,"location",None); out.append(x)
        return self._send({"results":out})
    def log_message(self,*args): pass

class DashboardServer(ThreadingHTTPServer):
    allow_reuse_address=True
    def __init__(self,address,project): self.project=str(Path(project).resolve()); super().__init__(address,DashboardHandler)
def create_server(project,host="127.0.0.1",port=DEFAULT_PORT): return DashboardServer((host,port),project)
