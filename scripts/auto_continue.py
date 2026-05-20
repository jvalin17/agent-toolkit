#!/usr/bin/env python3
"""Auto-continuation wrapper — manages Claude Code session lifecycle.

Outer loop that launches Claude Code sessions, detects when context is
exhausted (via HANDOFF.md), and relaunches fresh sessions until the goal
is achieved or marked COMPLETE.

Usage:
    python scripts/auto_continue.py "Build auth system"
    python scripts/auto_continue.py --headless "Build auth system"
    python scripts/auto_continue.py --max-budget-usd 5.00 "Build auth system"

Goal resolution: CLI arg > HANDOFF.md ## Goal > interactive prompt.
"""

import argparse
import json
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


class AutoContinue:
    """Manages Claude Code session lifecycle for multi-session tasks."""

    def __init__(
        self,
        goal: Optional[str],
        max_budget: Optional[float],
        project_dir: Path,
        headless: bool = True,
    ):
        self.goal = goal
        self.max_budget = max_budget
        self.project_dir = project_dir
        self.headless = headless
        self.handoff_file = project_dir / "HANDOFF.md"
        self.history_log = project_dir / "handoff-history.log"
        self.session_count = 0

    def run(self) -> int:
        """Main loop. Returns 0 on success, 1 on failure."""
        self.goal = self._resolve_goal()
        if not self.goal:
            print("No goal provided. Exiting.")
            return 1

        self._seed_handoff()

        while True:
            self.session_count += 1
            self._clean_session_dir()

            prompt = self._build_prompt()
            print(f"\n--- Session {self.session_count} starting ---")
            exit_code = self._launch_session(prompt)

            if self._is_complete():
                self._log_history("COMPLETE")
                print(
                    f"\nGoal reached in {self.session_count} session(s)."
                )
                return 0

            # Not complete — log handoff and continue
            self._log_history("HANDOFF")
            reason = self._detect_exit_reason()
            print(
                f"Session {self.session_count} ended ({reason}). "
                f"Continuing..."
            )

    def _resolve_goal(self) -> str:
        """Goal from: arg > HANDOFF.md > interactive prompt."""
        if self.goal:
            return self.goal

        # Try HANDOFF.md
        if self.handoff_file.is_file():
            content = self.handoff_file.read_text(encoding="utf-8")
            goal_match = re.search(
                r"## Goal\s*\n\s*\n(.+?)(?:\n\s*\n|\n##|\Z)",
                content,
                re.DOTALL,
            )
            if goal_match:
                return goal_match.group(1).strip()

        # Interactive prompt
        return input("What's the goal? ")

    def _build_prompt(self) -> str:
        """Build the prompt for the Claude session."""
        if self.session_count == 1:
            return (
                f"Read HANDOFF.md. The goal is: {self.goal}. Begin working."
            )
        return (
            "Read HANDOFF.md and continue from where the previous "
            "session left off."
        )

    def _launch_session(self, prompt: str) -> int:
        """Launch a Claude Code session. Returns process exit code."""
        if self.headless:
            cmd = ["claude", "-p", prompt, "--output-format", "json"]
        else:
            cmd = ["claude", "--resume", prompt]

        if self.max_budget:
            cmd.extend(["--max-budget-usd", str(self.max_budget)])

        result = subprocess.run(cmd, cwd=self.project_dir)
        return result.returncode

    def _is_complete(self) -> bool:
        """Check if the goal is complete.

        Complete if: HANDOFF.md doesn't exist (agent cleaned up)
        or contains ## COMPLETE marker.
        """
        if not self.handoff_file.is_file():
            return True
        content = self.handoff_file.read_text(encoding="utf-8")
        return "## COMPLETE" in content

    def _seed_handoff(self) -> None:
        """Write initial HANDOFF.md with goal so first session has context.

        Does not overwrite an existing HANDOFF.md (resume scenario).
        """
        if self.handoff_file.is_file():
            return

        self.handoff_file.write_text(
            f"# HANDOFF\n\n"
            f"## Goal\n\n{self.goal}\n\n"
            f"## Status\n\nSession 1 — starting.\n",
            encoding="utf-8",
        )

    def _clean_session_dir(self) -> None:
        """Remove .session/ directory for a fresh context window."""
        session_dir = self.project_dir / ".session"
        if session_dir.exists():
            shutil.rmtree(session_dir)

    def _detect_exit_reason(self) -> str:
        """Determine why session ended."""
        state_file = self.project_dir / ".session" / "state.json"
        if state_file.is_file():
            try:
                state = json.loads(state_file.read_text(encoding="utf-8"))
                if state.get("stopped", 0) >= 1:
                    return "context_exhaustion"
            except (json.JSONDecodeError, OSError):
                pass  # Corrupt/unreadable state — fall through to HANDOFF.md check

        if self.handoff_file.is_file():
            return "context_exhaustion"

        return "unexpected_exit"

    def _log_history(self, event: str) -> None:
        """Append one line to handoff-history.log."""
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        line = (
            f"[{timestamp}] Session {self.session_count} | {event} | "
            f"Goal: {self.goal}\n"
        )
        with open(self.history_log, "a", encoding="utf-8") as log_file:
            log_file.write(line)


def parse_args(argv: Optional[list] = None) -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Auto-continuation wrapper for Claude Code sessions.",
    )
    parser.add_argument(
        "goal",
        nargs="?",
        default=None,
        help="Goal description for the task.",
    )
    parser.add_argument(
        "--headless",
        action="store_true",
        default=False,
        help="Run in headless mode (uses claude -p).",
    )
    parser.add_argument(
        "--max-budget-usd",
        type=float,
        default=None,
        help="Maximum budget in USD.",
    )
    parser.add_argument(
        "--project-dir",
        type=str,
        default=".",
        help="Project directory (default: current directory).",
    )
    return parser.parse_args(argv)


def main() -> int:
    """Entry point."""
    args = parse_args()
    runner = AutoContinue(
        goal=args.goal,
        max_budget=args.max_budget_usd,
        project_dir=Path(args.project_dir).resolve(),
        headless=args.headless,
    )
    return runner.run()


if __name__ == "__main__":
    sys.exit(main())
