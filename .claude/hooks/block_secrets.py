#!/usr/bin/env python3
import json
import re
import sys

# Matches:
#   .env
#   .env.local
#   .env.production
#   .env*
#   .env?
#   .env[...]
ENV_SEGMENT_RE = re.compile(r"^\.env($|\..+|[\*\?\[].*)", re.IGNORECASE)

# Simple tokenization for common Bash commands/args
TOKEN_RE = re.compile(r'''(?:"([^"]+)"|'([^']+)'|([^\s|&;<>]+))''')


def emit_deny(reason: str) -> None:
    json.dump(
        {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
                "permissionDecisionReason": reason,
            }
        },
        sys.stdout,
    )
    sys.stdout.write("\n")
    sys.exit(0)


def normalize(value: str) -> str:
    return (value or "").replace("\\", "/").strip()


def is_protected_pathish(value: str) -> bool:
    """
    Block:
      - any path/file segment that is .env or .env.*
      - anything containing 'secret' anywhere in the path, case-insensitive
    """
    v = normalize(value)
    if not v:
        return False

    lower_v = v.lower()

    if "secret" in lower_v:
        return True

    for segment in lower_v.split("/"):
        if ENV_SEGMENT_RE.match(segment):
            return True

    return False


def find_blocked_bash_target(command: str) -> str | None:
    if not command:
        return None

    for match in TOKEN_RE.finditer(command):
        token = next(group for group in match.groups() if group is not None)
        if is_protected_pathish(token):
            return token

    # Fallback for shell syntax that tokenization may miss
    if re.search(r'(^|[\s="\'`])\.env($|[\s/"\'`]|[.][^\s/"\'`]+)', command, re.IGNORECASE):
        return ".env"

    if re.search(r"secret", command, re.IGNORECASE):
        return "secret"

    return None


def main() -> None:
    try:
        data = json.load(sys.stdin)
    except Exception:
        emit_deny("Blocked: could not parse hook input safely.")

    tool_name = data.get("tool_name", "")
    tool_input = data.get("tool_input", {}) or {}

    # File/path-like inputs used by Claude Code tools
    candidates = []

    file_path = tool_input.get("file_path")
    if isinstance(file_path, str) and file_path:
        candidates.append(file_path)

    path_value = tool_input.get("path")
    if isinstance(path_value, str) and path_value:
        candidates.append(path_value)

    # Glob uses `pattern`
    if tool_name == "Glob":
        pattern = tool_input.get("pattern")
        if isinstance(pattern, str) and pattern:
            candidates.append(pattern)

    # Grep may constrain files via `glob`
    if tool_name == "Grep":
        glob_value = tool_input.get("glob")
        if isinstance(glob_value, str) and glob_value:
            candidates.append(glob_value)

    for candidate in candidates:
        if is_protected_pathish(candidate):
            emit_deny(f"Blocked: access to protected path is not allowed: {candidate}")

    # Prevent easy shell bypasses like:
    #   cat .env
    #   sed -i ... secrets/app.env
    #   grep ... ./secret-config/
    if tool_name == "Bash":
        command = tool_input.get("command", "")
        blocked_target = find_blocked_bash_target(command)
        if blocked_target:
            emit_deny(
                f"Blocked: Bash command references a protected path or file: {blocked_target}"
            )

    sys.exit(0)


if __name__ == "__main__":
    main()