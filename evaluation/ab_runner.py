from __future__ import annotations
import argparse,json,shutil,subprocess,tempfile,time
from pathlib import Path
from .ab_metrics import score,summarize,write_report

class AgentRunner:
    def run(self, task, condition, worktree): raise NotImplementedError

class SubprocessAgentRunner(AgentRunner):
    def __init__(self, template): self.template=template
    def run(self,task,condition,worktree):
        command=self.template.format(prompt=task["prompt"],worktree=str(worktree),condition=condition)
        started=time.monotonic()
        try:
            p=subprocess.run(command,shell=True,cwd=worktree,text=True,capture_output=True,timeout=task["timeout"])
            return {"exit_code":p.returncode,"stdout":p.stdout[-8000:],"stderr":p.stderr[-8000:],"elapsed_seconds":time.monotonic()-started,"files_changed":[],"symbols_found":[]}
        except subprocess.TimeoutExpired as e: return {"exit_code":None,"timed_out":True,"stdout":str(e.stdout or '')[-8000:],"stderr":str(e.stderr or '')[-8000:],"elapsed_seconds":time.monotonic()-started,"files_changed":[],"symbols_found":[]}

class FakeAgentRunner(AgentRunner):
    def run(self,task,condition,worktree):
        ok=condition=="with_ckg" or task["id"] in {"py-auth","js-auth","go-auth"}
        return {"exit_code":0 if ok else 1,"elapsed_seconds":0.01,"input_tokens":100,"output_tokens":30,"total_tokens":130,"tool_calls":2 if condition=="with_ckg" else 0,"files_changed":task["expected_files"] if ok else [],"symbols_found":task["expected_symbols"] if ok else [],"ckg_retrieval":{"enabled":condition=="with_ckg","results":len(task["expected_symbols"])}}

def load_tasks(path):
    tasks=json.loads(Path(path).read_text()); assert len(tasks)==20, "manifest must contain exactly 20 tasks"; return tasks
def run(tasks,runner,conditions,output,dry_run=False):
    output.mkdir(parents=True,exist_ok=True); raw=output/"runs.jsonl"; done={}
    if raw.exists():
        for line in raw.read_text().splitlines():
            if line:
                x=json.loads(line); done[(x["task_id"],x["condition"])]=x
    results=list(done.values())
    with raw.open("a",encoding="utf-8") as fh:
        for task in tasks:
            for condition in conditions:
                if (task["id"],condition) in done: continue
                if dry_run: print(f"{task['id']} {condition} fixture={task['fixture']}"); continue
                with tempfile.TemporaryDirectory(prefix="ckg-ab-") as td:
                    work=Path(td)/"repo"; shutil.copytree(task["fixture"],work)
                    result=runner.run(task,condition,work); result.update(task_id=task["id"],language=task["language"],condition=condition); result=score(task,result)
                fh.write(json.dumps(result,separators=(",",":"))+"\n"); fh.flush(); results.append(result)
    if not dry_run:
        summary=summarize(results); (output/"summary.json").write_text(json.dumps(summary,indent=2)+"\n"); write_report(results,summary,output/"report.md")
    return results

def main(argv=None):
    p=argparse.ArgumentParser(); p.add_argument("--manifest",default="evaluation/tasks.json"); p.add_argument("--condition",choices=("with_ckg","without_ckg","both"),default="both"); p.add_argument("--output",default="results/"); p.add_argument("--dry-run",action="store_true"); p.add_argument("--agent-command"); a=p.parse_args(argv)
    conditions=("with_ckg","without_ckg") if a.condition=="both" else (a.condition,); runner=SubprocessAgentRunner(a.agent_command) if a.agent_command else FakeAgentRunner(); run(load_tasks(a.manifest),runner,conditions,Path(a.output),a.dry_run); return 0
if __name__=="__main__": raise SystemExit(main())
