"""Report whether commit gates look ready (stamps / passed flags)."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional


def run(args: Dict[str, Any], toolkit_root: Optional[Path] = None) -> Dict[str, Any]:
    project = Path(args.get("project_dir") or ".")
    skill = args.get("skill") or "precommit"
    gates = project / ".gates"
    missing: List[str] = []

    precommit_flag = gates / "precommit-passed"
    stamp = gates / "stamps" / skill

    if skill == "precommit" and not precommit_flag.is_file():
        missing.append("precommit-passed")
    if not stamp.is_file() and skill != "precommit":
        # For non-precommit, require skill stamp when checking that skill
        missing.append(f"stamps/{skill}")

    # When checking precommit readiness, also note if stamp dir exists
    ready = len(missing) == 0
    return {
        "ok": True,
        "ready": ready,
        "missing": missing,
        "project_dir": str(project.resolve()),
        "hint": "Run /precommit or stamp_skill + finalize_report before commit"
        if not ready
        else "Gate markers present",
    }
