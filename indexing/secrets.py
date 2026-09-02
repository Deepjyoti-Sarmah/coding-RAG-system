"""Secrets + PII scanning — CCE parity set, redaction before chunking/indexing."""

import re

# CCE set: 14 regexes (13 + generic credential) + placeholders exempt
_PATTERNS = [
    re.compile(r"AKIA[0-9A-Z]{16}"),  # AWS access key
    re.compile(r"aws_secret_access_key\s*=\s*[A-Za-z0-9/+=]{20,}"),
    re.compile(r"ghp_[A-Za-z0-9]{36,}"),  # GH classic PAT
    re.compile(r"github_pat_[A-Za-z0-9_]{80,}"),
    re.compile(r"ghs_[A-Za-z0-9]{36,}"),
    re.compile(r"gho_[A-Za-z0-9]{36,}"),
    re.compile(r"ghu_[A-Za-z0-9]{36,}"),
    re.compile(r"ghr_[A-Za-z0-9]{36,}"),
    re.compile(r"xox[abprs]-[0-9A-Za-z-]{10,}"),  # Slack
    re.compile(r"sk_live_[0-9a-zA-Z]{20,}"),  # Stripe live
    re.compile(r"sk-[A-Za-z0-9]{20,}T3BlbkFJ[A-Za-z0-9_-]{20,}"),  # OpenAI
    re.compile(r"sk-ant-[A-Za-z0-9\-_]{20,}"),  # Anthropic
    re.compile(r"AIza[0-9A-Za-z_\-]{35}"),  # Google API
    re.compile(r"eyJ[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,}"),  # JWT
    re.compile(r"-----BEGIN (?:RSA )?PRIVATE KEY-----"),
    # Generic credential: dotenv-style KEY=value with password/secret/token/api_key and 16+ chars — quoted+unquoted
    re.compile(r"(?i)(?:^\s*(?:export\s+)?\w*(?:password|passwd|secret|token|api[_-]?key)\w*\s*[:=]\s*['\"]?[^'\"\s]{16,}['\"]?)", re.MULTILINE),
]

_PLACEHOLDER_RE = re.compile(r"your-api-key|xxxxx|my-api-key|your-secret|test[_-]key", re.IGNORECASE)

_SECRET_FILENAMES = {".env", "credentials.json", "secrets.yml", "secrets.yaml", ".env.local", ".env.production"}
_SECRET_SUFFIXES = (".env",)
_SECRET_EXTENSIONS = {".pem", ".key", ".p12", ".jks"}

_REDACTED = "[REDACTED]"

# PII
_EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}")
_IPV4_RE = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")
_SSN_RE = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")
_PHONE_RE = re.compile(r"\+[1-9]\d{1,14}\b")


def _is_placeholder(text: str) -> bool:
    return bool(_PLACEHOLDER_RE.search(text))


def contains_secret(text: str) -> bool:
    if _is_placeholder(text):
        return False
    return any(p.search(text) for p in _PATTERNS)


def redact_secrets(text: str) -> str:
    if _is_placeholder(text):
        return text
    out = text
    for p in _PATTERNS:
        out = p.sub(_REDACTED, out)
    return out


def is_secret_filename(relative_path: str) -> bool:
    name = relative_path.split("/")[-1].lower()
    if name in _SECRET_FILENAMES:
        return True
    if any(name.endswith(suf) for suf in _SECRET_SUFFIXES):
        return True
    ext = "." + name.split(".")[-1] if "." in name else ""
    if ext.lower() in _SECRET_EXTENSIONS:
        return True
    return False


def should_skip_file_content(relative_path: str, content: str) -> bool:
    if is_secret_filename(relative_path) and contains_secret(content):
        return True
    if is_secret_filename(relative_path):
        # .env without obvious secret still skip if name is secret file? Conservative: skip .env entirely if it looks like env
        if relative_path.endswith(".env") or relative_path.split("/")[-1] in _SECRET_FILENAMES:
            # only skip if file is secret filename and small env-like; check heuristic
            if len(content) < 5000:
                return True
    if "PRIVATE KEY" in content:
        return True
    return False


def _luhn_valid(digits: str) -> bool:
    """Luhn check for credit card — true only if checksum passes."""
    try:
        nums = [int(d) for d in digits]
        checksum = 0
        parity = len(nums) % 2
        for i, d in enumerate(nums):
            if i % 2 == parity:
                d *= 2
                if d > 9:
                    d -= 9
            checksum += d
        return checksum % 10 == 0
    except (ValueError, IndexError):
        return False


def redact_pii(text: str, enabled: bool = True) -> str:
    if not enabled:
        return text
    out = _EMAIL_RE.sub("[REDACTED:EMAIL]", text)
    out = _IPV4_RE.sub("[REDACTED:IP]", out)
    out = _SSN_RE.sub("[REDACTED:SSN]", out)
    out = _PHONE_RE.sub("[REDACTED:PHONE]", out)
    # Credit card: 13-19 digits with spaces/dashes, Luhn-validated (matches CCE)

    def _card_repl(m: re.Match) -> str:
        raw = m.group(0)
        digits = re.sub(r"[ -]", "", raw)
        if 13 <= len(digits) <= 19 and digits.isdigit() and _luhn_valid(digits):
            return "[REDACTED:CARD]"
        return raw

    out = re.sub(r"\b(?:\d[ -]*?){13,19}\b", _card_repl, out)
    return out
