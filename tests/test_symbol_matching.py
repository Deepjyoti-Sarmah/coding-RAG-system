import tempfile
import unittest
from pathlib import Path

from analysis.build_graph import build_graph
from analysis.symbol_matching import MatchConfidence, match_symbols


def _build(files: dict[str, str]):
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        for relative_path, content in files.items():
            path = root / relative_path
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
        return build_graph(str(root))


def _symbols_by_name(result, name: str):
    return [s for s in result.symbols if s.name == name]


class TestSymbolMatching(unittest.TestCase):
    def test_unchanged_repo_matches_every_symbol_high(self):
        files = {
            "auth.ts": (
                "export function login(name: string) { return 1; }\n"
                "export class AuthService {\n"
                "  validateUser(name: string) { return true; }\n"
                "}\n"
            ),
        }

        old = _build(files)
        new = _build(files)

        matches = match_symbols(
            old_symbols=old.symbols,
            new_symbols=new.symbols,
        )

        self.assertEqual(len(matches), len(new.symbols))
        self.assertTrue(
            all(m.confidence == MatchConfidence.HIGH for m in matches)
        )
        self.assertEqual(
            {m.old_symbol.name for m in matches},
            {s.name for s in new.symbols},
        )

    def test_rename_in_place_matches_medium(self):
        old = _build(
            {"auth.ts": "export function login(name: string) { return 1; }\n"}
        )
        new = _build(
            {"auth.ts": "export function loginRenamed(name: string) { return 1; }\n"}
        )

        matches = match_symbols(
            old_symbols=old.symbols,
            new_symbols=new.symbols,
        )

        self.assertEqual(len(matches), 1)
        match = matches[0]
        self.assertEqual(match.old_symbol.name, "login")
        self.assertEqual(match.new_symbol.name, "loginRenamed")
        self.assertEqual(match.confidence, MatchConfidence.MEDIUM)

    def test_file_move_with_unchanged_content_matches_medium(self):
        old = _build(
            {"auth.ts": "export function login(name: string) { return 1; }\n"}
        )
        new = _build(
            {"src/auth.ts": "export function login(name: string) { return 1; }\n"}
        )

        matches = match_symbols(
            old_symbols=old.symbols,
            new_symbols=new.symbols,
        )

        self.assertEqual(len(matches), 1)
        match = matches[0]
        self.assertEqual(match.old_symbol.relative_path, "auth.ts")
        self.assertEqual(match.new_symbol.relative_path, "src/auth.ts")
        self.assertEqual(match.confidence, MatchConfidence.MEDIUM)

    def test_signature_change_is_still_same_identity(self):
        old = _build(
            {"auth.ts": "export function login(name: string) { return 1; }\n"}
        )
        new = _build(
            {"auth.ts": "export function login(name: number) { return 1; }\n"}
        )

        matches = match_symbols(
            old_symbols=old.symbols,
            new_symbols=new.symbols,
        )

        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0].confidence, MatchConfidence.HIGH)

    def test_rename_plus_signature_change_is_new_identity(self):
        old = _build(
            {"auth.ts": "export function login(name: string) { return 1; }\n"}
        )
        new = _build(
            {"auth.ts": "export function loginRenamed(name: number) { return 1; }\n"}
        )

        matches = match_symbols(
            old_symbols=old.symbols,
            new_symbols=new.symbols,
        )

        self.assertEqual(matches, [])

    def test_ambiguous_scope_signature_is_new_identity(self):
        old = _build(
            {
                "auth.ts": (
                    "export function login(name: string) { return 1; }\n"
                    "export function logout(name: string) { return 2; }\n"
                )
            }
        )
        new = _build(
            {
                "auth.ts": (
                    "export function loginRenamed(name: string) { return 1; }\n"
                    "export function logout(name: string) { return 2; }\n"
                )
            }
        )

        matches = match_symbols(
            old_symbols=old.symbols,
            new_symbols=new.symbols,
        )

        by_new_name = {m.new_symbol.name: m for m in matches}
        self.assertNotIn("loginRenamed", by_new_name)
        self.assertEqual(
            by_new_name["logout"].confidence,
            MatchConfidence.HIGH,
        )

    def test_moved_and_edited_is_new_identity(self):
        old = _build(
            {"auth.ts": "export function login(name: string) { return 1; }\n"}
        )
        new = _build(
            {"src/auth.ts": "export function login(name: string) { return 2; }\n"}
        )

        matches = match_symbols(
            old_symbols=old.symbols,
            new_symbols=new.symbols,
        )

        self.assertEqual(matches, [])


if __name__ == "__main__":
    unittest.main()
