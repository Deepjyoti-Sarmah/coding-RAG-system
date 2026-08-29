import tempfile
import unittest
from pathlib import Path

from analysis.build_graph import build_graph
from analysis.build_result import BuildResult
from models.entities.symbol_kind import SymbolKind


def _build(files: dict[str, str]) -> BuildResult:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        for relative_path, content in files.items():
            path = root / relative_path
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
        return build_graph(str(root))


class TestModuleSymbolSynthesis(unittest.TestCase):
    def test_import_only_file_yields_one_module_chunk_with_imported_names(self):
        result = _build(
            {
                "middleware/cors.py": (
                    "from starlette.middleware.cors import "
                    "CORSMiddleware as CORSMiddleware  # noqa\n"
                ),
            }
        )

        module_symbols = [s for s in result.symbols if s.kind == SymbolKind.MODULE]
        self.assertEqual(len(module_symbols), 1)

        symbol = module_symbols[0]
        self.assertEqual(symbol.relative_path, "middleware/cors.py")

        chunks = [c for c in result.chunks if c.symbol_id == symbol.symbol_id]
        self.assertEqual(len(chunks), 1)

        chunk = chunks[0]
        self.assertIn("CORSMiddleware", chunk.embedding_text)
        self.assertIn("file: middleware/cors.py", chunk.embedding_text)

    def test_genuinely_empty_file_yields_no_chunk(self):
        result = _build({"__init__.py": ""})

        self.assertEqual(result.symbols, [])
        self.assertEqual(result.chunks, [])

    def test_file_with_real_symbols_is_unchanged(self):
        result = _build(
            {
                "real.py": "def real_function():\n    return 1\n",
            }
        )

        kinds = {s.kind for s in result.symbols}
        self.assertEqual(kinds, {SymbolKind.FUNCTION})
        self.assertEqual(len(result.symbols), 1)
        self.assertEqual(len(result.chunks), 1)

    def test_module_symbol_only_synthesized_when_real_symbols_absent(self):
        result = _build(
            {
                "mixed.py": (
                    "import os\n\n"
                    "def real_function():\n    return os.getcwd()\n"
                ),
            }
        )

        module_symbols = [s for s in result.symbols if s.kind == SymbolKind.MODULE]
        self.assertEqual(module_symbols, [])
        self.assertEqual(len(result.symbols), 1)
        self.assertEqual(len(result.chunks), 1)


if __name__ == "__main__":
    unittest.main()
