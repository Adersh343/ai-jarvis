import re

_BLOCKED_PATTERNS = [
    r'\brm\s+-[rRfF]{2,}\b',
    r'\brm\s+--no-preserve-root\b',
    r'\bmkfs\b',
    r'\bdd\s+if=',
    r':\(\)\{.*\}',
    r'\bsudo\s+rm\b',
    r'>\s*/dev/sd',
    r'\bshutdown\b',
    r'\breboot\b',
    r'\bhalt\b',
    r'\bpoweroff\b',
    r'(curl|wget).*\|\s*(ba)?sh',
]


def is_safe(command: str) -> tuple[bool, str]:
    for pattern in _BLOCKED_PATTERNS:
        if re.search(pattern, command, re.IGNORECASE):
            return False, f"blocked pattern: {pattern}"
    return True, ""


def filter_commands(commands: list[str]) -> tuple[list[str], list[dict]]:
    safe, blocked = [], []
    for cmd in commands:
        cmd = cmd.strip()
        if not cmd:
            continue
        ok, reason = is_safe(cmd)
        if ok:
            safe.append(cmd)
        else:
            blocked.append({"command": cmd, "reason": reason})
    return safe, blocked
