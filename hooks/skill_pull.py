"""Pull skill stubs, modules, and run allowlisted gate functions."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

TOOLKIT_ROOT = Path(__file__).resolve().parents[1]
SKILLS_DIR = TOOLKIT_ROOT / "skills"
FUNCTIONS_DIR = TOOLKIT_ROOT / "functions"

# Allowlisted function module names under functions/
FUNCTION_REGISTRY = {
    "check_tdd_order": "check_tdd_order",
    "gate_status": "gate_status",
}


def _skills_dir(toolkit_root: Path) -> Path:
    return toolkit_root / "skills"


def _safe_under(root: Path, candidate: Path) -> bool:
    try:
        candidate.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def list_modules(skill: str, toolkit_root: Optional[Path] = None) -> List[str]:
    root = toolkit_root or TOOLKIT_ROOT
    modules_dir = _skills_dir(root) / skill / "modules"
    if not modules_dir.is_dir():
        return []
    return sorted(p.stem for p in modules_dir.glob("*.md"))


def get_skill(skill: str, toolkit_root: Optional[Path] = None) -> Dict[str, Any]:
    root = toolkit_root or TOOLKIT_ROOT
    skill_dir = _skills_dir(root) / skill
    skill_md = skill_dir / "SKILL.md"
    if not skill_md.is_file():
        return {"error": f"Unknown skill: {skill}"}
    if not _safe_under(_skills_dir(root), skill_md):
        return {"error": "Path escape blocked"}
    stub = skill_md.read_text(encoding="utf-8")
    return {
        "name": skill,
        "stub": stub,
        "modules": list_modules(skill, toolkit_root=root),
    }


def get_module(
    skill: str,
    module: str,
    toolkit_root: Optional[Path] = None,
) -> Dict[str, Any]:
    root = toolkit_root or TOOLKIT_ROOT
    if not module or "/" in module or "\\" in module or ".." in module:
        return {"error": "Invalid module name"}
    path = _skills_dir(root) / skill / "modules" / f"{module}.md"
    if not _safe_under(_skills_dir(root), path):
        return {"error": "Path escape blocked"}
    if not path.is_file():
        return {"error": f"Module not found: {skill}/{module}"}
    return {
        "skill": skill,
        "module": module,
        "content": path.read_text(encoding="utf-8"),
    }


def _load_function(name: str, toolkit_root: Path):
    mod_name = FUNCTION_REGISTRY.get(name)
    if not mod_name:
        return None
    path = toolkit_root / "functions" / f"{mod_name}.py"
    if not path.is_file():
        return None
    spec = importlib.util.spec_from_file_location(f"toolkit_fn_{mod_name}", path)
    if spec is None or spec.loader is None:
        return None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def run_function(
    name: str,
    args: Optional[Dict[str, Any]] = None,
    toolkit_root: Optional[Path] = None,
) -> Dict[str, Any]:
    root = toolkit_root or TOOLKIT_ROOT
    args = args or {}
    if name not in FUNCTION_REGISTRY:
        return {"ok": False, "error": f"Unknown function: {name}"}
    module = _load_function(name, root)
    if module is None or not hasattr(module, "run"):
        return {"ok": False, "error": f"Function not loadable: {name}"}
    try:
        result = module.run(args, toolkit_root=root)
        if not isinstance(result, dict):
            return {"ok": False, "error": "Function must return dict"}
        return result
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


def stamp_skill(
    name: str,
    project_dir: Path,
) -> Dict[str, Any]:
    """Write CLI skill stamp under project .gates/stamps/<name>."""
    project_dir = Path(project_dir)
    stamps = project_dir / ".gates" / "stamps"
    stamps.mkdir(parents=True, exist_ok=True)
    stamp_path = stamps / name
    stamp_path.write_text("cli_stamp\n", encoding="utf-8")
    return {"ok": True, "path": str(stamp_path)}
