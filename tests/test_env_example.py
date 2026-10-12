"""`.env.example` must name every AGENT_TOOLKIT_* variable the code reads."""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ENV_EXAMPLE = ROOT / ".env.example"

# Python: os.environ.get("X") / os.getenv("X") / os.environ["X"]; shell: ${X} / $X
PY_ENV_RE = re.compile(r"""(?:os\.environ(?:\.get)?\(|os\.getenv\(|os\.environ\[)\s*["'](AGENT_TOOLKIT_[A-Z_]+)["']""")
SH_ENV_RE = re.compile(r"\$\{?(AGENT_TOOLKIT_[A-Z_]+)")
SCAN_DIRS = ("hooks", "gate", "scripts", "functions", "toolkit_mcp")
SCAN_FILES = ("install.sh", "update.sh", "setup.sh")


def _referenced_variables() -> set[str]:
    found: set[str] = set()
    for sub in SCAN_DIRS:
        for path in (ROOT / sub).rglob("*"):
            if path.suffix == ".py":
                found.update(PY_ENV_RE.findall(path.read_text(encoding="utf-8", errors="replace")))
            elif path.suffix == ".sh":
                found.update(SH_ENV_RE.findall(path.read_text(encoding="utf-8", errors="replace")))
    for name in SCAN_FILES:
        path = ROOT / name
        if path.is_file():
            found.update(SH_ENV_RE.findall(path.read_text(encoding="utf-8", errors="replace")))
    return found


def _documented_variables() -> set[str]:
    names: set[str] = set()
    for line in ENV_EXAMPLE.read_text(encoding="utf-8").splitlines():
        match = re.match(r"^([A-Z][A-Z0-9_]+)=", line)
        if match:
            names.add(match.group(1))
    return names


def test_env_example_exists():
    assert ENV_EXAMPLE.is_file()


def test_env_example_covers_all_variables():
    referenced = _referenced_variables()
    assert referenced, "scanner found no AGENT_TOOLKIT_* references — regex broken?"
    missing = sorted(referenced - _documented_variables())
    assert missing == [], f"undocumented in .env.example: {missing}"


def test_env_example_has_no_secret_values():
    for line in ENV_EXAMPLE.read_text(encoding="utf-8").splitlines():
        match = re.match(r"^([A-Z0-9_]+)=(.*)$", line)
        if match and ("SECRET" in match.group(1) or "KEY" in match.group(1)):
            value = match.group(2).strip()
            assert value == "" or value.startswith("."), f"{match.group(1)} must not ship a value"
