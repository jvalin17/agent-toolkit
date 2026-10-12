#!/usr/bin/env python3
"""MCP server for agent-toolkit — zero dependencies, JSON-RPC over stdio.

Implements the MCP protocol (JSON-RPC 2.0 over stdin/stdout) with no
external packages. Works on any Python 3.9+.

Usage:
    python3 -m toolkit_mcp
"""

import json
import sys
from pathlib import Path

TOOLKIT_ROOT = Path(__file__).resolve().parent.parent
ROLES_DIR = TOOLKIT_ROOT / "roles"
SKILLS_DIR = TOOLKIT_ROOT / "skills"
AGENTS_DIR = TOOLKIT_ROOT / "agents"
sys.path.insert(0, str(ROLES_DIR))

SERVER_INFO = {
    "name": "agent-toolkit",
    "version": "1.0.0",
}

# --- Tool implementations (pure functions, no deps) ---

TOOLS = {}


def tool(name, description, schema):
    """Register a tool with its JSON schema."""
    def decorator(fn):
        TOOLS[name] = {"fn": fn, "description": description, "inputSchema": schema}
        return fn
    return decorator


def _parse_frontmatter_field(content, field):
    """Extract a field value from markdown frontmatter."""
    if not content.startswith("---"):
        return ""
    parts = content.split("---", 2)
    if len(parts) < 3:
        return ""
    for line in parts[1].split("\n"):
        if line.strip().startswith(f"{field}:"):
            return line.split(":", 1)[1].strip().strip('"')
    return ""


@tool("select_agent", "Select the best model for a task type (haiku/sonnet/opus)", {
    "type": "object",
    "properties": {
        "task_type": {"type": "string", "description": "Task type: fetch, file_search, code_generation, architecture_decision, etc."},
        "available": {"type": "array", "items": {"type": "string"}, "description": "Available model names (optional)"},
    },
    "required": ["task_type"],
})
def tool_select_agent(params):
    from agent_taxonomy import select_agent
    return select_agent(params["task_type"], available=params.get("available"))


@tool("build_plan", "Build a deterministic orchestration plan for a task", {
    "type": "object",
    "properties": {
        "primary_role": {"type": "string", "description": "Role doing the main work (e.g., backend)"},
        "task_type": {"type": "string", "description": "One of: new_feature, bug_fix, refactor, migration"},
        "active_roles": {"type": "array", "items": {"type": "string"}, "description": "All active roles"},
    },
    "required": ["primary_role", "task_type", "active_roles"],
})
def tool_build_plan(params):
    from orchestrator import build_orchestration_plan
    return build_orchestration_plan(
        primary_role=params["primary_role"],
        task_type=params["task_type"],
        active_roles=params["active_roles"],
        roles_dir=ROLES_DIR,
    )


@tool("plan_to_text", "Render an orchestration plan as injectable context text", {
    "type": "object",
    "properties": {
        "plan": {"type": "object", "description": "Plan dict from build_plan"},
    },
    "required": ["plan"],
})
def tool_plan_to_text(params):
    from orchestrator import plan_to_context
    return plan_to_context(params["plan"], roles_dir=ROLES_DIR)


@tool("get_role_context", "Detect roles for a project and generate context text", {
    "type": "object",
    "properties": {
        "project_dir": {"type": "string", "description": "Path to the project directory"},
        "roles": {"type": "array", "items": {"type": "string"}, "description": "Override: specific role names"},
        "max_roles": {"type": "integer", "description": "Max roles to include (default 4)"},
    },
    "required": ["project_dir"],
})
def tool_get_role_context(params):
    from context import get_context_json
    project_path = Path(params["project_dir"])
    if not project_path.is_dir():
        return {"error": f"Directory not found: {params['project_dir']}"}
    result = get_context_json(
        project_dir=project_path,
        roles_dir=ROLES_DIR,
        config_roles=params.get("roles"),
        max_roles=params.get("max_roles", 4),
    )
    return json.loads(result) if isinstance(result, str) else result


@tool("list_roles", "List all 19 available roles with descriptions", {
    "type": "object", "properties": {},
})
def tool_list_roles(_params):
    roles = []
    for role_dir in sorted(ROLES_DIR.iterdir()):
        role_md = role_dir / "role.md"
        if role_md.is_file():
            roles.append({
                "name": role_dir.name,
                "description": _parse_frontmatter_field(role_md.read_text(), "description"),
            })
    return roles


@tool("list_skills", "List all available skills with descriptions", {
    "type": "object", "properties": {},
})
def tool_list_skills(_params):
    skills = []
    for skill_dir in sorted(SKILLS_DIR.iterdir()):
        skill_md = skill_dir / "SKILL.md"
        if skill_md.is_file():
            skills.append({
                "name": skill_dir.name,
                "description": _parse_frontmatter_field(skill_md.read_text(), "description"),
            })
    return skills


@tool("list_agents", "List all available sub-agents with descriptions", {
    "type": "object", "properties": {},
})
def tool_list_agents(_params):
    agents = []
    for agent_file in sorted(AGENTS_DIR.glob("*.md")):
        agents.append({
            "name": agent_file.stem,
            "description": _parse_frontmatter_field(agent_file.read_text(), "description"),
        })
    return agents


@tool("build_research_plan", "Build a fan-out research plan: cheap fetchers + expensive synthesizer", {
    "type": "object",
    "properties": {
        "query": {"type": "string", "description": "What to research"},
        "search_count": {"type": "integer", "description": "Number of parallel searches (default 5)"},
    },
    "required": ["query"],
})
def tool_build_research_plan(params):
    from agent_taxonomy import build_research_plan
    return build_research_plan(query=params["query"], search_count=params.get("search_count", 5))


def _hooks_path():
    hooks = TOOLKIT_ROOT / "hooks"
    if str(hooks) not in sys.path:
        sys.path.insert(0, str(hooks))


@tool("resolve_host", "Detect LLM host and return merged host configuration", {
    "type": "object",
    "properties": {
        "stdin_payload": {"type": "object", "description": "Optional hook stdin JSON for detection"},
    },
})
def tool_resolve_host(params):
    _hooks_path()
    from host_config import resolve_host
    return resolve_host(params.get("stdin_payload"))


@tool("get_bootstrap", "Render short bootstrap text for the detected (or given) host", {
    "type": "object",
    "properties": {
        "host_id": {"type": "string", "description": "Optional host id; default = detect"},
    },
})
def tool_get_bootstrap(params):
    _hooks_path()
    from host_config import load_host_config, resolve_host, render_bootstrap
    host_id = params.get("host_id")
    cfg = load_host_config(host_id) if host_id else resolve_host()
    return {"host": cfg.get("id"), "text": render_bootstrap(cfg, toolkit_root=TOOLKIT_ROOT)}


@tool("get_skill", "Get skill stub + module catalog (not full long body modules)", {
    "type": "object",
    "properties": {
        "name": {"type": "string", "description": "Skill directory name"},
    },
    "required": ["name"],
})
def tool_get_skill(params):
    _hooks_path()
    from skill_pull import get_skill
    return get_skill(params["name"], toolkit_root=TOOLKIT_ROOT)


@tool("get_module", "Fetch one skill module markdown by name", {
    "type": "object",
    "properties": {
        "skill": {"type": "string"},
        "module": {"type": "string"},
    },
    "required": ["skill", "module"],
})
def tool_get_module(params):
    _hooks_path()
    from skill_pull import get_module
    return get_module(params["skill"], params["module"], toolkit_root=TOOLKIT_ROOT)


@tool("get_role", "Load role context at compact|checks|full depth", {
    "type": "object",
    "properties": {
        "name": {"type": "string"},
        "depth": {"type": "string", "description": "compact, checks, or full"},
    },
    "required": ["name"],
})
def tool_get_role(params):
    from detect_role import load_role_context
    depth = params.get("depth") or "compact"
    # "checks" = compact role body (anti-patterns + quality checks in role.md)
    load_depth = "compact" if depth in ("compact", "checks") else "full"
    text = load_role_context([params["name"]], roles_dir=ROLES_DIR, max_roles=1, depth=load_depth)
    return {"name": params["name"], "depth": depth, "text": text}


@tool("run_function", "Run an allowlisted gate function (check_tdd_order, gate_status)", {
    "type": "object",
    "properties": {
        "name": {"type": "string"},
        "args": {"type": "object"},
    },
    "required": ["name"],
})
def tool_run_function(params):
    _hooks_path()
    from skill_pull import run_function
    return run_function(params["name"], params.get("args") or {}, toolkit_root=TOOLKIT_ROOT)


@tool("stamp_skill", "Write CLI skill stamp under project .gates/stamps/", {
    "type": "object",
    "properties": {
        "name": {"type": "string"},
        "project_dir": {"type": "string"},
    },
    "required": ["name", "project_dir"],
})
def tool_stamp_skill(params):
    _hooks_path()
    from skill_pull import stamp_skill
    return stamp_skill(params["name"], Path(params["project_dir"]))


# --- MCP JSON-RPC protocol handler ---

def handle_initialize(_params):
    return {
        "protocolVersion": "2024-11-05",
        "capabilities": {"tools": {}},
        "serverInfo": SERVER_INFO,
    }


def handle_tools_list(_params):
    return {
        "tools": [
            {"name": name, "description": t["description"], "inputSchema": t["inputSchema"]}
            for name, t in TOOLS.items()
        ]
    }


def handle_tools_call(params):
    name = params.get("name", "")
    if name not in TOOLS:
        return {"content": [{"type": "text", "text": json.dumps({"error": f"Unknown tool: {name}"})}], "isError": True}
    try:
        result = TOOLS[name]["fn"](params.get("arguments", {}))
        text = json.dumps(result, default=str) if not isinstance(result, str) else result
        return {"content": [{"type": "text", "text": text}]}
    except Exception as e:
        return {"content": [{"type": "text", "text": json.dumps({"error": str(e)})}], "isError": True}


HANDLERS = {
    "initialize": handle_initialize,
    "initialized": lambda _: None,  # notification, no response
    "tools/list": handle_tools_list,
    "tools/call": handle_tools_call,
}


def process_message(msg):
    """Process a JSON-RPC message. Returns response dict or None for notifications."""
    method = msg.get("method", "")
    params = msg.get("params", {})
    msg_id = msg.get("id")

    handler = HANDLERS.get(method)
    if handler is None:
        if msg_id is not None:
            return {"jsonrpc": "2.0", "id": msg_id, "error": {"code": -32601, "message": f"Method not found: {method}"}}
        return None

    result = handler(params)
    if result is None:  # notification
        return None
    return {"jsonrpc": "2.0", "id": msg_id, "result": result}


def run():
    """Run the MCP server over stdio."""
    while True:
        line = sys.stdin.readline()
        if not line:
            break
        line = line.strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
            response = process_message(msg)
            if response is not None:
                sys.stdout.write(json.dumps(response) + "\n")
                sys.stdout.flush()
        except json.JSONDecodeError:
            err = {"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": "Parse error"}}
            sys.stdout.write(json.dumps(err) + "\n")
            sys.stdout.flush()


if __name__ == "__main__":
    run()
