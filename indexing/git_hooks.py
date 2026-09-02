"""Git hooks keep-fresh — post-commit/post-checkout/post-merge triggers background ckg index."""

import os
import stat
from pathlib import Path


def _hook_content(root: Path) -> str:
    return f"""#!/bin/sh
# CKG keep-fresh hook — do not edit manually
if echo "$1" | grep -q "/tmp\\|/private/tmp\\|/.claude/worktrees/" 2>/dev/null; then exit 0; fi
if [ -f /tmp/ckg-index-hook.lock ]; then
  pid=$(cat /tmp/ckg-index-hook.lock 2>/dev/null)
  if [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null; then exit 0; fi
fi
echo $$ > /tmp/ckg-index-hook.lock
nice -n 10 ckg index "{root}" &>/dev/null &
"""


def _git_hooks_dir(root: Path) -> Path | None:
    try:
        import subprocess

        out = subprocess.run(["git", "rev-parse", "--git-common-dir"], cwd=root, capture_output=True, text=True, check=False)
        if out.returncode == 0:
            return (Path(root) / out.stdout.strip()).resolve()
        git_dir = root / ".git"
        if git_dir.exists():
            return git_dir
    except Exception:
        pass
    return None


def install_hooks(root: str | Path) -> list[str]:
    root = Path(root).resolve()
    hooks_dir = _git_hooks_dir(root)
    if hooks_dir is None or not hooks_dir.exists():
        return []
    installed = []
    for name in ("post-commit", "post-checkout", "post-merge"):
        path = hooks_dir / "hooks" / name
        if path.exists() and "CKG keep-fresh" not in path.read_text(encoding="utf-8", errors="ignore"):
            continue  # don't clobber user hook
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(_hook_content(root), encoding="utf-8")
        path.chmod(path.stat().st_mode | stat.S_IEXEC)
        installed.append(str(path))
    return installed


def uninstall_hooks(root: str | Path) -> list[str]:
    root = Path(root).resolve()
    hooks_dir = _git_hooks_dir(root)
    if hooks_dir is None:
        return []
    removed = []
    for name in ("post-commit", "post-checkout", "post-merge"):
        path = hooks_dir / "hooks" / name
        if path.exists() and "CKG keep-fresh" in path.read_text(encoding="utf-8", errors="ignore"):
            path.unlink()
            removed.append(str(path))
    return removed
