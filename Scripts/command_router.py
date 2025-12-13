# Command Router v1.1
# Converts natural phrases into console commands with light normalization.
import re
import unicodedata


_SUBSTITUTIONS = [
    (re.compile(r"\bk\s*l[iy]x(?:e?s)?\b"), "calyx"),
    (re.compile(r"\bk\s*lit(?:e?s)?\b"), "calyx"),
    (re.compile(r"\bcalix\b"), "calyx"),
    (re.compile(r"\bkalix\b"), "calyx"),
    (re.compile(r"\bkalex\b"), "calyx"),
    (re.compile(r"\bkalic\b"), "calyx"),
    (re.compile(r"\bkali(?:s|es)?\b"), "calyx"),
    (re.compile(r"\bkalec(?:s)?\b"), "calyx"),
    (re.compile(r"\bkale(?:igh|y)(?:s)?\b"), "calyx"),
    (re.compile(r"\bkale(?:s)?\b"), "calyx"),
    (re.compile(r"\bkalec(?:'s)?\b"), "calyx"),
    (re.compile(r"\bkalics?\b"), "calyx"),
    (re.compile(r"\bcronicles?\b"), "chronicles"),
    (re.compile(r"\bchronicals?\b"), "chronicles"),
    (re.compile(r"\bchronicle\b"), "chronicles"),
    (re.compile(r"\bfunful\b"), "chronicles"),
]


def _normalize(text: str) -> str:
    ascii_text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    ascii_text = ascii_text.lower().replace("-", " ").replace("'", " ")
    ascii_text = re.sub(r"[^a-z0-9\s]", " ", ascii_text)
    ascii_text = re.sub(r"\s+", " ", ascii_text).strip()
    for pattern, replacement in _SUBSTITUTIONS:
        ascii_text = pattern.sub(replacement, ascii_text)
    ascii_text = re.sub(r"\s+", " ", ascii_text).strip()
    return ascii_text


def route(text):
    if not text:
        return None

    t = _normalize(text)

    if re.search(r"\b(begin|start)\b.*\bsession\b", t):
        return ["begin_session"]

    if "calyx" in t and "terminal" in t and any(
        trigger in t for trigger in ("activate", "enable", "start", "begin", "open")
    ):
        return ["begin_session"]

    m = re.search(r"\bsummon\b\s+(.*)$", t)
    if m:
        return ["summon", m.group(1).strip()]

    if "aurora" in t and "chronicles" in t:
        return ["summon", "Chronicles of Aurora"]

    if "log reflection" in t or "add reflection" in t:
        after = t.split("reflection", 1)[-1].lstrip(": ").strip()
        return ["log_reflection", after] if after else ["log_reflection"]

    # Journal entry commands
    if re.search(r"\b(create|start|begin|new)\b.*\b(entry|note|journal)\b", t):
        return ["create_journal_entry"]
    
    if re.search(r"\b(open|show|view)\b.*\b(journal|entries|notes)\b", t):
        return ["open_journal"]
    
    if re.search(r"\b(transcribe|record|dictate)\b", t):
        return ["start_transcription"]

    return None
