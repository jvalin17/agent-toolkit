"""Developer mode — the toolkit's own hooks step aside while the toolkit is being changed.

Covers: the switch (launch variable and toolkit repo only), linked git
worktrees of the toolkit, a separately installed copy of the hooks, every
registered hook run as the host runs it, the session start notice, a broken
sibling module, and that no gate integrity starting record is written.
Test data: synthetic — no real PII.

Requirement: requirements/developer-mode.md.
"""

import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "hooks"))

DEV_VARIABLE = "AGENT_TOOLKIT_DEV"
SESSION_START_HOOK = "hooks/session_init.py"
SHELL_HOOK = "hooks/check_doc_write.sh"

# Every python hook a host registers, with an event that makes it do real work.
PYTHON_HOOKS = {
    "hooks/taxonomy_enforce.py": {"tool_name": "Agent", "tool_input": {"prompt": "Review the billing module"}},
    "hooks/gate_hook.py": {"tool_name": "Bash", "tool_input": {"command": "git commit -m 'Add invoice totals'"}},
    "hooks/gate_cleanup.py": {"tool_name": "Bash", "tool_input": {"command": "git commit -m 'Add invoice totals'"}},
    "hooks/skill_enforce.py": {"tool_name": "Edit", "tool_input": {"file_path": "src/billing.py"}},
    "hooks/tdd_enforce.py": {"tool_name": "Edit", "tool_input": {"file_path": "src/billing.py"}},
    "hooks/session_monitor.py": {
        "hook_event_name": "PreToolUse", "tool_name": "Bash",
        "tool_input": {"command": "cat ~/.agent-toolkit/flag.key"},
    },
    "hooks/skill_passed.py": {
        "hook_event_name": "PostToolUse", "tool_name": "Skill", "tool_input": {"skill": "implementation"},
    },
    "hooks/route_to_skill.py": {"hook_event_name": "UserPromptSubmit", "prompt": "fix the broken invoice total"},
    "hooks/canary_check.py": {"hook_event_name": "Stop"},
    "hooks/deferral_detect.py": {"hook_event_name": "Stop"},
    SESSION_START_HOOK: {"hook_event_name": "SessionStart", "source": "startup"},
}
OUTSIDE_WRITE = {"tool_name": "Write", "tool_input": {"file_path": "/var/tmp/invoice-export.csv"}}
# A command the session monitor always refuses: it names the gate key.
KEY_READ = PYTHON_HOOKS["hooks/session_monitor.py"]


def _git_init(folder: Path) -> None:
    subprocess.run(["git", "init", "-q", str(folder)], check=True, capture_output=True)


@pytest.fixture
def toolkit(tmp_path) -> Path:
    """A copy of the toolkit in its own git repository, so nothing live is touched."""
    copy = tmp_path / "toolkit"
    for folder in ("hooks", "gate", "roles", "hosts"):
        if (ROOT / folder).is_dir():
            shutil.copytree(
                ROOT / folder, copy / folder,
                ignore=shutil.ignore_patterns("__pycache__", ".session", ".gates"),
            )
    _git_init(copy)
    return copy


@pytest.fixture
def other_project(tmp_path) -> Path:
    project = tmp_path / "invoice-app"
    (project / "src").mkdir(parents=True)
    (project / "src" / "billing.py").write_text("def total(items):\n    return sum(items)\n")
    _git_init(project)
    return project


def _add_worktree(repo: Path, path: Path) -> Path:
    """A linked git worktree of ``repo`` at ``path``, made by git itself."""
    git = [
        "git", "-C", str(repo), "-c", "user.name=Ana Diaz", "-c", "user.email=ana@example.com",
        "-c", "commit.gpgsign=false",
    ]
    subprocess.run(git + ["commit", "-q", "--allow-empty", "-m", "Start"], check=True, capture_output=True)
    subprocess.run(git + ["worktree", "add", "-q", str(path)], check=True, capture_output=True)
    return path


@pytest.fixture
def installed_copy(tmp_path) -> Path:
    """A separately installed copy of the hooks, laid out like a plugin cache: in no git checkout."""
    copy = tmp_path / "plugins" / "cache" / "agent-toolkit" / "e418bf65df6e"
    for folder in ("hooks", "gate", "roles", "hosts"):
        if (ROOT / folder).is_dir():
            shutil.copytree(
                ROOT / folder, copy / folder,
                ignore=shutil.ignore_patterns("__pycache__", ".session", ".gates"),
            )
    return copy


def _record(tmp_path: Path) -> Path:
    """Where the toolkit's location is recorded, under the home folder ``_run`` gives every hook."""
    return tmp_path / "home" / ".agent-toolkit" / "dev-repo"


def _run(toolkit: Path, hook: str, event: dict, cwd: Path, dev, tmp_path: Path) -> subprocess.CompletedProcess:
    """Run a hook from the toolkit copy the way a host does: a script, the event on stdin."""
    env = dict(os.environ, HOME=str(tmp_path / "home"))
    env.pop(DEV_VARIABLE, None)
    env.pop("CLAUDE_PROJECT_DIR", None)
    if dev is not None:
        env[DEV_VARIABLE] = dev
    (tmp_path / "home").mkdir(exist_ok=True)
    runner = ["bash"] if hook.endswith(".sh") else [sys.executable]
    return subprocess.run(
        runner + [str(toolkit / hook)], input=json.dumps(event),
        text=True, capture_output=True, cwd=cwd, env=env, timeout=30,
    )


def _refused(done: subprocess.CompletedProcess) -> bool:
    return "flag key" in done.stdout or "key material" in done.stdout or '"block"' in done.stdout


class TestTheSwitch:
    """dev_mode.is_on: the launch variable and the toolkit repo, both."""

    def _is_on(self, toolkit: Path, cwd: Path, value) -> bool:
        from dev_mode import is_on

        environ = {} if value is None else {DEV_VARIABLE: value}
        return is_on(str(toolkit / "hooks" / "gate_hook.py"), environ=environ, cwd=cwd)

    def test_on_with_the_variable_inside_the_toolkit_repo(self, toolkit):
        assert self._is_on(toolkit, toolkit, "1") is True

    def test_on_from_a_subfolder_of_the_toolkit_repo(self, toolkit):
        assert self._is_on(toolkit, toolkit / "hooks", "1") is True

    def test_off_without_the_variable(self, toolkit):
        assert self._is_on(toolkit, toolkit, None) is False

    @pytest.mark.parametrize("value", ["", "0", "true", "yes", " 1"])
    def test_off_for_any_value_other_than_one(self, toolkit, value):
        assert self._is_on(toolkit, toolkit, value) is False

    def test_off_in_another_project(self, toolkit, other_project):
        assert self._is_on(toolkit, other_project, "1") is False

    def test_off_in_a_separate_repository_nested_inside_the_toolkit(self, toolkit):
        nested = toolkit / "examples" / "invoice-app"
        nested.mkdir(parents=True)
        _git_init(nested)

        assert self._is_on(toolkit, nested, "1") is False

    def test_off_outside_any_git_repository(self, toolkit, tmp_path):
        plain = tmp_path / "notes"
        plain.mkdir()

        assert self._is_on(toolkit, plain, "1") is False

    def _is_on_launched_in(self, toolkit: Path, launch_dir: Path, cwd: Path) -> bool:
        from dev_mode import is_on

        environ = {DEV_VARIABLE: "1", "CLAUDE_PROJECT_DIR": str(launch_dir)}
        return is_on(str(toolkit / "hooks" / "gate_hook.py"), environ=environ, cwd=cwd)

    def test_on_when_the_host_was_launched_in_the_toolkit(self, toolkit):
        assert self._is_on_launched_in(toolkit, toolkit / "hooks", toolkit) is True

    def test_off_when_launched_in_another_project_and_moved_into_the_toolkit(self, toolkit, other_project):
        """A session started in a user's project must not lose its hooks by a change of folder."""
        assert self._is_on_launched_in(toolkit, other_project, toolkit) is False

    def test_off_when_launched_in_the_toolkit_and_moved_to_another_project(self, toolkit, other_project):
        assert self._is_on_launched_in(toolkit, toolkit, other_project) is False

    def test_on_when_the_toolkit_is_reached_through_a_link(self, toolkit, tmp_path):
        link = tmp_path / "toolkit-link"
        link.symlink_to(toolkit, target_is_directory=True)

        assert self._is_on(link, toolkit, "1") is True


class TestWorktrees:
    """A linked git worktree of the toolkit is the toolkit; a folder that only points at it is not."""

    def _is_on(self, hooks_in: Path, cwd: Path, launch_dir: Path = None) -> bool:
        from dev_mode import is_on

        environ = {DEV_VARIABLE: "1"}
        if launch_dir is not None:
            environ["CLAUDE_PROJECT_DIR"] = str(launch_dir)
        return is_on(str(hooks_in / "hooks" / "gate_hook.py"), environ=environ, cwd=cwd)

    def test_on_in_a_linked_worktree_of_the_toolkit(self, toolkit, tmp_path):
        worktree = _add_worktree(toolkit, tmp_path / "toolkit-gate-integrity")

        assert self._is_on(toolkit, worktree) is True

    def test_on_in_a_subfolder_of_a_linked_worktree(self, toolkit, tmp_path):
        worktree = _add_worktree(toolkit, tmp_path / "toolkit-gate-integrity")
        (worktree / "tests").mkdir()

        assert self._is_on(toolkit, worktree / "tests") is True

    def test_on_when_launched_in_the_toolkit_and_working_in_its_worktree(self, toolkit, tmp_path):
        worktree = _add_worktree(toolkit, tmp_path / "toolkit-gate-integrity")

        assert self._is_on(toolkit, worktree, launch_dir=toolkit) is True

    def test_on_when_launched_in_a_worktree_and_working_in_the_toolkit(self, toolkit, tmp_path):
        worktree = _add_worktree(toolkit, tmp_path / "toolkit-gate-integrity")

        assert self._is_on(toolkit, toolkit, launch_dir=worktree) is True

    def test_on_in_the_main_checkout_for_hooks_loaded_from_a_worktree(self, toolkit, tmp_path):
        worktree = _add_worktree(toolkit, tmp_path / "toolkit-gate-integrity")

        assert self._is_on(worktree, toolkit) is True

    def test_off_in_a_worktree_of_another_project(self, toolkit, other_project, tmp_path):
        worktree = _add_worktree(other_project, tmp_path / "invoice-app-refunds")

        assert self._is_on(toolkit, worktree) is False

    def test_off_when_launched_in_a_worktree_of_another_project(self, toolkit, other_project, tmp_path):
        worktree = _add_worktree(other_project, tmp_path / "invoice-app-refunds")

        assert self._is_on(toolkit, toolkit, launch_dir=worktree) is False

    def test_off_in_a_submodule_inside_the_toolkit(self, toolkit):
        """A submodule also has a ``.git`` file, but it is a repository of its own."""
        (toolkit / ".git" / "modules" / "charts").mkdir(parents=True)
        submodule = toolkit / "vendor" / "charts"
        submodule.mkdir(parents=True)
        (submodule / ".git").write_text("gitdir: ../../.git/modules/charts\n")

        assert self._is_on(toolkit, submodule) is False

    def test_off_in_a_folder_that_points_at_the_toolkit_without_being_named_back(
        self, toolkit, other_project, tmp_path,
    ):
        """A hand-written ``.git`` file cannot make another project a worktree of the toolkit."""
        _add_worktree(toolkit, tmp_path / "toolkit-gate-integrity")
        entry = toolkit / ".git" / "worktrees" / "toolkit-gate-integrity"
        assert entry.is_dir()
        disguised = other_project / "tools"
        disguised.mkdir()
        (disguised / ".git").write_text(f"gitdir: {entry}\n")

        assert self._is_on(toolkit, disguised) is False

    @pytest.mark.parametrize("launched_there", [True, False])
    def test_off_in_a_project_whose_git_entry_is_a_link_to_a_toolkit_worktree(
        self, toolkit, tmp_path, launched_there,
    ):
        """Linking to a real worktree's ``.git`` file borrows its records; the project is still not the toolkit."""
        worktree = _add_worktree(toolkit, tmp_path / "toolkit-gate-integrity")
        project = tmp_path / "payroll-app"
        project.mkdir()
        (project / ".git").symlink_to(worktree / ".git")

        assert self._is_on(toolkit, project, launch_dir=project if launched_there else None) is False

    def test_off_in_a_project_whose_git_entry_is_a_link_to_the_toolkit_git_folder(self, toolkit, tmp_path):
        project = tmp_path / "payroll-app"
        project.mkdir()
        (project / ".git").symlink_to(toolkit / ".git", target_is_directory=True)

        assert self._is_on(toolkit, project) is False

    def test_off_in_a_folder_whose_git_file_is_not_a_pointer(self, toolkit, other_project):
        broken = other_project / "tools"
        broken.mkdir()
        (broken / ".git").write_text("not a git pointer\n")

        assert self._is_on(toolkit, broken) is False

    def test_hook_steps_aside_in_a_linked_worktree(self, toolkit, tmp_path):
        worktree = _add_worktree(toolkit, tmp_path / "toolkit-gate-integrity")

        done = _run(toolkit, "hooks/session_monitor.py", KEY_READ, worktree, "1", tmp_path)

        assert (done.returncode, done.stdout, done.stderr) == (0, "", "")

    def test_shell_hook_steps_aside_in_a_linked_worktree(self, toolkit, tmp_path):
        worktree = _add_worktree(toolkit, tmp_path / "toolkit-gate-integrity")

        done = _run(toolkit, SHELL_HOOK, OUTSIDE_WRITE, worktree, "1", tmp_path)

        assert (done.returncode, done.stdout, done.stderr) == (0, "", "")

    def test_hook_in_a_worktree_of_another_project_still_refuses(self, toolkit, other_project, tmp_path):
        worktree = _add_worktree(other_project, tmp_path / "invoice-app-refunds")

        done = _run(toolkit, "hooks/session_monitor.py", KEY_READ, worktree, "1", tmp_path)

        assert _refused(done), done.stdout


class TestAnInstalledCopy:
    """The plugin copy steps aside in the toolkit's own repository, and nowhere else."""

    START = PYTHON_HOOKS[SESSION_START_HOOK]

    def _start_session_in_the_toolkit(self, toolkit: Path, tmp_path: Path) -> None:
        """What a developer-mode launch does: the toolkit's own session start hook runs."""
        _run(toolkit, SESSION_START_HOOK, self.START, toolkit, "1", tmp_path)

    def test_session_start_in_the_toolkit_records_where_the_toolkit_is(self, toolkit, tmp_path):
        self._start_session_in_the_toolkit(toolkit, tmp_path)

        assert _record(tmp_path).read_text().strip() == os.path.realpath(toolkit)

    def test_session_start_in_a_worktree_records_the_main_checkout(self, toolkit, tmp_path):
        worktree = _add_worktree(toolkit, tmp_path / "toolkit-gate-integrity")

        _run(toolkit, SESSION_START_HOOK, self.START, worktree, "1", tmp_path)

        assert _record(tmp_path).read_text().strip() == os.path.realpath(toolkit)

    def test_session_start_without_the_variable_records_nothing(self, toolkit, tmp_path):
        _run(toolkit, SESSION_START_HOOK, self.START, toolkit, None, tmp_path)

        assert not _record(tmp_path).exists()

    def test_session_start_in_another_project_records_nothing(self, toolkit, other_project, tmp_path):
        _run(toolkit, SESSION_START_HOOK, self.START, other_project, "1", tmp_path)

        assert not _record(tmp_path).exists()

    @pytest.mark.parametrize("hook", sorted(set(PYTHON_HOOKS) - {SESSION_START_HOOK}))
    def test_installed_hook_steps_aside_in_the_recorded_toolkit(self, toolkit, installed_copy, tmp_path, hook):
        self._start_session_in_the_toolkit(toolkit, tmp_path)

        done = _run(installed_copy, hook, PYTHON_HOOKS[hook], toolkit, "1", tmp_path)

        assert (done.returncode, done.stdout, done.stderr) == (0, "", "")

    def test_installed_shell_hook_steps_aside_in_the_recorded_toolkit(self, toolkit, installed_copy, tmp_path):
        self._start_session_in_the_toolkit(toolkit, tmp_path)

        done = _run(installed_copy, SHELL_HOOK, OUTSIDE_WRITE, toolkit, "1", tmp_path)

        assert (done.returncode, done.stdout, done.stderr) == (0, "", "")

    def test_installed_hook_steps_aside_in_a_worktree_of_the_recorded_toolkit(
        self, toolkit, installed_copy, tmp_path,
    ):
        self._start_session_in_the_toolkit(toolkit, tmp_path)
        worktree = _add_worktree(toolkit, tmp_path / "toolkit-gate-integrity")

        done = _run(installed_copy, "hooks/gate_hook.py", PYTHON_HOOKS["hooks/gate_hook.py"], worktree, "1", tmp_path)

        assert (done.returncode, done.stdout, done.stderr) == (0, "", "")

    def test_installed_session_start_prints_only_the_notice(self, toolkit, installed_copy, tmp_path):
        self._start_session_in_the_toolkit(toolkit, tmp_path)

        done = _run(installed_copy, SESSION_START_HOOK, self.START, toolkit, "1", tmp_path)

        context = json.loads(done.stdout)["hookSpecificOutput"]["additionalContext"]
        assert "developer mode is on" in context.lower()
        assert "AGENT TOOLKIT ACTIVE" not in done.stdout

    def test_installed_hook_still_refuses_while_nothing_is_recorded(self, toolkit, installed_copy, tmp_path):
        done = _run(installed_copy, "hooks/session_monitor.py", KEY_READ, toolkit, "1", tmp_path)

        assert _refused(done), done.stdout

    def test_installed_hook_still_refuses_in_another_project(self, toolkit, installed_copy, other_project, tmp_path):
        self._start_session_in_the_toolkit(toolkit, tmp_path)

        done = _run(installed_copy, "hooks/session_monitor.py", KEY_READ, other_project, "1", tmp_path)

        assert _refused(done), done.stdout

    def test_installed_hook_still_refuses_without_the_variable(self, toolkit, installed_copy, tmp_path):
        self._start_session_in_the_toolkit(toolkit, tmp_path)

        done = _run(installed_copy, "hooks/session_monitor.py", KEY_READ, toolkit, None, tmp_path)

        assert _refused(done), done.stdout

    def test_installed_copy_never_writes_the_record(self, installed_copy, other_project, tmp_path):
        """Only a checkout's own hooks know where the toolkit is; a copy cannot name a project."""
        _run(installed_copy, SESSION_START_HOOK, self.START, other_project, "1", tmp_path)

        assert not _record(tmp_path).exists()

    @pytest.mark.parametrize("recorded", ["", "\n", "invoice-app", "../invoice-app", "/nonexistent/toolkit"])
    def test_a_record_that_names_no_folder_is_ignored(self, installed_copy, other_project, tmp_path, recorded):
        _record(tmp_path).parent.mkdir(parents=True)
        _record(tmp_path).write_text(recorded)

        done = _run(installed_copy, "hooks/session_monitor.py", KEY_READ, other_project, "1", tmp_path)

        assert _refused(done), done.stdout

    @pytest.mark.parametrize("recorded", [".", "../toolkit"])
    def test_a_relative_record_is_ignored_even_when_it_leads_to_the_toolkit(
        self, toolkit, installed_copy, tmp_path, recorded,
    ):
        """A relative entry would mean "wherever the hook happens to run"; only a full path names a folder."""
        _record(tmp_path).parent.mkdir(parents=True)
        _record(tmp_path).write_text(recorded)

        done = _run(installed_copy, "hooks/session_monitor.py", KEY_READ, toolkit, "1", tmp_path)

        assert _refused(done), done.stdout

    def test_a_record_naming_a_project_that_links_to_the_toolkit_git_folder_is_ignored(
        self, toolkit, installed_copy, tmp_path,
    ):
        project = tmp_path / "payroll-app"
        shutil.copytree(toolkit / "hooks", project / "hooks")
        (project / ".git").symlink_to(toolkit / ".git", target_is_directory=True)
        _record(tmp_path).parent.mkdir(parents=True)
        _record(tmp_path).write_text(str(project))

        done = _run(installed_copy, "hooks/session_monitor.py", KEY_READ, project, "1", tmp_path)

        assert _refused(done), done.stdout

    def test_session_start_does_not_write_through_a_link_planted_at_the_draft_name(self, toolkit, tmp_path):
        """The record is written by way of a draft file; a link waiting there must not be followed."""
        from dev_mode import _record_toolkit

        _record(tmp_path).parent.mkdir(parents=True)
        payslips = tmp_path / "payslips.csv"
        payslips.write_text("Maria Garcia,4120.50\n")
        (_record(tmp_path).parent / f"dev-repo.{os.getpid()}").symlink_to(payslips)

        _record_toolkit(str(toolkit / SESSION_START_HOOK), environ={"HOME": str(tmp_path / "home")})

        assert payslips.read_text() == "Maria Garcia,4120.50\n"
        assert not _record(tmp_path).exists()

    def test_a_record_naming_a_project_with_no_toolkit_hooks_is_ignored(
        self, installed_copy, other_project, tmp_path,
    ):
        _record(tmp_path).parent.mkdir(parents=True)
        _record(tmp_path).write_text(str(other_project))

        done = _run(installed_copy, "hooks/session_monitor.py", KEY_READ, other_project, "1", tmp_path)

        assert _refused(done), done.stdout

    def test_a_record_naming_a_worktree_instead_of_a_main_checkout_is_ignored(
        self, toolkit, installed_copy, tmp_path,
    ):
        """The record is always a main checkout; anything else was not written by the session start hook."""
        worktree = _add_worktree(toolkit, tmp_path / "toolkit-gate-integrity")
        shutil.copytree(toolkit / "hooks", worktree / "hooks")
        _record(tmp_path).parent.mkdir(parents=True)
        _record(tmp_path).write_text(str(worktree))

        done = _run(installed_copy, "hooks/session_monitor.py", KEY_READ, worktree, "1", tmp_path)

        assert _refused(done), done.stdout

    def test_off_when_the_host_was_launched_in_another_project(self, toolkit, installed_copy, other_project, tmp_path):
        from dev_mode import is_on

        self._start_session_in_the_toolkit(toolkit, tmp_path)
        environ = {DEV_VARIABLE: "1", "HOME": str(tmp_path / "home"), "CLAUDE_PROJECT_DIR": str(other_project)}

        assert is_on(str(installed_copy / "hooks" / "gate_hook.py"), environ=environ, cwd=toolkit) is False

    def test_a_checkout_does_not_follow_a_record_that_names_another_toolkit(self, toolkit, tmp_path):
        """A checkout's own hooks go by where they were loaded from, never by the record."""
        from dev_mode import is_on

        second = tmp_path / "toolkit-second-clone"
        shutil.copytree(toolkit / "hooks", second / "hooks")
        _git_init(second)
        _record(tmp_path).parent.mkdir(parents=True)
        _record(tmp_path).write_text(str(second))
        environ = {DEV_VARIABLE: "1", "HOME": str(tmp_path / "home")}

        assert is_on(str(toolkit / "hooks" / "gate_hook.py"), environ=environ, cwd=second) is False


class TestTheListOfHooks:
    def test_every_registered_hook_is_covered_here(self):
        registered = set()
        for source in (ROOT / "install.sh", ROOT / "hooks" / "hooks.json", ROOT / "scripts" / "config_generator.py"):
            registered |= set(re.findall(r"hooks/[a-z_]+\.(?:py|sh)", source.read_text()))
        registered = {hook for hook in registered if (ROOT / hook).is_file()}

        assert registered == set(PYTHON_HOOKS) | {SHELL_HOOK}


class TestHooksStepAside:
    """Variable set, in the toolkit repo: exit 0 and nothing applied."""

    @pytest.mark.parametrize("hook", sorted(set(PYTHON_HOOKS) - {SESSION_START_HOOK}))
    def test_python_hook_exits_zero_with_no_output(self, toolkit, tmp_path, hook):
        done = _run(toolkit, hook, PYTHON_HOOKS[hook], toolkit, "1", tmp_path)

        assert (done.returncode, done.stdout, done.stderr) == (0, "", "")

    def test_shell_hook_exits_zero_with_no_output(self, toolkit, tmp_path):
        done = _run(toolkit, SHELL_HOOK, OUTSIDE_WRITE, toolkit, "1", tmp_path)

        assert (done.returncode, done.stdout, done.stderr) == (0, "", "")

    def test_session_start_prints_only_the_notice(self, toolkit, tmp_path):
        done = _run(toolkit, SESSION_START_HOOK, PYTHON_HOOKS[SESSION_START_HOOK], toolkit, "1", tmp_path)

        assert done.returncode == 0
        context = json.loads(done.stdout)["hookSpecificOutput"]["additionalContext"]
        assert "developer mode is on" in context.lower()
        assert "not applied" in context.lower()
        assert "AGENT TOOLKIT ACTIVE" not in done.stdout
        assert not (toolkit / ".session").exists()

    def test_no_gate_integrity_starting_record_is_written(self, toolkit, tmp_path):
        state = toolkit / ".scratch" / "autopilot" / "state.json"
        state.parent.mkdir(parents=True)
        state.write_text(json.dumps({
            "status": "running", "task": "Add invoice totals",
            "steps": [{"name": "plan", "status": "pending"}],
        }))
        event = {"hook_event_name": "PreToolUse", "tool_name": "Bash", "tool_input": {"command": "ls"}}

        # The starting record lives in the hook-owned state folder; in developer
        # mode the hook that records it writes no state at all, during a run too.
        _run(toolkit, "hooks/session_monitor.py", event, toolkit, "1", tmp_path)
        assert not (toolkit / ".session").exists()

        # The same call without the variable does write state, so the check above means something.
        _run(toolkit, "hooks/session_monitor.py", event, toolkit, None, tmp_path)
        assert (toolkit / ".session" / "state.json").is_file()


class TestHooksBehaveAsNormal:
    def test_variable_set_in_another_project_still_refuses(self, toolkit, other_project, tmp_path):
        done = _run(toolkit, "hooks/session_monitor.py", KEY_READ, other_project, "1", tmp_path)

        assert _refused(done), done.stdout

    def test_variable_not_set_in_the_toolkit_repo_still_refuses(self, toolkit, tmp_path):
        done = _run(toolkit, "hooks/session_monitor.py", KEY_READ, toolkit, None, tmp_path)

        assert _refused(done), done.stdout

    def test_shell_hook_with_the_variable_in_another_project_still_blocks(self, toolkit, other_project, tmp_path):
        done = _run(toolkit, SHELL_HOOK, OUTSIDE_WRITE, other_project, "1", tmp_path)

        assert json.loads(done.stdout)["decision"] == "block"

    def test_shell_hook_without_the_variable_in_the_toolkit_repo_still_blocks(self, toolkit, tmp_path):
        done = _run(toolkit, SHELL_HOOK, OUTSIDE_WRITE, toolkit, None, tmp_path)

        assert json.loads(done.stdout)["decision"] == "block"

    def test_session_start_in_another_project_gives_no_developer_notice(self, toolkit, other_project, tmp_path):
        from dev_mode import is_on

        assert is_on(str(toolkit / SESSION_START_HOOK), environ={DEV_VARIABLE: "1"}, cwd=other_project) is False


class TestBrokenSiblingModule:
    """A half-edited helper must not crash a hook in developer mode."""

    BROKEN = ("session_state.py", "mode_resolver.py", "hook_io.py", "path_protection.py", "git_command.py")

    def _break_siblings(self, toolkit: Path) -> None:
        for name in self.BROKEN:
            (toolkit / "hooks" / name).write_text("def half_edited(:\n")

    @pytest.mark.parametrize("hook", sorted(PYTHON_HOOKS))
    def test_hook_still_exits_zero(self, toolkit, tmp_path, hook):
        self._break_siblings(toolkit)

        done = _run(toolkit, hook, PYTHON_HOOKS[hook], toolkit, "1", tmp_path)

        assert done.returncode == 0
        assert "Traceback" not in done.stderr
        assert "crashed" not in done.stdout

    @pytest.mark.parametrize("dev", [None, "1"])
    def test_a_broken_switch_means_not_on_and_the_hook_still_refuses(self, toolkit, other_project, tmp_path, dev):
        """The check runs first in every hook, in every project: a fault in it must not switch hooks off."""
        (toolkit / "hooks" / "dev_mode.py").write_text("def half_edited(:\n")

        done = _run(toolkit, "hooks/session_monitor.py", KEY_READ, other_project, dev, tmp_path)

        assert _refused(done), (done.returncode, done.stdout, done.stderr)

    def test_a_missing_switch_means_not_on_and_the_hook_still_refuses(self, toolkit, tmp_path):
        (toolkit / "hooks" / "dev_mode.py").unlink()

        done = _run(toolkit, "hooks/session_monitor.py", KEY_READ, toolkit, "1", tmp_path)

        assert _refused(done), (done.returncode, done.stdout, done.stderr)
        assert "developer mode check failed, so hooks stay on" in done.stderr

    @pytest.mark.parametrize("hook", sorted(PYTHON_HOOKS))
    def test_without_the_variable_the_same_break_does_crash(self, toolkit, tmp_path, hook):
        """The control for every hook: it does reach its sibling imports when developer mode is off."""
        self._break_siblings(toolkit)

        done = _run(toolkit, hook, PYTHON_HOOKS[hook], toolkit, None, tmp_path)

        assert "SyntaxError" in done.stderr or "crashed" in done.stdout, (done.stdout, done.stderr)
