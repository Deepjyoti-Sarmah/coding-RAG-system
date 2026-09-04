"""Multi-editor config matrix — writes/detects MCP server entries per editor."""

import hashlib
import os
import tempfile
from pathlib import Path

EDITORS = {
    "claude": {"config_path": ".mcp.json", "container_key": "mcpServers"},
    "cursor": {"config_path": ".cursor/mcp.json", "container_key": "mcpServers"},
    "vscode": {"config_path": ".vscode/mcp.json", "container_key": "mcpServers"},
    "opencode": {"config_path": "opencode.json", "container_key": "mcp"},
    "gemini": {"config_path": ".gemini/settings.json", "container_key": "mcpServers"},
    "copilot": {"config_path": ".github/copilot-instructions.md", "container_key": None},
    "pi": {"config_path": "AGENTS.md", "container_key": None},
    "codex": {"config_path": "~/.codex/config.toml", "container_key": "mcp_servers"},
}


SG_BLOCK_VERSION = 1
SG_BLOCK_START = f"<!-- sg-block-version: {SG_BLOCK_VERSION} -->"
SG_BLOCK_END = "<!-- end sg-block -->"
SG_BLOCK_CONTENT = """<!-- sg-block-version: 1 -->
## symbolgraph symbolgraph
Use `sg search` / `sg context` / `definition` / `callers` / `callees` before reading files. Index via `sg index .`
<!-- end sg-block -->"""


def toml_escape(s: str) -> str:
    """Escape backslashes and double quotes for a TOML string value."""
    return s.replace("\\", "\\\\").replace('"', '\\"')


def project_storage_slug(abs_path: str) -> str:
    h = hashlib.sha256(abs_path.encode()).hexdigest()[:6]
    # sanitize  basename for filesystem/ TOML safety
    base = Path(abs_path).name.replace("\\", "_").replace('"', "_")
    return f"{base}-{h}"


def ensure_block_content(existing: str) -> tuple[str, bool]:
    """Return (new_content, already_configured). Handles version upgrade."""
    if SG_BLOCK_START in existing and SG_BLOCK_END in existing:
        return existing, True
    # Legacy marker upgrade
    if "<!-- symbolgraph MCP: sg-mcp -->" in existing:
        return existing.replace("<!-- symbolgraph MCP: sg-mcp -->", SG_BLOCK_CONTENT), False
    if existing and not existing.endswith("\n"):
        existing += "\n"
    return existing + SG_BLOCK_CONTENT + "\n", False


def atomic_write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(path.parent))
    try:
        os.write(fd, content.encode())
        os.fsync(fd)
        os.close(fd)
        os.replace(tmp, path)
    finally:
        try:
            os.unlink(tmp)
        except OSError:
            pass


def detect_editors(root: Path) -> list[str]:
    detected = []
    if (root / ".vscode").is_dir():
        detected.append("vscode")
    if (root / ".cursor").is_dir():
        detected.append("cursor")
    if (root / "opencode.json").exists():
        detected.append("opencode")
    if not detected:
        detected.append("claude")
    return detected
