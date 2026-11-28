"""The CI workflow sets up the gate for the project under test, from the trusted copy of the toolkit.

Covers: the order of the two folders handed to bootstrap-project-gates.sh. Swapped, a pull
request run sets up the signing key for the trusted copy instead of the project, and the token
step then finds no key.
"""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "agent-toolkit-gate.yml"
BOOTSTRAP = ROOT / "scripts" / "bootstrap-project-gates.sh"
TRUSTED_SOURCE = "${{ steps.gate.outputs.src }}"
PROJECT_UNDER_TEST = "$(pwd)"


def _bootstrap_arguments() -> list:
    line = next(line for line in WORKFLOW.read_text().splitlines() if "bootstrap-project-gates.sh" in line)
    return re.findall(r'"([^"]*)"', line.split("run:", 1)[1])[1:]


def test_bootstrap_script_takes_the_toolkit_first_and_the_project_second():
    script = BOOTSTRAP.read_text()

    assert 'TOOLKIT_DIR="${1:-}"' in script
    assert 'PROJECT_ROOT="${2:-}"' in script


def test_workflow_hands_bootstrap_the_trusted_toolkit_then_the_project():
    assert _bootstrap_arguments() == [TRUSTED_SOURCE, PROJECT_UNDER_TEST]
