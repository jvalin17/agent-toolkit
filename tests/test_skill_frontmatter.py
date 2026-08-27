#!/usr/bin/env python3
"""Regression test: all skills must have disable-model-invocation: false.

Setting it to true prevents the Skill tool from invoking the skill,
which breaks /debug_tool and any other skill that gets flipped.
"""

from pathlib import Path

import pytest

SKILLS_DIR = Path(__file__).resolve().parents[1] / "skills"


def get_all_skill_files():
    """Return all SKILL.md files in the skills directory."""
    return sorted(SKILLS_DIR.glob("*/SKILL.md"))


@pytest.mark.parametrize(
    "skill_file",
    get_all_skill_files(),
    ids=lambda p: p.parent.name,
)
def test_disable_model_invocation_is_false(skill_file):
    """Every skill must have disable-model-invocation: false so the Skill tool works."""
    content = skill_file.read_text()
    assert "disable-model-invocation: false" in content, (
        f"{skill_file.parent.name}/SKILL.md has disable-model-invocation != false. "
        f"This will cause 'Error: Skill {skill_file.parent.name} cannot be used "
        f"with Skill tool due to disable-model-invocation'."
    )
