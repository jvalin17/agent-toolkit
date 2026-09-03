#!/usr/bin/env python3
"""Cross-role orchestration — deterministic role invocation and model routing.

Reads `invokes:` and `cost_guidance:` from role.md files to build
orchestration plans. The LLM follows the plan — it doesn't decide the plan.

Usage:
  from orchestrator import build_orchestration_plan, plan_to_context

  plan = build_orchestration_plan(
      primary_role="backend",
      task_type="new_feature",
      active_roles=["backend", "dba", "security", "qa"],
      roles_dir=roles_dir,
  )
  context = plan_to_context(plan)
  # → inject context into skill workflow
"""

import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional


ROLES_DIR = Path(__file__).resolve().parent

# Import taxonomy for model selection
try:
    from agent_taxonomy import select_agent, MODEL_IDS
except ImportError:
    select_agent = None  # type: ignore
    MODEL_IDS = {"haiku": "haiku", "sonnet": "sonnet", "opus": "opus", "fable": "fable"}

MODEL_MAP = {
    "cheap": "haiku",
    "mid": "sonnet",
    "expensive": "opus",
}


def _parse_frontmatter(role_path: Path) -> Dict[str, Any]:
    """Parse YAML-like frontmatter from role.md. Simple key: value parser."""
    if not role_path.is_file():
        return {}

    content = role_path.read_text()
    if not content.startswith("---"):
        return {}

    parts = content.split("---", 2)
    if len(parts) < 3:
        return {}

    frontmatter = parts[1].strip()
    result: Dict[str, Any] = {}
    current_key = None
    current_dict: Optional[Dict[str, Any]] = None

    for line in frontmatter.split("\n"):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue

        # Top-level key: value
        if not line.startswith(" ") and not line.startswith("\t") and ":" in stripped:
            key, _, value = stripped.partition(":")
            key = key.strip()
            value = value.strip()

            if value:
                # Try to parse as JSON (for lists like ["a", "b"])
                try:
                    result[key] = json.loads(value)
                except (json.JSONDecodeError, ValueError):
                    result[key] = value
                current_key = None
                current_dict = None
            else:
                # Start of a nested dict
                current_key = key
                current_dict = {}
                result[key] = current_dict

        elif current_dict is not None and (":" in stripped):
            # Nested key: value
            key, _, value = stripped.partition(":")
            key = key.strip()
            value = value.strip()
            if key.startswith("- "):
                # It's a list item, not a dict entry
                if current_key and current_key in result and not isinstance(result[current_key], dict):
                    pass
            else:
                try:
                    current_dict[key] = json.loads(value)
                except (json.JSONDecodeError, ValueError):
                    current_dict[key] = value

    return result


def get_invocations(
    role_name: str,
    phase: str,
    roles_dir: Optional[Path] = None,
) -> List[str]:
    """Get which roles to invoke at a given phase for a primary role.

    Args:
        role_name: Primary role (e.g., "backend")
        phase: Invocation phase (e.g., "after_skeleton", "for_evaluation")
        roles_dir: Path to roles/ directory

    Returns:
        List of role names to invoke, or empty list.
    """
    if roles_dir is None:
        roles_dir = ROLES_DIR

    role_md = roles_dir / role_name / "role.md"
    config = _parse_frontmatter(role_md)
    invokes = config.get("invokes", {})

    if not isinstance(invokes, dict):
        return []

    result = invokes.get(phase, [])
    if isinstance(result, str):
        return [result]
    if isinstance(result, list):
        return result
    return []


def get_model_tier(
    role_name: str,
    task_type: str,
    roles_dir: Optional[Path] = None,
) -> str:
    """Get recommended model tier for a task type within a role.

    Returns: "cheap", "mid", or "expensive"
    """
    if roles_dir is None:
        roles_dir = ROLES_DIR

    role_md = roles_dir / role_name / "role.md"
    config = _parse_frontmatter(role_md)
    cost = config.get("cost_guidance", {})

    if not isinstance(cost, dict):
        return "mid"

    for tier in ["cheap", "mid", "expensive"]:
        tasks = cost.get(tier, [])
        if isinstance(tasks, list) and task_type in tasks:
            return tier

    return "mid"  # default


def _extract_role_checklist(
    role_name: str,
    roles_dir: Optional[Path] = None,
) -> Dict[str, List[str]]:
    """Extract anti-patterns and quality checks from a role's markdown.

    Returns:
        {"anti_patterns": ["...", ...], "quality_checks": ["...", ...]}
    """
    if roles_dir is None:
        roles_dir = ROLES_DIR

    role_md = roles_dir / role_name / "role.md"
    if not role_md.is_file():
        return {"anti_patterns": [], "quality_checks": []}

    content = role_md.read_text()
    # Strip frontmatter
    if content.startswith("---"):
        parts = content.split("---", 2)
        if len(parts) >= 3:
            content = parts[2]

    anti_patterns: List[str] = []
    quality_checks: List[str] = []

    current_section = None
    for line in content.split("\n"):
        stripped = line.strip()

        # Detect section headers
        if re.match(r"^##\s+Anti-Patterns", stripped, re.IGNORECASE):
            current_section = "anti_patterns"
            continue
        elif re.match(r"^##\s+Quality Checks", stripped, re.IGNORECASE):
            current_section = "quality_checks"
            continue
        elif re.match(r"^##\s+", stripped):
            current_section = None
            continue

        # Collect list items
        if current_section and stripped.startswith("- "):
            item = stripped[2:].strip()
            # Strip checkbox prefix
            if item.startswith("[ ] "):
                item = item[4:]
            elif item.startswith("[x] "):
                item = item[4:]
            if item:
                if current_section == "anti_patterns":
                    anti_patterns.append(item)
                else:
                    quality_checks.append(item)

    return {"anti_patterns": anti_patterns, "quality_checks": quality_checks}


def build_orchestration_plan(
    primary_role: str,
    task_type: str,
    active_roles: List[str],
    roles_dir: Optional[Path] = None,
) -> Dict[str, Any]:
    """Build a deterministic orchestration plan for a task.

    The plan defines what happens in what order. The LLM follows it.

    Args:
        primary_role: Role doing the main work (e.g., "backend")
        task_type: "new_feature", "bug_fix", "refactor", "migration"
        active_roles: All currently active roles
        roles_dir: Path to roles/ directory

    Returns:
        Plan dict with ordered steps.
    """
    if roles_dir is None:
        roles_dir = ROLES_DIR

    active_set = set(active_roles)
    steps = []

    if task_type == "new_feature":
        # Step 1: Primary role builds
        steps.append({
            "type": "build",
            "role": primary_role,
            "description": f"{primary_role} builds skeleton using learned knowledge",
            "model_tier": get_model_tier(primary_role, "code-generation", roles_dir),
        })

        # Step 2: Post-skeleton evaluation
        after_skeleton = get_invocations(primary_role, "after_skeleton", roles_dir)
        active_evaluators = [r for r in after_skeleton if r in active_set]
        if active_evaluators:
            steps.append({
                "type": "evaluate",
                "roles": active_evaluators,
                "description": f"Post-skeleton review by {', '.join(active_evaluators)}",
                "model_tier": "cheap",
                "parallel": True,
            })

            # Step 3: Primary applies feedback
            steps.append({
                "type": "apply_feedback",
                "role": primary_role,
                "description": f"{primary_role} applies evaluation feedback",
                "model_tier": get_model_tier(primary_role, "code-generation", roles_dir),
            })

        # Step 4: Final evaluation
        for_eval = get_invocations(primary_role, "for_evaluation", roles_dir)
        active_final = [r for r in for_eval if r in active_set]
        if active_final:
            steps.append({
                "type": "evaluate",
                "roles": active_final,
                "description": f"Final evaluation by {', '.join(active_final)}",
                "model_tier": "cheap",
                "parallel": True,
            })

    elif task_type == "bug_fix":
        # Step 1: Primary diagnoses and fixes
        steps.append({
            "type": "fix",
            "role": primary_role,
            "description": f"{primary_role} diagnoses and fixes using learned patterns",
            "model_tier": get_model_tier(primary_role, "bug-fix", roles_dir),
        })

        # Step 2: Evaluation to verify fix doesn't introduce issues
        for_eval = get_invocations(primary_role, "for_evaluation", roles_dir)
        active_eval = [r for r in for_eval if r in active_set]
        if active_eval:
            steps.append({
                "type": "evaluate",
                "roles": active_eval,
                "description": f"Verify fix with {', '.join(active_eval)}",
                "model_tier": "cheap",
                "parallel": True,
            })

    elif task_type == "refactor":
        # Step 1: Snapshot current behavior
        steps.append({
            "type": "snapshot",
            "role": primary_role,
            "description": "Snapshot current behavior (run all tests, capture outputs)",
            "model_tier": "cheap",
        })

        # Step 2: Refactor
        steps.append({
            "type": "refactor",
            "role": primary_role,
            "description": f"{primary_role} refactors in small steps",
            "model_tier": get_model_tier(primary_role, "code-generation", roles_dir),
        })

        # Step 3: Verify behavior unchanged
        steps.append({
            "type": "verify",
            "role": primary_role,
            "description": "Verify behavior unchanged (same tests pass, same outputs)",
            "model_tier": "cheap",
        })

        # Step 4: Code health review
        if "code-health" in active_set:
            steps.append({
                "type": "evaluate",
                "roles": ["code-health"],
                "description": "Code Health Engineer reviews refactor quality",
                "model_tier": "cheap",
                "parallel": False,
            })

    elif task_type == "migration":
        # Step 1: Primary proposes approach
        steps.append({
            "type": "plan",
            "role": primary_role,
            "description": f"{primary_role} proposes migration approach",
            "model_tier": "expensive",
        })

        # Step 2: ALL active roles evaluate the approach
        other_roles = [r for r in active_roles if r != primary_role]
        if other_roles:
            steps.append({
                "type": "evaluate",
                "roles": other_roles,
                "description": f"All roles evaluate migration approach: {', '.join(other_roles)}",
                "model_tier": "mid",
                "parallel": True,
            })

        # Step 3: Implement
        steps.append({
            "type": "build",
            "role": primary_role,
            "description": f"{primary_role} implements migration",
            "model_tier": get_model_tier(primary_role, "code-generation", roles_dir),
        })

        # Step 4: Full evaluation
        for_eval = get_invocations(primary_role, "for_evaluation", roles_dir)
        active_final = [r for r in for_eval if r in active_set]
        if active_final:
            steps.append({
                "type": "evaluate",
                "roles": active_final,
                "description": f"Post-migration evaluation by {', '.join(active_final)}",
                "model_tier": "cheap",
                "parallel": True,
            })

    else:
        # Generic: just build + evaluate
        steps.append({
            "type": "build",
            "role": primary_role,
            "description": f"{primary_role} implements task",
            "model_tier": "mid",
        })

        for_eval = get_invocations(primary_role, "for_evaluation", roles_dir)
        active_eval = [r for r in for_eval if r in active_set]
        if active_eval:
            steps.append({
                "type": "evaluate",
                "roles": active_eval,
                "description": f"Evaluation by {', '.join(active_eval)}",
                "model_tier": "cheap",
                "parallel": True,
            })

    return {
        "primary": primary_role,
        "task_type": task_type,
        "active_roles": active_roles,
        "steps": steps,
    }


def plan_to_context(
    plan: Dict[str, Any],
    roles_dir: Optional[Path] = None,
) -> str:
    """Convert an orchestration plan to injectable context text.

    This text gets injected into the skill workflow so the LLM
    follows the plan deterministically. Build steps include the
    role's anti-patterns and quality checks as a mandatory pre-flight.
    """
    lines = [
        f"ORCHESTRATION PLAN ({plan['task_type']})",
        f"Primary role: {plan['primary']}",
        f"Active roles: {', '.join(plan['active_roles'])}",
        "",
    ]

    # Pre-load checklists for roles that have build steps
    checklists: Dict[str, Dict[str, List[str]]] = {}
    build_step_types = {"build", "fix", "refactor"}

    for step in plan["steps"]:
        if step.get("type") in build_step_types:
            role = step.get("role", plan["primary"])
            if role not in checklists:
                checklists[role] = _extract_role_checklist(role, roles_dir)

    for i, step in enumerate(plan["steps"], 1):
        model = MODEL_MAP.get(step.get("model_tier", "mid"), step.get("model_tier", "sonnet"))
        is_parallel = step.get("parallel", False)

        if "roles" in step:
            roles_str = ", ".join(step["roles"])
            lines.append(f"Step {i}: [{step['type'].upper()}] {step['description']}")
            lines.append(f"  Roles: {roles_str}")
            lines.append(f"  Model: {model}")

            if is_parallel and len(step["roles"]) > 1:
                lines.append(f"  Execution: PARALLEL — spawn {len(step['roles'])} Agent subagents simultaneously:")
                for role in step["roles"]:
                    lines.append(f"    → Agent(model={model}): \"Review as {role} role. Check {role} quality checks against the code. Return structured findings.\"")
                lines.append(f"  Wait for ALL agents to complete before proceeding to Step {i + 1}.")
            else:
                lines.append(f"  Execution: sequential")
        else:
            step_role = step.get("role", plan["primary"])
            lines.append(f"Step {i}: [{step['type'].upper()}] {step['description']}")
            lines.append(f"  Role: {step_role}")
            lines.append(f"  Model: {model}")

            # Inject role checklist for build/fix/refactor steps
            if step.get("type") in build_step_types and step_role in checklists:
                cl = checklists[step_role]
                if cl["anti_patterns"] or cl["quality_checks"]:
                    lines.append(f"  PRE-FLIGHT CHECKLIST ({step_role}):")
                    if cl["anti_patterns"]:
                        lines.append(f"    MUST NOT (anti-patterns — if your code matches any, redesign):")
                        for ap in cl["anti_patterns"]:
                            lines.append(f"      ✗ {ap}")
                    if cl["quality_checks"]:
                        lines.append(f"    MUST (quality checks — verify each before moving on):")
                        for qc in cl["quality_checks"]:
                            lines.append(f"      ✓ {qc}")

        lines.append("")

    lines.append("Follow these steps in order. Do not skip steps or change the sequence.")
    lines.append("For PARALLEL steps: use the Agent tool to spawn multiple subagents in a single message.")
    lines.append("")
    lines.append("Model guide: haiku=mechanical/cheap, sonnet=implementation/mid, opus/fable=reasoning/expensive.")
    lines.append("Use the cheapest model that can handle the task. Fetch/lint/search → haiku. Code/review → sonnet. Architecture/security → opus/fable.")

    return "\n".join(lines)
