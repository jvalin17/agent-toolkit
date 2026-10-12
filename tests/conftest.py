"""Shared pytest setup.

Gate flags are HMAC-signed with a key that normally lives in ~/.agent-toolkit.
Point every test at a throwaway key so the suite never touches, creates or
depends on the developer's real key.
"""

import pytest


@pytest.fixture(autouse=True)
def _isolated_flag_key(tmp_path_factory, monkeypatch):
    key_dir = tmp_path_factory.mktemp("flag-key")
    monkeypatch.setenv("AGENT_TOOLKIT_FLAG_KEY_FILE", str(key_dir / "flag.key"))
    yield
