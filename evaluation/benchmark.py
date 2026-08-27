from dataclasses import dataclass, field
from pathlib import Path

BENCHMARK_REPO = str(
    Path(__file__).resolve().parent.parent / "tests" / "fixtures" / "evaluation_repo"
)

STRUCTURAL = "structural"
SEMANTIC = "semantic"

DEFINITION = "definition"
CALLERS = "callers"
CALLEES = "callees"
IMPORTERS = "importers"
SEARCH = "search"


@dataclass(frozen=True, slots=True)
class Question:
    id: str
    text: str
    category: str
    kind: str
    # Symbol name (definition/callers/callees) or relative path (importers).
    # Unused for plain "search" questions.
    target: str
    # Ground truth: symbol names (definition/callers/callees/search) or
    # relative paths (importers) that a correct answer must surface.
    relevant: frozenset[str] = field(default_factory=frozenset)
    # Definition-only: the relative path the target symbol must be defined in.
    expected_location: str = ""


BENCHMARK_QUESTIONS: tuple[Question, ...] = (
    Question(
        id="def-createAuth",
        text="Where is createAuth defined?",
        category=STRUCTURAL,
        kind=DEFINITION,
        target="createAuth",
        relevant=frozenset({"createAuth"}),
        expected_location="auth.ts",
    ),
    Question(
        id="callers-login",
        text="Who calls login?",
        category=STRUCTURAL,
        kind=CALLERS,
        target="login",
        relevant=frozenset({"handleRequest"}),
    ),
    Question(
        id="callees-login",
        text="What does login call?",
        category=STRUCTURAL,
        kind=CALLEES,
        target="login",
        relevant=frozenset({"validateToken", "createAuth"}),
    ),
    Question(
        id="importers-auth",
        text="What imports auth.ts?",
        category=STRUCTURAL,
        kind=IMPORTERS,
        target="auth.ts",
        relevant=frozenset({"api.ts", "auth/handler.ts"}),
    ),
    Question(
        id="sem-authentication-flow",
        text="How does authentication work?",
        category=SEMANTIC,
        kind=SEARCH,
        target="",
        relevant=frozenset({"login", "createAuth", "validateToken"}),
    ),
    Question(
        id="sem-token-validation",
        text="Where is token validation implemented?",
        category=SEMANTIC,
        kind=SEARCH,
        target="",
        relevant=frozenset({"validateToken"}),
    ),
    Question(
        id="sem-request-to-database",
        text="How does a request reach the database?",
        category=SEMANTIC,
        kind=SEARCH,
        target="",
        relevant=frozenset({"handleRequest", "queryUser", "connect"}),
    ),
    Question(
        id="def-createAuthToken",
        text="Where is createAuthToken defined?",
        category=STRUCTURAL,
        kind=DEFINITION,
        target="createAuthToken",
        relevant=frozenset({"createAuthToken"}),
        expected_location="session.ts",
    ),
    Question(
        id="sem-token-expiry",
        text="How is token expiry checked?",
        category=SEMANTIC,
        kind=SEARCH,
        target="",
        relevant=frozenset({"validateTokenExpiry"}),
    ),
    Question(
        id="sem-auth-callback",
        text="Where is the auth callback handled?",
        category=SEMANTIC,
        kind=SEARCH,
        target="",
        relevant=frozenset({"handleAuthCallback"}),
    ),
    Question(
        id="sem-session-creation",
        text="How is a session token created?",
        category=SEMANTIC,
        kind=SEARCH,
        target="",
        relevant=frozenset({"createAuthToken", "generateToken"}),
    ),
    Question(
        id="sem-negative-not-the-one",
        text="Where is the login username validated?",
        category=SEMANTIC,
        kind=SEARCH,
        target="",
        relevant=frozenset({"login"}),
    ),
)
