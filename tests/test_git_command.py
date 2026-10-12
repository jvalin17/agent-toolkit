"""hooks/git_command.py — find git commit/push anywhere in a shell command line.

The previous regex only matched a segment that *started* with `git`, so any
wrapper (bash -c, env prefix, absolute path, newline) slipped past the gate.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "hooks"))

from git_command import detect_git_actions


class TestWrappers:
    @pytest.mark.parametrize("command", [
        'bash -c "git commit -m \'add invoice export\'"',
        "sh -c 'git push origin main'",
        'eval "git commit -m x"',
        "bash -lc 'cd app && git commit -am wip'",
        "nohup git push origin feature/invoices &",
        "xargs -0 git commit -m x",
        "command git commit -m x",
        "exec git push",
    ])
    def test_detects_git_inside_shell_wrappers(self, command):
        assert detect_git_actions(command) != set()

    @pytest.mark.parametrize("command, expected", [
        ("FOO=1 git commit -m x", {"commit"}),
        ("GIT_AUTHOR_NAME=ana GIT_AUTHOR_EMAIL=ana@acme.dev git commit -m x", {"commit"}),
        ("env GIT_TRACE=1 git push", {"push"}),
        ("/usr/bin/git commit -m x", {"commit"}),
        ("/opt/homebrew/bin/git push --force-with-lease", {"push"}),
        ("git -C /home/ana/app commit -m x", {"commit"}),
        ("git -c core.hooksPath=/dev/null commit -m x", {"commit"}),
        ("git --git-dir=.git --work-tree=. push", {"push"}),
    ])
    def test_detects_env_prefix_and_absolute_path(self, command, expected):
        assert detect_git_actions(command) == expected

    @pytest.mark.parametrize("command, expected", [
        ("printf hi\ngit commit -m x", {"commit"}),
        ("ls; git commit -m x", {"commit"}),
        ("pytest -q && git commit -m x && git push", {"commit", "push"}),
        ("make test || git commit -m x", {"commit"}),
        ("cat notes.txt | git commit -F -", {"commit"}),
        ("(git push)", {"push"}),
        ("{ git push; }", {"push"}),
        ("git add -A &\ngit commit -m x", {"commit"}),
    ])
    def test_detects_after_separators(self, command, expected):
        assert detect_git_actions(command) == expected

    def test_detects_inside_command_substitution(self):
        assert detect_git_actions('echo "$(git commit -m x)"') == {"commit"}
        assert detect_git_actions("echo `git push`") == {"push"}


class TestNoFalsePositives:
    @pytest.mark.parametrize("command", [
        "git log --oneline -5",
        "git diff HEAD~1",
        "git status",
        "git commit --help",
        "git show HEAD:gates.json",
        'echo "remember to git commit later"',
        "grep -rn 'git push' docs/",
        "python3 -m pytest tests/test_gate_hook.py -k commit",
        "git push --dry-run",
        "ls -la",
        "",
    ])
    def test_read_only_git_not_gated(self, command):
        assert detect_git_actions(command) == set()

    def test_commit_message_mentioning_push_is_commit_only(self):
        assert detect_git_actions('git commit -m "ready to git push"') == {"commit"}

    def test_unicode_message(self):
        assert detect_git_actions('git commit -m "Añadir facturación — étape 1 ✓"') == {"commit"}

    def test_unbalanced_quotes_fail_closed(self):
        """A line shlex cannot parse still gates when it names git commit."""
        assert detect_git_actions("git commit -m 'unterminated") == {"commit"}
