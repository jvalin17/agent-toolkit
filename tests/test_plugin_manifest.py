"""Claude Code plugin manifests: no pinned version, so `claude plugin update`
tracks commits (the computed version becomes the commit SHA).

With `"version": "1.0.0"` in either file, every user stays on the cached copy
until the string changes, however many commits land on main. See
https://code.claude.com/docs/en/plugins/loading#versions-and-updates
"""

import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / ".claude-plugin" / "plugin.json"
MARKETPLACE = ROOT / ".claude-plugin" / "marketplace.json"


@pytest.fixture(scope="module")
def plugin() -> dict:
    return json.loads(PLUGIN.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def marketplace_entry() -> dict:
    data = json.loads(MARKETPLACE.read_text(encoding="utf-8"))
    entries = [p for p in data["plugins"] if p["name"] == "agent-toolkit"]
    assert len(entries) == 1
    return entries[0]


def test_plugin_manifest_has_no_pinned_version(plugin):
    assert "version" not in plugin, "a pinned version freezes plugin updates until it is bumped"


def test_marketplace_entry_has_no_pinned_version(marketplace_entry):
    assert "version" not in marketplace_entry, "a pinned version freezes plugin updates until it is bumped"


def test_manifests_still_describe_the_same_plugin(plugin, marketplace_entry):
    assert plugin["name"] == "agent-toolkit"
    assert marketplace_entry["source"] == "./"
    assert plugin["repository"] == "https://github.com/jvalin17/agent-toolkit"
