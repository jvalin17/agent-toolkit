#!/usr/bin/env python3
"""Compliance tracking + evidence-based verification.

Tracks which role rules the LLM follows vs ignores per session.
Requires evidence (actual command output, file:line references) for claims.

Usage:
  from compliance import ComplianceTracker, verify_evidence

  # Track rule compliance
  tracker = ComplianceTracker(session_dir)
  tracker.record("backend", "paginate all list endpoints", "obeyed",
                  evidence="src/routes/stats.ts:42")

  # Get summary
  summary = tracker.summary()
  # → {"total": 10, "obeyed": 8, "violated": 2, "compliance_rate": 80.0, ...}

  # Verify evidence for a claim
  result = verify_evidence("all tests pass", "$ pytest\n24 passed")
  # → {"verified": True}
"""

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


COMPLIANCE_FILE = "compliance.json"


def get_user_requests() -> List[str]:
    """Extract meaningful user prompts from session JSONL.

    Filters out: commands, system messages, short replies (<20 chars).
    Returns list of user requests — what they actually asked for.
    Use in /reviewer to verify code delivers what was asked.
    """
    claude_projects = Path.home() / ".claude" / "projects"
    if not claude_projects.is_dir():
        return []

    cwd_slug = str(Path.cwd()).replace("/", "-")
    project_dir = None
    for d in claude_projects.iterdir():
        if cwd_slug.lstrip("-") in d.name:
            project_dir = d
            break

    if not project_dir:
        return []

    logs = sorted(project_dir.glob("*.jsonl"), key=lambda p: p.stat().st_mtime)
    if not logs:
        return []

    requests = []
    for line in logs[-1].read_text(errors="ignore").split("\n"):
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
    claude_projects = Path.home() / ".claude" / "projects"
    if not claude_projects.is_dir():
        return {"available": False, "reason": "no Claude Code logs found"}

    # Find current project's log dir
    cwd_slug = str(Path.cwd()).replace("/", "-")
    project_dir = None
    for d in claude_projects.iterdir():
        if cwd_slug.lstrip("-") in d.name:
            project_dir = d
            break

    if not project_dir:
        return {"available": False, "reason": "no logs for current project"}

    # Find latest session JSONL
    logs = sorted(project_dir.glob("*.jsonl"), key=lambda p: p.stat().st_mtime)
    if not logs:
        return {"available": False, "reason": "no session logs found"}

    log_path = logs[-1]
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

# --- Session action auditing (mechanical verification) --------------------

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
    tool_index = 0

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

                # Track Edit/Write for TDD ordering
                elif name in ("Edit", "Write"):
                    file_path = inp.get("file_path", "")
                    is_test = bool(TEST_FILE_PATTERN.search(file_path))
                    if is_test and first_test_edit_index is None:
                        first_test_edit_index = tool_index
                    elif not is_test and first_source_edit_index is None:
                        first_source_edit_index = tool_index

        except (json.JSONDecodeError, TypeError, KeyError):
            continue

    # TDD: test file must be edited before source file
    # Vacuously true if no edits or only one type of file edited
    tdd_order_respected = True
    if first_test_edit_index is not None and first_source_edit_index is not None:
        tdd_order_respected = first_test_edit_index < first_source_edit_index

    return {
        "available": True,
        "server_started": server_started,
        "http_request_made": http_request_made,
        "role_agents_spawned": role_agents_spawned,
        "tdd_order_respected": tdd_order_respected,
    }


# --- Git diff TDD check ---------------------------------------------------

# Patterns for function/method definitions (added lines only)
FUNCTION_DEF_PATTERNS = [
    # Python: def func_name(
    re.compile(r"^\+\s*def\s+(\w+)\s*\("),
    # JS/TS: function funcName(  or  const funcName = (  or  funcName(
    re.compile(r"^\+\s*(?:export\s+)?(?:async\s+)?function\s+(\w+)\s*\("),
    # Go: func FuncName(
    re.compile(r"^\+\s*func\s+(?:\(\w+\s+\*?\w+\)\s+)?(\w+)\s*\("),
    # Rust: fn func_name(
    re.compile(r"^\+\s*(?:pub\s+)?fn\s+(\w+)\s*\("),
    # Java/C#: public void methodName(
    re.compile(r"^\+\s*(?:public|private|protected|static|\s)*\s+(\w+)\s*\("),
]

# Dunder / magic methods to ignore
DUNDER_RE = re.compile(r"^__\w+__$")

# Files/dirs exempt from TDD diff check
DIFF_TDD_EXEMPT_DIRS = re.compile(
    r"(^|/)(hooks|scripts|migrations|\.github|templates|config|docs)(/|$)"
)

DIFF_TEST_FILE_PATTERN = re.compile(
    r"(test_|_test\.|\.test\.|\.spec\.|tests/|__tests__/|spec/)",
    re.IGNORECASE,
)


def check_diff_for_untested_functions(diff_text: str) -> List[str]:
    """Scan a unified diff for new functions/methods without corresponding tests.

    Returns list of warning strings, one per untested function.
    Empty list = all new functions have tests (or no new functions).
    """
    if not diff_text.strip():
        return []

    # Parse diff into per-file sections
    current_file = None
    source_functions: Dict[str, List[str]] = {}  # file -> [func_names]
    test_functions: List[str] = []

    for line in diff_text.split("\n"):
        # Track which file we're in
        if line.startswith("diff --git"):
            match = re.search(r"b/(.+)$", line)
            if match:
                current_file = match.group(1)
            continue

        if current_file is None:
            continue

        # Only look at added lines
        if not line.startswith("+"):
            continue

        is_test_file = bool(DIFF_TEST_FILE_PATTERN.search(current_file))
        is_exempt = bool(DIFF_TDD_EXEMPT_DIRS.search(current_file))

        for pattern in FUNCTION_DEF_PATTERNS:
            m = pattern.match(line)
            if m:
                func_name = m.group(1)
                # Skip dunder methods
                if DUNDER_RE.match(func_name):
                    break
                if is_test_file:
                    test_functions.append(func_name)
                elif not is_exempt:
                    if current_file not in source_functions:
                        source_functions[current_file] = []
                    source_functions[current_file].append(func_name)
                break

    # Check each source function for a corresponding test
    warnings = []
    for filepath, funcs in source_functions.items():
        for func in funcs:
            # Look for test_<func> or <func> mentioned in any test function name
            has_test = any(
                func in test_name or func.lower() in test_name.lower()
                for test_name in test_functions
            )
            if not has_test:
                warnings.append(
                    f"{filepath}: new function '{func}' has no corresponding test"
                )

    return warnings


# Patterns that indicate real evidence (command output, file references)
EVIDENCE_PATTERNS = [
    re.compile(r"\$\s+\w"),          # command: $ pytest, $ curl
    re.compile(r"\w+\.\w+:\d+"),     # file:line: src/app.ts:42
    re.compile(r"\d+ passed"),        # test output: 24 passed
    re.compile(r"HTTP/\d"),           # HTTP response
    re.compile(r"\{.*:.*\}"),         # JSON output
    re.compile(r"status.*\d{3}"),     # status code
    re.compile(r"✓|✗|PASS|FAIL"),    # test markers
]

# Minimum evidence length to not be "vague"
MIN_EVIDENCE_LENGTH = 20


class ComplianceTracker:
    """Track role rule compliance across a session."""

    def __init__(self, session_dir: Path):
        self.filepath = session_dir / COMPLIANCE_FILE
        self._ensure_file()

    def _ensure_file(self) -> None:
        if not self.filepath.exists():
            self.filepath.parent.mkdir(parents=True, exist_ok=True)
            self.filepath.write_text(json.dumps({
                "records": [],
                "session_start": datetime.now().isoformat(),
            }, indent=2))

    def load(self) -> Dict[str, Any]:
        try:
            return json.loads(self.filepath.read_text())
        except (json.JSONDecodeError, OSError):
            return {"records": [], "session_start": datetime.now().isoformat()}

    def _save(self, data: Dict[str, Any]) -> None:
        self.filepath.write_text(json.dumps(data, indent=2))

    def record(
        self,
        role: str,
        rule: str,
        status: str,
        evidence: str = "",
    ) -> None:
        """Record a compliance check result.

        Args:
            role: Role name (e.g., "backend", "security")
            rule: Rule description (e.g., "paginate all list endpoints")
            status: "obeyed" or "violated"
            evidence: File:line reference, command output, or other proof
        """
        data = self.load()
        data["records"].append({
            "role": role,
            "rule": rule,
            "status": status,
            "evidence": evidence,
            "timestamp": datetime.now().isoformat(),
        })
        self._save(data)

    def summary(self) -> Dict[str, Any]:
        """Get compliance summary with per-role breakdown."""
        data = self.load()
        records = data.get("records", [])

        if not records:
            return {
                "total": 0,
                "obeyed": 0,
                "violated": 0,
                "compliance_rate": 100.0,
                "by_role": {},
            }

        obeyed = sum(1 for r in records if r["status"] == "obeyed")
        violated = sum(1 for r in records if r["status"] == "violated")
        total = len(records)

        # Per-role breakdown
        by_role: Dict[str, Dict[str, int]] = {}
        for record in records:
            role = record["role"]
            if role not in by_role:
                by_role[role] = {"obeyed": 0, "violated": 0}
            by_role[role][record["status"]] = by_role[role].get(record["status"], 0) + 1

        return {
            "total": total,
            "obeyed": obeyed,
            "violated": violated,
            "compliance_rate": round((obeyed / total) * 100, 1) if total > 0 else 100.0,
            "by_role": by_role,
        }

    def violated_rules(self) -> List[Dict[str, str]]:
        """Get list of violated rules with evidence."""
        data = self.load()
        return [
            r for r in data.get("records", [])
            if r["status"] == "violated"
        ]

    def to_text(self) -> str:
        """Human-readable compliance report."""
        s = self.summary()
        lines = [
            f"Compliance: {s['compliance_rate']}% ({s['obeyed']}/{s['total']} rules followed)",
        ]
        if s["violated"] > 0:
            lines.append(f"Violated ({s['violated']}):")
            for v in self.violated_rules():
                lines.append(f"  [{v['role']}] {v['rule']} — {v['evidence']}")
        for role, counts in s.get("by_role", {}).items():
            lines.append(f"  {role}: {counts.get('obeyed', 0)} obeyed, {counts.get('violated', 0)} violated")
        return "\n".join(lines)


def verify_evidence(claim: str, evidence: str) -> Dict[str, Any]:
    """Verify that evidence is sufficient to support a claim.

    Evidence must be concrete: command output, file:line references,
    HTTP responses, test results. Not just "it works" or "tests pass."

    Returns:
        {"verified": True/False, "reason": "..."}
    """
    if not evidence or not evidence.strip():
        return {
            "verified": False,
            "reason": "No evidence provided. Include command output, file:line references, or test results.",
        }

    evidence = evidence.strip()

    # Too short = vague
    if len(evidence) < MIN_EVIDENCE_LENGTH:
        return {
            "verified": False,
            "reason": f"Insufficient evidence (only {len(evidence)} chars). "
                      "Include actual command output or file:line references.",
        }

    # Check for real evidence patterns
    has_pattern = any(p.search(evidence) for p in EVIDENCE_PATTERNS)

    if not has_pattern:
        return {
            "verified": False,
            "reason": "Insufficient evidence. Must include at least one of: "
                      "command output ($ ...), file:line reference (file.ts:42), "
                      "test results (N passed), or HTTP response.",
        }

    return {
        "verified": True,
        "reason": "Evidence includes concrete output.",
    }
