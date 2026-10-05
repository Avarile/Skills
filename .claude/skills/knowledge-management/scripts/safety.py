"""Secret detection for knowledge bodies being captured or appended.

Reads (`get`, `type`) are never filtered or redacted (owner decision CR-1, 2026-10-05). This module lets `capture`
and `append` warn that a body looks like it holds a secret, so the entry can be filed under a credential type, and
lets search previews (`find` snippets) hide secret values the user did not ask for.
Findings show the kind, line and a masked hint, never the full value.
"""
import re

# A value that is clearly a placeholder or a variable reference, not a secret.
_PLACEHOLDER = r"(?!\$|<|\[|\{\{|your|change[_-]?me|xxx|\*{3}|example|placeholder|redacted|none\b|null\b|true\b|false\b)"
# Compound labels first, so "Secret key: ..." and "Master key = ..." match with the space included.
# "\_" is a Markdown-escaped underscore (Notion/Obsidian exports: API\_KEY).
_KEYS = (r"[\w.\\-]*(?:(?:secret|access|master|private|api|client|root)(?:\\?[ _-])?(?:key|secret|token)|"
         r"password|passwd|pwd|(?<![a-z])pass\b|secret|token|apikey|auth(?!or))[\w.\\-]*")

PATTERNS = [
    ("key=value secret", re.compile(r"(?i)(?:^|(?<=[\s\"'{,;(]))(?:export\s+)?[\"']?" + _KEYS + r"[\"']?\s*[:=]\s*[\"']?" + _PLACEHOLDER + r"([^\s\"'#,]{6,})")),
    ("SQL password", re.compile(r"(?i)\b(?:with\s+password|identified\s+by)\s+'" + _PLACEHOLDER + r"([^'\s]{6,})'")),
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


def redact(text, marker="[secret]", known=()):
    """text with every detected secret value replaced by marker, including repeats of that value elsewhere in the
    text (e.g. a password reused as a user name) and any of `known` (values detected in other entries).
    For previews only; reads stay unredacted (CR-1)."""
    spans = sorted((m.start(1), m.end(1)) for _, rx in PATTERNS for m in rx.finditer(text or "") if m.end(1) > m.start(1))
    found = {text[a:b] for a, b in spans if b - a >= 6} | {v for v in known if len(v) >= 6}
    out, pos = [], 0
    for a, b in spans:
        if a >= pos:
            out += [text[pos:a], marker]
            pos = b
        elif b > pos:  # overlapping match: extend the hidden span
            pos = b
    text = "".join(out) + (text or "")[pos:]
    for v in sorted(found, key=len, reverse=True):
        text = text.replace(v, marker)
    return text


def is_credential_type(type_title):
    return bool(type_title and CREDENTIAL_TYPE.search(type_title))


def values(text):
    """Raw secret values found in text. Internal use only (reuse detection); never print or store them."""
    return [m.group(1) for _, rx in PATTERNS for m in rx.finditer(text or "") if m.group(1)]


_TOKEN_PREFIX = re.compile(r"^(sk-proj-|sk-|ghp_|github_pat_|xox[baprs]-|AKIA|eyJ)")


def stem_key(value):
    """Comparable form of a human-chosen password: provider token prefixes removed, lower-cased."""
    return _TOKEN_PREFIX.sub("", value).lower()


def looks_like_bare_secret(text):
    """A body that is just one password-like token: 8-64 chars, no spaces, not a URL or path, 3+ character classes."""
    t = (text or "").strip().strip("`").strip()
    if not re.fullmatch(r"\S{8,64}", t) or re.match(r"(https?://|/|~/|\./)", t):
        return False
    classes = sum(bool(re.search(p, t)) for p in (r"[a-z]", r"[A-Z]", r"[0-9]", r"[^A-Za-z0-9]"))
    return classes >= 3
