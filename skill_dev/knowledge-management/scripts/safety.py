"""Secret detection for knowledge bodies being captured or appended.

Reads are never filtered or redacted (owner decision CR-1, 2026-10-05). This module only lets `capture` and
`append` warn that a body looks like it holds a secret, so the entry can be filed under a credential type.
Findings show the kind, line and a masked hint, never the full value.
"""
import re

# A value that is clearly a placeholder or a variable reference, not a secret.
_PLACEHOLDER = r"(?!\$|<|\{\{|your|change[_-]?me|xxx|\*{3}|example|placeholder|redacted|none\b|null\b|true\b|false\b)"
_KEYS = r"[\w.-]*(?:password|passwd|pwd|secret|token|api[_-]?key|apikey|access[_-]?key|private[_-]?key|client[_-]?secret|auth)[\w.-]*"

PATTERNS = [
    ("key=value secret", re.compile(r"(?i)(?:^|(?<=[\s\"'{,;(]))(?:export\s+)?[\"']?" + _KEYS + r"[\"']?\s*[:=]\s*[\"']?" + _PLACEHOLDER + r"([^\s\"'#,]{6,})")),
    ("private key block", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----()")),
    ("credentials in URL", re.compile(r"\b[a-z][a-z0-9+.-]*://[^/\s:@]+:" + _PLACEHOLDER + r"([^/\s@]{3,})@")),
    ("provider token", re.compile(r"\b(sk-[A-Za-z0-9_-]{20,}|ghp_[A-Za-z0-9]{30,}|github_pat_\w{30,}|AKIA[0-9A-Z]{16}|xox[baprs]-[\w-]{10,}|eyJ[\w-]{10,}\.[\w-]{10,}\.[\w-]{10,})")),
]

CREDENTIAL_TYPE = re.compile(r"credential|api[ _-]?key", re.I)


def mask(v):
    return (v[:2] + "…(%d chars)" % len(v)) if v else "…"


def scan(text):
    """[(kind, line_no, masked_hint)] for every likely secret in text."""
    out = []
    for kind, rx in PATTERNS:
        for m in rx.finditer(text or ""):
            out.append((kind, text.count("\n", 0, m.start()) + 1, mask(m.group(1))))
    return sorted(set(out), key=lambda x: x[1])


def is_credential_type(type_title):
    return bool(type_title and CREDENTIAL_TYPE.search(type_title))
