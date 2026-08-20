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
