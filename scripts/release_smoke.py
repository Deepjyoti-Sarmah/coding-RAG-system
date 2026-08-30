"""Build and exercise CKG from a wheel in an external temporary environment."""
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
import time
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MAX_OUTPUT = 8000


class SmokeError(RuntimeError):
    pass


def run_command(command, *, cwd=None, timeout=60, env=None):
    try:
        completed = subprocess.run(command, cwd=cwd, env=env, text=True,
                                   capture_output=True, timeout=timeout)
    except subprocess.TimeoutExpired as exc:
        raise SmokeError(f"timed out after {timeout}s: {' '.join(map(str, command))}") from exc
    if completed.returncode:
        output = (completed.stdout + "\n" + completed.stderr)[-MAX_OUTPUT:]
        raise SmokeError(f"command failed ({completed.returncode}): {' '.join(map(str, command))}\n{output}")
    return completed


def discover_wheel(dist=ROOT / "dist"):
    wheels = sorted(Path(dist).glob("code_knowledge_graph-*.whl"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not wheels:
        raise SmokeError(f"no CKG wheel found in {dist}")
    return wheels[0]


def entrypoint(venv, name):
    return str(Path(venv) / ("Scripts" if os.name == "nt" else "bin") / name)


def verify_wheel(wheel):
    with zipfile.ZipFile(wheel) as archive:
        names = set(archive.namelist())
        if not any(n.startswith("code_knowledge_graph-") and n.endswith(".dist-info/METADATA") for n in names):
            raise SmokeError("wheel metadata is missing")
        metadata = archive.read(next(n for n in names if n.endswith(".dist-info/METADATA"))).decode()
        version = next((line.split(":", 1)[1].strip() for line in metadata.splitlines() if line.startswith("Version:")), "")
        if not version: raise SmokeError("wheel version is missing")
        for package in ("session_memory/", "ckg/dashboard/"):
            if not any(n.startswith(package) for n in names): raise SmokeError(f"{package} is missing from wheel")
    return version


def smoke():
    run_command(["uv", "build"], cwd=ROOT, timeout=120)
    wheel = discover_wheel(); version = verify_wheel(wheel)
    with tempfile.TemporaryDirectory(prefix="ckg-wheel-smoke-") as temp:
        temp = Path(temp); venv = temp / "venv"; work = temp / "work"; fixture = work / "fixture"
        work.mkdir(); shutil.copytree(ROOT / "tests" / "fixtures" / "session_repo", fixture)
        run_command(["uv", "venv", str(venv)], cwd=work, timeout=60)
        python = entrypoint(venv, "python")
        try:
            run_command(["uv", "pip", "install", "--offline", "--python", python, str(wheel)], cwd=work, timeout=120)
        except SmokeError as exc:
            raise SmokeError("offline wheel installation failed; missing cached dependency: " + str(exc)) from exc
        env = os.environ.copy(); env.pop("PYTHONPATH", None); env["HF_HUB_OFFLINE"] = "1"
        commands = [
            ([entrypoint(venv, "ckg"), "--help"], 30),
            ([entrypoint(venv, "ckg"), "index", str(fixture)], 60),
            ([entrypoint(venv, "ckg"), "status", str(fixture)], 30),
            ([entrypoint(venv, "ckg"), "search", "login", str(fixture), "--no-vector"], 30),
            ([entrypoint(venv, "ckg"), "sessions", "--help"], 30),
            ([entrypoint(venv, "ckg"), "sessions", "list", str(fixture)], 30),
            ([entrypoint(venv, "ckg"), "dashboard", "--help"], 30),
        ]
        for command, timeout in commands: run_command(command, cwd=work, timeout=timeout, env=env)
        proc = subprocess.Popen([entrypoint(venv, "ckg-mcp")], cwd=work, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        try: proc.wait(timeout=5)
        except subprocess.TimeoutExpired: proc.terminate(); proc.wait(timeout=5)
        if proc.returncode not in (0, -15, 143):
            raise SmokeError(f"ckg-mcp exited unexpectedly: {proc.returncode}\n{(proc.stderr.read() if proc.stderr else '')[-MAX_OUTPUT:]}")
        print(f"wheel={wheel.name} version={version}; installed external venv; source checkout not imported; ckg-mcp started")


def main():
    parser = argparse.ArgumentParser(description=__doc__); parser.parse_args()
    try: smoke()
    except SmokeError as exc: print(f"release smoke failed: {exc}", file=sys.stderr); return 1
    return 0


if __name__ == "__main__": raise SystemExit(main())
