import json
import tempfile
import unittest
from pathlib import Path

import mcp_server
from embeddings.fake_provider import FakeEmbeddingProvider

AUTH = {
    "auth.ts": (
        "export function createAuth() { return 1; }\n"
        "export function login(name: string) { createAuth(); return name; }\n"
    ),
    "api.ts": (
        'import { login } from "./auth";\n'
        'export function run() { login("admin"); }\n'
    ),
}


def _write(root: Path, files: dict[str, str]) -> None:
    for relative_path, content in files.items():
        (root / relative_path).write_text(content, encoding="utf-8")


async def _call(tool_name: str, **arguments) -> dict:
    result = await mcp_server.mcp.call_tool(tool_name, arguments)
    payload = json.loads(result.content[0].text)
    assert result.is_error is not True, payload
    return payload


class TestMcpServer(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        _write(self.root, AUTH)
        # Inject a fake embedding provider so the lazy drain in
        # mcp_server.index_repository never constructs a real
        # LocalEmbeddingProvider (which would trigger a HuggingFace
        # download). _get_mcp_provider() memoizes into the global,
        # so short-circuiting the global is sufficient.
        self._orig_mcp_provider = mcp_server._mcp_provider
        mcp_server.set_mcp_provider(FakeEmbeddingProvider(dimension=8))

    def tearDown(self):
        mcp_server.set_mcp_provider(self._orig_mcp_provider)
        self.tmp.cleanup()

    async def test_tools_are_registered(self):
        tools = await mcp_server.mcp.list_tools()

        self.assertEqual(
            {tool.name for tool in tools},
            {
                "index_repository",
                "repository_status",
                "definition",
                "callers",
                "callees",
                "search",
                "imports",
                "context",
            },
        )

    async def test_status_before_index_reports_not_indexed(self):
        payload = await _call("repository_status", path=str(self.root))

        self.assertEqual(payload, {"indexed": False})

    async def test_read_tool_before_index_returns_soft_error(self):
        payload = await _call("definition", name="createAuth", path=str(self.root))

        self.assertIn("error", payload)
        self.assertIn("index_repository", payload["error"])

    async def test_index_repository_then_status(self):
        index_payload = await _call("index_repository", path=str(self.root))

        self.assertEqual(index_payload["parsed_files"], 2)

        status_payload = await _call("repository_status", path=str(self.root))

        self.assertTrue(status_payload["indexed"])
        self.assertEqual(status_payload["documents"], 2)

    async def test_definition_finds_symbol(self):
        await _call("index_repository", path=str(self.root))

        payload = await _call("definition", name="createAuth", path=str(self.root))

        self.assertEqual(
            {r["symbol_name"] for r in payload["results"]}, {"createAuth"}
        )
        self.assertEqual(payload["results"][0]["relative_path"], "auth.ts")

    async def test_callers_and_callees(self):
        await _call("index_repository", path=str(self.root))

        callers_payload = await _call("callers", name="login", path=str(self.root))
        callees_payload = await _call("callees", name="login", path=str(self.root))

        self.assertEqual(
            {r["symbol_name"] for r in callers_payload["results"]}, {"run"}
        )
        self.assertEqual(
            {r["symbol_name"] for r in callees_payload["results"]}, {"createAuth"}
        )

    async def test_imports_lists_resolution(self):
        await _call("index_repository", path=str(self.root))

        payload = await _call("imports", file="api.ts", path=str(self.root))

        self.assertEqual(len(payload["imports"]), 1)
        entry = payload["imports"][0]
        self.assertEqual(entry["local_name"], "login")
        self.assertTrue(entry["resolved"])
        self.assertEqual(entry["target_file"], "auth.ts")
        self.assertEqual(entry["target_symbol"], "login")

    async def test_search_without_embed_still_finds_matches(self):
        await _call("index_repository", path=str(self.root))

        payload = await _call("search", query="login", path=str(self.root))

        # After lazy drain the worker may have embedded chunks, so vector use is
        # opportunistic — the test only cares that lexical matches still work.
        self.assertIn("login", {r["symbol_name"] for r in payload["results"]})

    async def test_context_respects_token_budget(self):
        await _call("index_repository", path=str(self.root))

        payload = await _call(
            "context", query="login", path=str(self.root), token_budget=500
        )

        self.assertLessEqual(payload["total_tokens"], 500)
        self.assertIn(
            "login",
            [entry["qualified_name"] for entry in payload["primary_definitions"]],
        )


if __name__ == "__main__":
    unittest.main()
