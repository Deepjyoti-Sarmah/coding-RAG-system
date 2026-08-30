"""Task-level A/B runner using a file-based real-agent protocol."""
from __future__ import annotations
import argparse,json,os,shutil,subprocess,tempfile,time,sys
from pathlib import Path
from .ab_metrics import score,summarize,write_report

MAX_OUTPUT=8000; METRICS=("input_tokens","output_tokens","total_tokens","tool_calls","ckg_tools_used","ckg_queries")
class AgentRunner:
    def run(self,task,condition,worktree): raise NotImplementedError

def _metric(value,name):
    if value is None:return None
    if isinstance(value,bool) or not isinstance(value,int) or value<0:raise ValueError(f"{name} must be a non-negative integer or null")
    return value
def parse_result(path):
    try:data=json.loads(Path(path).read_text(encoding="utf-8"))
    except FileNotFoundError as e:raise ValueError("agent did not create result file") from e
    except (json.JSONDecodeError,OSError) as e:raise ValueError(f"malformed result JSON: {e}") from e
    if not isinstance(data,dict) or data.get("status") not in ("success","failure"):raise ValueError("result status must be success or failure")
    for key in ("changed_files","files_found","symbols_found"):
        if key not in data or not isinstance(data[key],list) or not all(isinstance(x,str) for x in data[key]):raise ValueError(f"{key} must be an array of strings")
    for key in METRICS:data[key]=_metric(data.get(key),key)
    if "tests_passed" in data and data["tests_passed"] is not None and not isinstance(data["tests_passed"],bool):raise ValueError("tests_passed must be boolean or null")
    data["notes"]=str(data.get("notes",""))[:2000];return data

class SubprocessAgentRunner(AgentRunner):
    def __init__(self,template,timeout=None):self.template=template;self.timeout=timeout
    def run(self,task,condition,worktree):
        run_dir=Path(tempfile.mkdtemp(prefix="agent-run-",dir=worktree));prompt=run_dir/"prompt.txt";result_file=run_dir/"result.json";prompt.write_text(task["prompt"],encoding="utf-8")
        env=os.environ.copy();env.update(CKG_AB_TASK_ID=task["id"],CKG_AB_CONDITION=condition,CKG_AB_WORKTREE=str(worktree),CKG_AB_PROMPT_FILE=str(prompt),CKG_AB_RESULT_FILE=str(result_file),CKG_AB_PROJECT=str(worktree))
        config=worktree/".mcp.json"; index=worktree/".ckg"/"index.sqlite"
        if condition=="with_ckg" and config.exists() and index.exists(): env.update(CKG_AB_MCP_CONFIG=str(config),CKG_AB_INDEX=str(index))
        else: env.pop("CKG_AB_MCP_CONFIG",None);env.pop("CKG_AB_INDEX",None)
        started=time.monotonic()
        base={"files_changed":[],"files_found":[],"symbols_found":[],"input_tokens":None,"output_tokens":None,"total_tokens":None,"tool_calls":None,"ckg_tools_used":None,"ckg_queries":None,"stdout":"","stderr":"","timed_out":False}
        try:
            p=subprocess.run(self.template,shell=True,cwd=worktree,env=env,text=True,capture_output=True,timeout=self.timeout or task["timeout"]);base.update(exit_code=p.returncode,stdout=p.stdout[-MAX_OUTPUT:],stderr=p.stderr[-MAX_OUTPUT:])
            if result_file.exists():base.update(parse_result(result_file))
            else:base.update(status="failure",failure_reason="agent did not create result file")
        except subprocess.TimeoutExpired as e:base.update(exit_code=None,timed_out=True,status="failure",failure_reason="agent timed out",stdout=str(e.stdout or "")[-MAX_OUTPUT:],stderr=str(e.stderr or "")[-MAX_OUTPUT:])
        except ValueError as e:base.update(exit_code=p.returncode if "p" in locals() else None,status="failure",failure_reason=str(e))
        base["elapsed_seconds"]=time.monotonic()-started
        base["files_changed"]=_git_changed(worktree) if not base.get("changed_files") else base["changed_files"];shutil.rmtree(run_dir,ignore_errors=True);return base
def _git_changed(worktree):
    try:return subprocess.run(["git","-C",str(worktree),"diff","--name-only"],text=True,capture_output=True,timeout=10).stdout.splitlines()
    except (OSError,subprocess.SubprocessError):return []

class FakeAgentRunner(AgentRunner):
    def run(self,task,condition,worktree):
        ok=condition=="with_ckg" or task["id"] in {"py-auth","js-auth","go-auth"};data={"status":"success" if ok else "failure","changed_files":[],"files_found":task["expected_files"] if ok else [],"symbols_found":task["expected_symbols"] if ok else [],"input_tokens":100,"output_tokens":30,"total_tokens":130,"tool_calls":2 if condition=="with_ckg" else 0,"ckg_tools_used":None,"ckg_queries":None,"tests_passed":ok,"notes":"deterministic fake"};path=Path(worktree)/"fake-result.json";path.write_text(json.dumps(data));parsed=parse_result(path);parsed["files_changed"]=parsed["changed_files"];return dict(parsed,exit_code=0 if ok else 1,elapsed_seconds=.01)
def load_tasks(path):
    tasks=json.loads(Path(path).read_text());assert len(tasks)==20,"manifest must contain exactly 20 tasks";return tasks
def _provision_ckg(worktree):
    db=worktree/".ckg"/"index.sqlite";subprocess.run([sys.executable,"-m","ckg.cli","index",str(worktree)],cwd=Path(__file__).resolve().parents[1],capture_output=True,timeout=120,check=True);config=worktree/".mcp.json";config.write_text(json.dumps({"mcpServers":{"ckg":{"command":"ckg-mcp"}}}));
    parsed=json.loads(config.read_text());assert parsed["mcpServers"]["ckg"]["command"]=="ckg-mcp" and db.exists();return db,config
def _validate_condition(worktree, condition):
    db=worktree/".ckg"/"index.sqlite";config=worktree/".mcp.json"
    if condition=="without_ckg":
        if db.exists() or config.exists(): raise ValueError("without_ckg must not contain CKG index or MCP config")
        return None
    if not db.exists() or not config.exists(): raise ValueError("CKG index or .mcp.json is missing")
    parsed=json.loads(config.read_text(encoding="utf-8"))
    if parsed.get("mcpServers",{}).get("ckg",{}).get("command")!="ckg-mcp": raise ValueError(".mcp.json has invalid mcpServers.ckg.command")
    return db,config
def run(tasks,runner,conditions,output,dry_run=False):
    output.mkdir(parents=True,exist_ok=True);raw=output/"runs.jsonl";done={}
    if raw.exists():
        for line in raw.read_text().splitlines():
            if line:x=json.loads(line);done[(x["task_id"],x["condition"])] = x
    results=list(done.values())
    with raw.open("a",encoding="utf-8") as fh:
        for task in tasks:
            for condition in conditions:
                if (task["id"],condition) in done:continue
                if dry_run:print(f"{task['id']} {condition} fixture={task['fixture']}");continue
                with tempfile.TemporaryDirectory(prefix="ckg-ab-") as td:
                    work=Path(td)/"repo";shutil.copytree(task["fixture"],work);ckg=None
                    if condition=="with_ckg":
                        try:
                            db,config=_provision_ckg(work);_validate_condition(work,condition);ckg={"enabled":True,"index":str(db),"mcp_config":str(config)}
                        except Exception as e:
                            result={"status":"failure","exit_code":None,"files_changed":[],"files_found":[],"symbols_found":[],"input_tokens":None,"output_tokens":None,"total_tokens":None,"tool_calls":None,"ckg_tools_used":None,"ckg_queries":None,"infrastructure_failure":True,"failure_reason":f"CKG provisioning failed: {str(e)[:2000]}","ckg_retrieval":{"enabled":False},"elapsed_seconds":0,"timed_out":False}
                            result.update(task_id=task["id"],language=task["language"],condition=condition);result["success"]=False
                            fh.write(json.dumps(result,separators=(",",":"))+"\n");fh.flush();results.append(result);continue
                    else: _validate_condition(work,condition)
                    result=runner.run(task,condition,work);result.update(task_id=task["id"],language=task["language"],condition=condition,ckg_retrieval=ckg);result=score(task,result)
                fh.write(json.dumps(result,separators=(",",":"))+"\n");fh.flush();results.append(result)
    if not dry_run:summary=summarize(results);(output/"summary.json").write_text(json.dumps(summary,indent=2)+"\n");write_report(results,summary,output/"report.md")
    return results
def main(argv=None):
    p=argparse.ArgumentParser();p.add_argument("--manifest",default="evaluation/tasks.json");p.add_argument("--condition",choices=("with_ckg","without_ckg","both"),default="both");p.add_argument("--output",default="results/");p.add_argument("--dry-run",action="store_true");p.add_argument("--agent-command");p.add_argument("--pilot",action="store_true");p.add_argument("--preflight",action="store_true");p.add_argument("--timeout",type=int,help="per-run timeout in seconds, overriding each task's manifest value");a=p.parse_args(argv);tasks=load_tasks(a.manifest)
    if a.pilot:
        pilot=[]
        for language in ("python","javascript"):
            pilot.append(next(x for x in tasks if x["language"]==language))
        tasks=pilot
    conditions=("with_ckg","without_ckg") if a.condition=="both" else (a.condition,)
    if a.preflight:
        for task in tasks:
            statuses=[]
            for condition in conditions:
                with tempfile.TemporaryDirectory(prefix="ckg-preflight-") as td:
                    work=Path(td)/"repo";shutil.copytree(task["fixture"],work)
                    try:
                        if condition=="with_ckg": _provision_ckg(work)
                        _validate_condition(work,condition);statuses.append(f"{condition}=PASS")
                    except Exception as e:statuses.append(f"{condition}=FAIL ({e})")
            print(f"{task['id']} fixture={task['fixture']} " + " ".join(statuses))
        return 0
    run(tasks,SubprocessAgentRunner(a.agent_command,a.timeout) if a.agent_command else FakeAgentRunner(),conditions,Path(a.output),a.dry_run);return 0
if __name__=="__main__":raise SystemExit(main())
