"""Session JSONL analysis — read Claude Code logs for audit and summary.

Extracted from compliance.py. Contains:
- get_user_requests: extract user prompts from session
- get_session_skill_usage: verify which skills were called
- audit_session_actions: mechanical verification of session actions
- generate_session_summary: produce markdown summary of toolkit usage
"""

import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional


# --- Session JSONL reading ---------------------------------------------------


def get_user_requests() -> List[str]:
    """Extract meaningful user prompts from session JSONL.

    Filters out: commands, system messages, short replies (<20 chars).
    Returns list of user requests — what they actually asked for.
    Use in /reviewer to verify code delivers what was asked.
    """
    from hooks.session_log import find_latest_session_log

    log_path = find_latest_session_log()
    if not log_path:
        return []

    requests = []
    for line in log_path.read_text(errors="ignore").split("\n"):
        if not line.strip():
            continue
        try:
            entry = json.loads(line)
            if entry.get("type") != "user":
                continue
            msg = entry.get("message", {})
            content = msg.get("content", "")

            text = ""
            if isinstance(content, str):
                text = content
            elif isinstance(content, list):
                for block in content:
                    if block.get("type") == "text":
                        text = block.get("text", "")
                        break

            # Filter: skip commands, system messages, short replies
            if not text or len(text) < 20:
                continue
            if text.startswith("<local-command") or text.startswith("<command"):
                continue
            if text.startswith("<system-reminder"):
                continue

            requests.append(text[:300])  # cap each at 300 chars
        except (json.JSONDecodeError, TypeError, KeyError):
            pass

    return requests


def get_session_skill_usage() -> Dict[str, Any]:
    """Read Claude Code session log to verify which skills were actually called.

    Returns tool call counts, skills invoked, agents spawned.
    Cannot be faked — JSONL is written by Claude Code, not the agent.
    """
    from hooks.session_log import find_latest_session_log

    log_path = find_latest_session_log()
    if not log_path:
        return {"available": False, "reason": "no session logs found"}
    tools: Dict[str, int] = {}
    skills: list = []

    for line in log_path.read_text(errors="ignore").split("\n"):
        if not line.strip():
            continue
        try:
            entry = json.loads(line)
            msg = entry.get("message", {})
            content = msg.get("content", [])
            if isinstance(content, list):
                for block in content:
                    if block.get("type") == "tool_use":
                        name = block.get("name", "")
                        tools[name] = tools.get(name, 0) + 1
                        if name == "Skill":
                            skill = block.get("input", {}).get("skill", "?")
                            skills.append(skill)
        except (json.JSONDecodeError, TypeError, KeyError):
            pass

    # Check Agent model usage
    agents = []
    agents_without_model = 0
    for line in log_path.read_text(errors="ignore").split("\n"):
        if not line.strip():
            continue
        try:
            entry = json.loads(line)
            msg = entry.get("message", {})
            content = msg.get("content", [])
            if isinstance(content, list):
                for block in content:
                    if block.get("type") == "tool_use" and block.get("name") == "Agent":
                        inp = block.get("input", {})
                        model = inp.get("model", "")
                        desc = inp.get("description", "?")
                        agents.append({"description": desc, "model": model or "NOT SET"})
                        if not model:
                            agents_without_model += 1
        except (json.JSONDecodeError, TypeError, KeyError):
            pass

    return {
        "available": True,
        "session_id": log_path.stem,
        "tools": tools,
        "skills": skills,
        "skill_count": len(skills),
        "precommit_called": "precommit" in skills,
        "agents": agents,
        "agents_without_model": agents_without_model,
        "taxonomy_violations": agents_without_model,
    }


# --- Session action auditing -------------------------------------------------

# Patterns that indicate a server was started
SERVER_START_PATTERNS = [
    re.compile(r"npm\s+(start|run\s+dev|run\s+serve)"),
    re.compile(r"node\s+\S+\.(js|ts)"),
    re.compile(r"python3?\s+(-m\s+)?(flask|uvicorn|gunicorn|django|http\.server)"),
    re.compile(r"(rails|ruby)\s+\S*(server|s\b)"),
    re.compile(r"go\s+run"),
    re.compile(r"cargo\s+run"),
    re.compile(r"java\s+-jar"),
    re.compile(r"docker\s+(compose\s+up|run)"),
    re.compile(r"(yarn|pnpm|npx)\s+(start|dev|serve)"),
]

# Patterns that indicate an HTTP request was made
HTTP_REQUEST_PATTERNS = [
    re.compile(r"curl\s+"),
    re.compile(r"wget\s+"),
    re.compile(r"http(s)?://localhost"),
    re.compile(r"http(s)?://127\.0\.0\.1"),
    re.compile(r"http(s)?://0\.0\.0\.0"),
]

# Patterns in Agent prompts that indicate role-based review
ROLE_AGENT_PATTERNS = [
    re.compile(r"\brole\b.*\breview\b", re.IGNORECASE),
    re.compile(r"\breview\b.*\brole\b", re.IGNORECASE),
    re.compile(r"\b(qa|security|backend|frontend|dba|architect|infrastructure|legal)\b.*\b(check|review|audit)\b", re.IGNORECASE),
    re.compile(r"\b(check|review|audit)\b.*\b(qa|security|backend|frontend|dba|architect|infrastructure|legal)\b", re.IGNORECASE),
]

# Test file path patterns
TEST_FILE_PATTERN = re.compile(
    r"(test_|_test\.|\.test\.|\.spec\.|tests/|__tests__/|spec/)",
    re.IGNORECASE,
)


def audit_session_actions(log_path: Path) -> Dict[str, Any]:
    """Read session JSONL and mechanically verify what actions happened.

    Returns dict with:
        available: bool — whether the log could be read
        server_started: bool — was a dev server started?
        http_request_made: bool — was an HTTP request made to localhost?
        role_agents_spawned: int — how many role-specific agents were spawned?
        tdd_order_respected: bool — were test files edited before source files?
    """
    if not log_path.is_file():
        return {"available": False, "reason": f"log not found: {log_path}"}

    server_started = False
    http_request_made = False
    role_agents_spawned = 0
    first_test_edit_index = None
    first_source_edit_index = None
    first_test_plan_write_index = None
    tool_index = 0

    # Skill adherence: track Skill invocations and whether SKILL.md was read
    # Each entry: {"skill": name, "followed": bool}
    skill_invocations: List[dict] = []
    current_skill: Optional[str] = None  # skill awaiting a SKILL.md Read

    try:
        text = log_path.read_text(errors="ignore")
    except OSError:
        return {"available": False, "reason": "cannot read log file"}

    for line in text.split("\n"):
        if not line.strip():
            continue
        try:
            entry = json.loads(line)
            msg = entry.get("message", {})
            content = msg.get("content", [])
            if not isinstance(content, list):
                continue

            for block in content:
                if block.get("type") != "tool_use":
                    continue

                name = block.get("name", "")
                inp = block.get("input", {})
                tool_index += 1

                # Skill adherence: track Skill invocations and Read of SKILL.md
                # Skills that are self-contained (expanded inline, no SKILL.md read needed)
                _SELF_CONTAINED_SKILLS = {
                    "precommit", "agent-toolkit-mode", "agent-toolkit:precommit",
                    "simplify", "loop", "schedule", "claude-api",
                    "keybindings-help", "update-config",
                }
                if name == "Skill":
                    skill_name = inp.get("skill", "?")
                    # Finalize previous skill if any
                    if current_skill is not None:
                        skill_invocations.append({"skill": current_skill, "followed": False})
                    # Self-contained skills are always "followed"
                    if skill_name in _SELF_CONTAINED_SKILLS:
                        skill_invocations.append({"skill": skill_name, "followed": True})
                        current_skill = None
                    else:
                        current_skill = skill_name
                elif name == "Read" and current_skill:
                    file_path_read = inp.get("file_path", "")
                    # Check if this reads the SKILL.md for the current skill
                    expected = f"skills/{current_skill}/SKILL.md"
                    if expected in file_path_read:
                        skill_invocations.append({"skill": current_skill, "followed": True})
                        current_skill = None

                # Check Bash commands for server starts and HTTP requests
                if name == "Bash":
                    cmd = inp.get("command", "")
                    if any(p.search(cmd) for p in SERVER_START_PATTERNS):
                        server_started = True
                    if any(p.search(cmd) for p in HTTP_REQUEST_PATTERNS):
                        http_request_made = True

                # Check WebFetch as HTTP request
                elif name == "WebFetch":
                    url = inp.get("url", "")
                    if "localhost" in url or "127.0.0.1" in url or "0.0.0.0" in url:
                        http_request_made = True

                # Check Agent spawns for role-related prompts
                elif name == "Agent":
                    prompt = inp.get("prompt", "") + " " + inp.get("description", "")
                    if any(p.search(prompt) for p in ROLE_AGENT_PATTERNS):
                        role_agents_spawned += 1

                # Track Edit/Write for TDD ordering and test plan ordering
                elif name in ("Edit", "Write"):
                    file_path = inp.get("file_path", "")
                    # Track test plan writes
                    if "test-plan_" in file_path and ".scratch" in file_path:
                        if first_test_plan_write_index is None:
                            first_test_plan_write_index = tool_index
                    else:
                        is_test = bool(TEST_FILE_PATTERN.search(file_path))
                        if is_test and first_test_edit_index is None:
                            first_test_edit_index = tool_index
                        elif not is_test and first_source_edit_index is None:
                            first_source_edit_index = tool_index

        except (json.JSONDecodeError, TypeError, KeyError):
            continue

    # Finalize trailing skill (invoked but never followed by end of log)
    if current_skill is not None:
        skill_invocations.append({"skill": current_skill, "followed": False})

    # Skill adherence summary
    followed_count = sum(1 for s in skill_invocations if s["followed"])
    hollow = [s["skill"] for s in skill_invocations if not s["followed"]]

    # TDD: test file must be edited before source file
    # Vacuously true if no edits or only one type of file edited
    tdd_order_respected = True
    if first_test_edit_index is not None and first_source_edit_index is not None:
        tdd_order_respected = first_test_edit_index < first_source_edit_index

    # Test plan ordering: plan must be written before first source edit
    # Vacuously true if no source edits or no test plan
    test_plan_before_source = True
    if first_source_edit_index is not None and first_test_plan_write_index is not None:
        test_plan_before_source = first_test_plan_write_index < first_source_edit_index
    elif first_source_edit_index is not None and first_test_plan_write_index is None:
        # Source was edited but no test plan was ever written — still vacuously true
        # (the _require_test_plan check handles the "no plan at all" case)
        pass

    return {
        "available": True,
        "server_started": server_started,
        "http_request_made": http_request_made,
        "role_agents_spawned": role_agents_spawned,
        "tdd_order_respected": tdd_order_respected,
        "test_plan_before_source": test_plan_before_source,
        "skill_adherence": {
            "invoked": len(skill_invocations),
            "followed": followed_count,
            "hollow": hollow,
        },
    }


# --- Session summary ---------------------------------------------------------

# Pattern to extract test results from pytest output
TEST_RESULT_PATTERN = re.compile(r"(\d+)\s+passed(?:,\s*(\d+)\s+(?:skipped|failed|error))?")

# Role names to detect in agent prompts
ROLE_NAMES = [
    "qa", "security", "backend", "frontend", "dba", "architect",
    "infrastructure", "legal", "data-engineer", "data-scientist",
    "embedded", "ios", "android", "game-dev", "research",
    "production", "code-health", "ai-ml", "requirements-eng",
]


def generate_session_summary(log_path: Path) -> str:
    """Read a session JSONL and produce a markdown summary of toolkit usage.

    Extracts: skills used, files changed, test results, roles checked.
    Returns a markdown string suitable for appending to project-state.md.
    """
    if not log_path.is_file():
        return "Session summary unavailable — log not found."

    try:
        text = log_path.read_text(errors="ignore")
    except OSError:
        return "Session summary unavailable — cannot read log."

    skills: List[str] = []
    files_changed: set = set()
    test_results: List[str] = []
    roles_checked: set = set()

    for line in text.split("\n"):
        if not line.strip():
            continue
        try:
            entry = json.loads(line)
            msg = entry.get("message", {})
            content = msg.get("content", "")

            # Handle tool_result entries (test output as string)
            if isinstance(content, str):
                m = TEST_RESULT_PATTERN.search(content)
                if m:
                    test_results.append(m.group(0))
                continue

            if not isinstance(content, list):
                continue

            # Also check list-form content for tool_result text blocks
            for text_block in content:
                if isinstance(text_block, dict) and text_block.get("type") == "text":
                    txt = text_block.get("text", "")
                    m = TEST_RESULT_PATTERN.search(txt)
                    if m:
                        test_results.append(m.group(0))

            for block in content:
                block_type = block.get("type", "")
                name = block.get("name", "")
                inp = block.get("input", {})

                if block_type == "tool_use":
                    # Skills invoked
                    if name == "Skill":
                        skill = inp.get("skill", "?")
                        if skill not in skills:
                            skills.append(skill)

                    # Files changed
                    elif name in ("Edit", "Write"):
                        fp = inp.get("file_path", "")
                        if fp:
                            # Keep just filename for brevity
                            files_changed.add(fp.split("/")[-1])

                    # Role agents
                    elif name == "Agent":
                        prompt = (inp.get("prompt", "") + " " + inp.get("description", "")).lower()
                        for role in ROLE_NAMES:
                            if role in prompt and ("review" in prompt or "check" in prompt or "audit" in prompt):
                                roles_checked.add(role)

                    # Test results from Bash output
                    elif name == "Bash":
                        cmd = inp.get("command", "")
                        if "pytest" in cmd or "test" in cmd:
                            pass  # results come in tool_result

                # Check tool_result text for test output
                elif block_type == "tool_result":
                    result_text = block.get("content", "")
                    if isinstance(result_text, str):
                        m = TEST_RESULT_PATTERN.search(result_text)
                        if m:
                            test_results.append(m.group(0))

        except (json.JSONDecodeError, TypeError, KeyError):
            continue

    # No toolkit activity
    if not skills and not files_changed and not test_results and not roles_checked:
        return "No toolkit activity detected in this session."

    # Build summary
    lines = ["## Session Summary", ""]

    if skills:
        lines.append(f"**Skills used:** {', '.join(f'/{s}' for s in skills)}")

    if roles_checked:
        lines.append(f"**Roles checked:** {', '.join(sorted(roles_checked))}")

    if files_changed:
        file_list = ", ".join(sorted(files_changed))
        if len(file_list) > 200:
            file_list = file_list[:200] + "..."
        lines.append(f"**Files changed:** {file_list}")

    if test_results:
        # Use the last test result (most recent run)
        lines.append(f"**Tests:** {test_results[-1]}")

    return "\n".join(lines)
