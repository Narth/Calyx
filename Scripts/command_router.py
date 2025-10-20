# Command Router v1.0
# Converts natural phrases into console commands.
import re

def route(text):
    t = text.lower().strip()

    # Begin session
    if re.search(r"\b(begin|start)\b.*\bsession\b", t):
        return ["begin_session"]

    # Summon project
    m = re.search(r"\bsummon\b\s+(.*)$", t)
    if m:
        return ["summon", m.group(1).strip()]

    # Log reflection
    # Example: "log reflection: today was good"
    if "log reflection" in t or "add reflection" in t:
        after = t.split("reflection", 1)[-1].lstrip(": ").strip()
        return ["log_reflection", after] if after else ["log_reflection"]

    return None