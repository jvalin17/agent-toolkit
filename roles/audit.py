#!/usr/bin/env python3
"""Session audit — see what the agent actually did.

Shows tool calls, skill invocations, agent spawns, and role usage.
Reads Claude Code session JSONL logs.

Usage:
  python3 roles/audit.py                    # current/latest session
  python3 roles/audit.py <session-id>       # specific session
  python3 roles/audit.py --all              # all sessions for current project
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Dict, List, Optional


def find_session_logs(project_dir: Optional[Path] = None) -> List[Path]:
    """Find Claude Code session JSONL files for a project."""
    claude_dir = Path.home() / ".claude" / "projects"
    if not claude_dir.is_dir():
        return []

    if project_dir is None:
        project_dir = Path.cwd()

    # Convert project path to Claude's directory naming
    project_slug = str(project_dir).replace("/", "-")
    project_log_dir = claude_dir / project_slug

    if not project_log_dir.is_dir():
        # Try to find a match
        for d in claude_dir.iterdir():
            if str(project_dir).replace("/", "-").lstrip("-") in d.name:
                project_log_dir = d
                break

    if not project_log_dir.is_dir():
        return []

    return sorted(project_log_dir.glob("*.jsonl"), key=lambda p: p.stat().st_mtime)


def parse_session(log_path: Path) -> Dict:
    """Parse a session JSONL file into structured audit data."""
    tools: Dict[str, int] = {}
    skills: List[str] = []
    agents: List[str] = []
    role_mentions: Dict[str, int] = {}
    total_entries = 0

    for line in log_path.read_text(errors="ignore").split("\n"):
        if not line.strip():
            continue
        total_entries += 1

        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            continue

        msg = entry.get("message", {})
        content = msg.get("content", [])

        if isinstance(content, list):
            for block in content:
                if block.get("type") == "tool_use":
                    name = block.get("name", "unknown")
                    tools[name] = tools.get(name, 0) + 1

                    if name == "Skill":
                        skill = block.get("input", {}).get("skill", "?")
                        skills.append(skill)

                    elif name == "Agent":
                        desc = block.get("input", {}).get("description", "?")
                        agents.append(desc)

        # Check for role mentions in hook context
        if isinstance(content, str) and "ACTIVE ROLES:" in content:
            # Extract role names
            for part in content.split("ACTIVE ROLES:")[1:]:
                roles_line = part.split("\n")[0].strip()
                for role in roles_line.split(","):
                    role = role.strip()
                    if role:
                        role_mentions[role] = role_mentions.get(role, 0) + 1

    return {
        "session_id": log_path.stem,
        "file": str(log_path),
        "total_entries": total_entries,
        "tools": tools,
        "skills": skills,
        "agents": agents,
        "role_mentions": role_mentions,
    }


def format_audit(data: Dict) -> str:
    """Format audit data as readable text."""
    lines = [
        f"Session: {data['session_id']}",
        f"Entries: {data['total_entries']}",
        "",
        "Tool Calls:",
    ]

    for name, count in sorted(data["tools"].items(), key=lambda x: -x[1]):
        lines.append(f"  {name}: {count}")

    lines.append(f"\nSkills Invoked ({len(data['skills'])}):")
    for s in data["skills"]:
        lines.append(f"  /{s}")
    if not data["skills"]:
        lines.append("  (none)")

    lines.append(f"\nAgent Spawns ({len(data['agents'])}):")
    for a in data["agents"]:
        lines.append(f"  {a}")
    if not data["agents"]:
        lines.append("  (none)")

    if data["role_mentions"]:
        lines.append(f"\nRoles Detected:")
        for role, count in sorted(data["role_mentions"].items(), key=lambda x: -x[1]):
            lines.append(f"  {role}: mentioned {count}x")

    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit agent session — what did it actually do?")
    parser.add_argument("session_id", nargs="?", help="Session ID (default: latest)")
    parser.add_argument("--all", action="store_true", help="Show all sessions")
    parser.add_argument("--json", action="store_true", help="JSON output")

    args = parser.parse_args()

    logs = find_session_logs()
    if not logs:
        print("No session logs found.", file=sys.stderr)
        return 1

    if args.all:
        for log in logs:
            data = parse_session(log)
            if args.json:
                print(json.dumps(data, indent=2))
            else:
                print(format_audit(data))
                print("\n" + "=" * 40 + "\n")
    else:
        if args.session_id:
            log = next((l for l in logs if args.session_id in l.stem), None)
            if not log:
                print(f"Session {args.session_id} not found.", file=sys.stderr)
                return 1
        else:
            log = logs[-1]  # latest

        data = parse_session(log)
        if args.json:
            print(json.dumps(data, indent=2))
        else:
            print(format_audit(data))

    return 0


if __name__ == "__main__":
    sys.exit(main())
