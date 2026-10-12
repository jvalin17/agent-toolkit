"""Report whether TDD order allows editing source (session-aware when present)."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional


def run(args: Dict[str, Any], toolkit_root: Optional[Path] = None) -> Dict[str, Any]:
    """Return ok/ready based on optional .session tdd markers in project_dir."""
    project = Path(args.get("project_dir") or ".")
    session = project / ".session"
    # If no session state, advise test-first but do not hard-block (CLI hosts)
    if not session.is_dir():
        return {
            "ok": True,
            "ready": True,
            "advisory": "No .session state — write/adjust a failing test before source edits.",
        }

    # Markers written by tdd_enforce when present
    last_test = session / "last_test_edit"
    blocked = session / "tdd_blocked"
    if blocked.is_file():
        return {
            "ok": True,
            "ready": False,
            "missing": ["failing test edit before source"],
            "detail": blocked.read_text(encoding="utf-8")[:500],
        }
    if last_test.is_file():
        return {"ok": True, "ready": True, "last_test_edit": last_test.read_text(encoding="utf-8")[:200]}
    return {
        "ok": True,
        "ready": True,
        "advisory": "Session exists but no TDD markers — prefer test-first.",
    }
