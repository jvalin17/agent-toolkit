#!/usr/bin/env python3
"""Auto-continuation wrapper — manages Claude Code session lifecycle.

Outer loop that launches Claude Code sessions in headless mode (claude -p),
detects when context is exhausted (via HANDOFF.md), and relaunches fresh
sessions until the goal is achieved or marked COMPLETE.

Usage:
    python3 scripts/auto_continue.py "Build auth system"
    python3 scripts/auto_continue.py --max-budget-usd 5.00 "Build auth system"
    python3 scripts/auto_continue.py --dry-run "Build auth system"  # verify CLI without running

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

# Add hooks/ to path for gate imports
sys.path.insert(0, str(Path(__file__).parent.parent / "hooks"))
from gate import get_config_value, load_gate_config  # noqa: E402


class AutoContinue:
    """Manages Claude Code session lifecycle for multi-session tasks."""

    def __init__(
        self,
        goal: Optional[str],
        max_budget: Optional[float],
        project_dir: Path,
        dry_run: bool = False,
        model: Optional[str] = None,
    ):
        self.goal = goal
        self.max_budget = max_budget
        self.project_dir = project_dir
        self.dry_run = dry_run
        self.handoff_file = project_dir / "HANDOFF.md"
        self.history_log = project_dir / "handoff-history.log"
        self.session_count = 0
        # Model: CLI arg > gates.json > "auto"
        config = load_gate_config(project_dir)
        self.model = model or get_config_value(config, "model", "auto")

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
        """Launch a Claude Code session in headless mode. Returns process exit code.

        Uses `claude -p` (print mode) which runs non-interactively.
        --dangerously-skip-permissions allows autonomous file operations.
        --max-budget-usd caps spend per session.
        """
        cmd = [
            "claude", "-p", prompt,
            "--output-format", "json",
            "--dangerously-skip-permissions",
        ]

        if self.model and self.model != "auto":
            cmd.extend(["--model", self.model])

        if self.max_budget:
            cmd.extend(["--max-budget-usd", str(self.max_budget)])

        if self.dry_run:
            print(f"[dry-run] Would execute: {' '.join(cmd)}")
            # Signal completion so the loop stops after one iteration
            if self.handoff_file.is_file():
                content = self.handoff_file.read_text(encoding="utf-8")
                if "## COMPLETE" not in content:
                    self.handoff_file.write_text(
                        content + "\n## COMPLETE\n\nDry run — no session executed.\n",
                        encoding="utf-8",
                    )
            return 0

        result = subprocess.run(cmd, cwd=self.project_dir)
        return result.returncode

    def _is_complete(self) -> bool:
        """Check if the goal is complete.

        Complete if: HANDOFF.md doesn't exist (agent cleaned up)
        or contains ## COMPLETE as a standalone section header (not inside goal text).
        """
        if not self.handoff_file.is_file():
            return True
        content = self.handoff_file.read_text(encoding="utf-8")
        # Match ## COMPLETE only at start of a line (section header)
        return bool(re.search(r"^## COMPLETE\s*$", content, re.MULTILINE))

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
        "--dry-run",
        action="store_true",
        default=False,
        help="Print the claude command that would run without executing it.",
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
    parser.add_argument(
        "--model",
        type=str,
        default=None,
        help="Model to use (overrides gates.json). 'auto' = no override.",
    )
    return parser.parse_args(argv)


def main() -> int:
    """Entry point."""
    args = parse_args()
    runner = AutoContinue(
        goal=args.goal,
        max_budget=args.max_budget_usd,
        project_dir=Path(args.project_dir).resolve(),
        dry_run=args.dry_run,
        model=args.model,
    )
    return runner.run()


if __name__ == "__main__":
    sys.exit(main())
