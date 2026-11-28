"""Direct tests for hooks/path_protection.py — G-SESSION-1, G-GATE-1, G-REPORT-1."""

import sys
import time
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "hooks"))

from path_protection import (
    GATE_WRITING_TOOLS,
    PROTECTED_PATHS,
    check_protected_paths,
)
from session_state import SessionState


def _state(gate_protect=True, report_protect=True):
    return SessionState(
        session_start=1760227200,  # 2025-10-12T00:00:00Z
        gate_protect=gate_protect,
        report_protect=report_protect,
    )


class TestProtectedDirs:
    @pytest.mark.parametrize("tool", ["Write", "Edit"])
    @pytest.mark.parametrize("path, rule", [
        ("/home/ana/app/.session/state.json", "G-SESSION-1"),
        ("/home/ana/app/.gates/precommit-passed", "G-GATE-1"),
        ("/home/ana/app/.gates/stamps/reviewer", "G-GATE-1"),
        ("/home/ana/app/reports/precommit/pc_login_1a2b3c4d.md", "G-REPORT-1"),
    ])
    def test_blocks_write_to_each_protected_dir(self, tool, path, rule):
        blocked, msg = check_protected_paths(_state(), tool, path, "")
        assert blocked is True
        expected = next(s["message"] for s in PROTECTED_PATHS if s["rule"] == rule)
        assert msg == expected

    def test_allows_write_to_source_file(self):
        blocked, msg = check_protected_paths(
            _state(), "Write", "/home/ana/app/src/billing/invoice.py", ""
        )
        assert blocked is False
        assert msg == ""

    def test_allows_unicode_source_path(self):
        blocked, _ = check_protected_paths(
            _state(), "Edit", "/home/ana/app/src/módulos/façade.py", ""
        )
        assert blocked is False

    def test_bash_write_to_gates_blocked(self):
        blocked, _ = check_protected_paths(
            _state(), "Bash", "", "echo READY > .gates/precommit-passed"
        )
        assert blocked is True

    def test_bash_read_of_gates_allowed(self):
        blocked, _ = check_protected_paths(
            _state(), "Bash", "", "cat .gates/precommit-passed"
        )
        assert blocked is False

    def test_gate_protect_off_allows_gates_write(self):
        blocked, _ = check_protected_paths(
            _state(gate_protect=False), "Write", "/home/ana/app/.gates/precommit-passed", ""
        )
        assert blocked is False

    def test_report_protect_off_allows_reports_write(self):
        blocked, _ = check_protected_paths(
            _state(report_protect=False), "Write", "/home/ana/app/reports/evaluate/x.md", ""
        )
        assert blocked is False


class TestDefaultDeny:
    """Bash that names a protected path is denied unless every segment is read-only."""

    @pytest.mark.parametrize("command", [
        "touch .gates/precommit-passed",
        "python3 -c 'open(\".gates/precommit-passed\",\"w\").write(\"READY\")'",
        "ln -s /tmp/x .gates/evaluate-passed",
        "cp /tmp/flag .gates/precommit-passed",
        "node -e 'require(\"fs\").writeFileSync(\".gates/evaluate-passed\",\"PASSED 100\")'",
        "cat .gates/precommit-passed > /tmp/copy && touch .gates/reviewer-passed",
        "perl -e 'open(F,\">.session/state.json\")'",
        "truncate -s 0 reports/precommit/pc_login_1a2b3c4d.md",
        "dd if=/dev/zero of=.gates/x",
        "cat .gates/precommit-passed | tee .gates/evaluate-passed",
    ])
    def test_default_deny_for_protected_paths(self, command):
        blocked, msg = check_protected_paths(_state(), "Bash", "", command)
        assert blocked is True, command
        assert "hook-managed" in msg or "read-only" in msg

    @pytest.mark.parametrize("command", [
        "cat .gates/precommit-passed",
        "ls -la .gates/",
        "ls .gates/stamps 2>/dev/null",
        "grep -c READY .gates/precommit-passed",
        "head -n 3 reports/precommit/pc_login_1a2b3c4d.md",
        "stat .session/state.json",
        "git status --short .gates/",
        "git check-ignore -v .gates/precommit-passed",
        "find .gates -type f",
        "wc -l reports/evaluate/eval_login_1a2b3c4d.md",
        "test -f .gates/precommit-passed && cat .gates/precommit-passed",
    ])
    def test_read_only_access_allowed(self, command):
        blocked, _ = check_protected_paths(_state(), "Bash", "", command)
        assert blocked is False, command

    def test_unparseable_command_naming_protected_path_is_denied(self):
        blocked, _ = check_protected_paths(_state(), "Bash", "", "cat '.gates/precommit-passed")
        assert blocked is True


class TestHeredocsAndGit:
    """Commit messages and file contents are data; interpreter heredocs are code."""

    def test_commit_message_heredoc_naming_policy_files_allowed(self):
        command = (
            "git commit -q -F - <<'EOF'\n"
            "Harden gates\n\n"
            "A deleted gates.json now blocks; .gates/ flags are signed; the .agent-toolkit\n"
            "verifier is never used; key lives outside signing.key paths.\n"
            "EOF\n"
            "git log --oneline -1 && git push origin main"
        )
        blocked, msg = check_protected_paths(_state(), "Bash", "", command)
        assert blocked is False, msg

    def test_heredoc_after_a_chain_uses_only_its_own_command(self):
        command = (
            "python3 -m pytest -q && git add -A && git commit -q -F - <<'EOF'\n"
            "Fail closed when gates.json is deleted; sign .gates/ flags\n"
            "EOF\n"
            "git push origin main"
        )
        blocked, msg = check_protected_paths(_state(), "Bash", "", command)
        assert blocked is False, msg

    def test_interpreter_heredoc_is_still_scanned(self):
        command = "bash <<'EOF'\ntouch .gates/precommit-passed\nEOF"
        blocked, _ = check_protected_paths(_state(), "Bash", "", command)
        assert blocked is True
        command = "python3 - <<'EOF'\nopen('.gates/precommit-passed','w')\nEOF"
        blocked, _ = check_protected_paths(_state(), "Bash", "", command)
        assert blocked is True

    def test_cat_heredoc_into_protected_path_blocked(self):
        command = "cat > .gates/precommit-passed <<'EOF'\nREADY\nEOF"
        blocked, _ = check_protected_paths(_state(), "Bash", "", command)
        assert blocked is True

    @pytest.mark.parametrize("command", [
        "git add gates.json",
        "git add -A && git commit -m 'tighten gates.json policy'",
        "git diff HEAD -- gates.json .claude/settings.json",
        "git push origin main",
    ])
    def test_git_non_writing_subcommands_allowed(self, command):
        blocked, msg = check_protected_paths(_state(), "Bash", "", command)
        assert blocked is False, msg

    @pytest.mark.parametrize("command", [
        "git checkout -- gates.json",
        "git restore gates.json",
        "git rm gates.json",
        "git checkout HEAD~1 -- .claude/settings.json",
    ])
    def test_git_writing_subcommands_naming_policy_blocked(self, command):
        blocked, _ = check_protected_paths(_state(), "Bash", "", command)
        assert blocked is True, command


class TestConfigFiles:
    """gates.json and host hook settings are policy — the agent may read, not write."""

    @pytest.mark.parametrize("path", [
        "/home/ana/app/gates.json",
        "gates.json",
        "/home/ana/app/.claude/settings.json",
        "/home/ana/app/.claude/settings.local.json",
        "/home/ana/.claude/settings.json",
        "/home/ana/app/.cursor/hooks.json",
        "/home/ana/app/.grok/hooks.json",
        "/home/ana/app/.windsurf/hooks.json",
        "/home/ana/app/.codex/config.toml",
        "/home/ana/app/.agent-toolkit/gate/scripts/verify_gate.py",
    ])
    @pytest.mark.parametrize("tool", ["Write", "Edit"])
    def test_config_files_protected(self, tool, path):
        blocked, msg = check_protected_paths(_state(), tool, path, "")
        assert blocked is True, path
        assert "G-CONFIG-1" in msg

    @pytest.mark.parametrize("path", [
        "/home/ana/agent-toolkit/templates/gates.json",
        "/home/ana/agent-toolkit/hooks/gates.json",
        "/home/ana/agent-toolkit/hooks/hooks.json",
        "/home/ana/app/src/settings.py",
        "/home/ana/app/docs/gates.md",
    ])
    def test_toolkit_sources_and_lookalikes_allowed(self, path):
        blocked, _ = check_protected_paths(_state(), "Write", path, "")
        assert blocked is False, path

    @pytest.mark.parametrize("command", [
        "jq '.mode = \"minimal\"' gates.json > gates.json.tmp && mv gates.json.tmp gates.json",
        "rm gates.json",
        "sed -i 's/safe/minimal/' gates.json",
        "python3 -c 'import json; json.dump({}, open(\"gates.json\",\"w\"))'",
        "cp /tmp/settings.json .claude/settings.json",
    ])
    def test_bash_writes_to_config_blocked(self, command):
        blocked, _ = check_protected_paths(_state(), "Bash", "", command)
        assert blocked is True, command

    @pytest.mark.parametrize("command", ["cat gates.json", "jq .mode gates.json", "git diff gates.json"])
    def test_bash_reads_of_config_allowed(self, command):
        blocked, _ = check_protected_paths(_state(), "Bash", "", command)
        assert blocked is False, command

    @pytest.mark.parametrize("command", [
        "cd ~/.agent-toolkit && printf /home/ana/app > dev-repo",
        "cd ~/.agent-toolkit; echo /home/ana/app > dev-repo",
        "cd $HOME && cd .agent-toolkit && echo /home/ana/app > dev-repo",
        "ln -sfn /home/ana/app ~/.agent-toolkit",
        "rm -rf /home/ana/.agent-toolkit",
        "mv ~/.agent-toolkit ~/toolkit-state-old",
        "cp /tmp/record '/home/ana/.agent-toolkit'",
    ])
    def test_bash_writes_naming_the_toolkit_home_folder_itself_blocked(self, command):
        """The folder holds the signing key and the developer-mode record: naming it without a slash is no way in."""
        blocked, msg = check_protected_paths(_state(), "Bash", "", command)
        assert blocked is True, command
        assert "G-CONFIG-1" in msg

    @pytest.mark.parametrize("tool", ["Write", "Edit"])
    def test_toolkit_home_folder_itself_protected_from_edit_tools(self, tool):
        blocked, msg = check_protected_paths(_state(), tool, "/home/ana/.agent-toolkit", "")
        assert blocked is True
        assert "G-CONFIG-1" in msg

    @pytest.mark.parametrize("command", ["ls ~/.agent-toolkit", "ls -la /home/ana/.agent-toolkit"])
    def test_bash_listing_of_the_toolkit_home_folder_allowed(self, command):
        blocked, _ = check_protected_paths(_state(), "Bash", "", command)
        assert blocked is False, command

    @pytest.mark.parametrize("command", [
        "rm /home/ana/agent-toolkit/notes.txt",
        "touch docs/.agent-toolkit-notes.md",
        "mkdir -p build/my.agent-toolkit",
    ])
    def test_bash_writes_to_lookalike_names_allowed(self, command):
        blocked, _ = check_protected_paths(_state(), "Bash", "", command)
        assert blocked is False, command

    @pytest.mark.parametrize("command", [
        # a glob that the shell expands to the folder
        "echo /home/ana/app > ~/.agent-toolki?/dev-repo",
        "echo /home/ana/app > ~/.agent-tool*/dev-repo",
        "echo /home/ana/app > ~/.agent-toolki[t]/dev-repo",
        "echo /home/ana/app > ~/.agent-{toolkit,backup}/dev-repo",
        "rm -rf ~/.a*",
        "rm -rf ~/.[a-z]*",
        # quoting or escaping inside the name
        "echo /home/ana/app > ~/.agent-'toolkit'/dev-repo",
        'echo /home/ana/app > ~/.agent-"tool"kit/dev-repo',
        "echo /home/ana/app > ~/.agent-tool\\kit/dev-repo",
        # a shell variable spliced into the name
        "d=toolkit; echo /home/ana/app > ~/.agent-$d/dev-repo",
        "a=.agent-; b=toolkit; cp /tmp/record ~/$a$b/dev-repo",
        "name=.agent-toolkit && echo /home/ana/app > $HOME/${name}/dev-repo",
        "echo /home/ana/app > ~/.agent-$SUFFIX/dev-repo",
        "echo /home/ana/app > ~/${unset:-.agent-toolkit}/dev-repo",
        "echo /home/ana/app > ~/.agent-$(echo toolkit)/dev-repo",
        "echo /home/ana/app > ~/.agent-`echo toolkit`/dev-repo",
        # an interpreter that puts the name together
        """python3 -c "import os; open(os.path.expanduser('~/.agent-' + 'toolkit/dev-repo'), 'w').write('/home/ana/app')" """,
        """python3 -c "import os; open(os.path.join(os.path.expanduser('~'), '.agent-' 'toolkit', 'dev-repo'), 'w')" """,
        """python3 -c "open('/home/ana/' + ''.join(['.agent-', 'toolkit']) + '/dev-repo', 'w')" """,
        """python3 -c "open('/home/ana/.agent-%s/dev-repo' % 'toolkit', 'w')" """,
        """python3 -c "s = 'toolkit'; open(f'/home/ana/.agent-{s}/dev-repo', 'w')" """,
        """node -e "require('fs').writeFileSync('/home/ana/.agent-' + 'toolkit/dev-repo', '/home/ana/app')" """,
    ])
    def test_bash_writes_that_disguise_the_toolkit_home_folder_blocked(self, command):
        """A glob, a spliced variable or a name put together in code still names the folder."""
        blocked, msg = check_protected_paths(_state(), "Bash", "", command)
        assert blocked is True, command
        assert "G-CONFIG-1" in msg
        assert "Ask the user" in msg

    @pytest.mark.parametrize("command", [
        "ls ~/.agent-toolki?",
        "cat ~/.agent-tool*/dev-repo",
        "d=toolkit; ls ~/.agent-$d",
    ])
    def test_bash_reads_through_a_disguised_name_allowed(self, command):
        blocked, _ = check_protected_paths(_state(), "Bash", "", command)
        assert blocked is False, command

    @pytest.mark.parametrize("command", [
        "rm build/*.pyc",
        "rm -rf node_modules/.cache/*",
        "rm ~/.b*",
        "cp $SRC/app.py $DEST/",
        "mkdir -p $HOME/.config/invoice-app",
        "d=toolkit; mkdir docs/agent-$d-notes",
        "touch ~/.agent-toolkit-notes?",
        "mv report-$DATE.csv archive/",
        """python3 -c "print('agent-' + 'toolkit')" """,
        """python3 -c "open('out/' + name + '.csv', 'w')" """,
    ])
    def test_bash_writes_that_only_resemble_a_disguise_allowed(self, command):
        blocked, _ = check_protected_paths(_state(), "Bash", "", command)
        assert blocked is False, command

    @pytest.mark.parametrize("command", [
        # the shell changes or fills in the rest of the name
        "t=toolkitx; echo /home/ana/app > ~/.agent-${t%x}/dev-repo",
        "echo /home/ana/app > ~/.agent-$'toolkit'/dev-repo",
        "echo /home/ana/app > ~/.agent-\\\ntoolkit/dev-repo",
        "d=toolkit; echo /home/ana/app > ~/.agent-$d/dev-repo; d=zzz",
        "echo /home/ana/app > ~/.agent-$(echo $(echo toolkit))/dev-repo",
        "xargs -I@ sh -c 'echo /home/ana/app > ~/.agent-@/dev-repo'",
        "rm -rf ~/.agent-toolki[[:alpha:]]",
        "rm -rf ~/.agent-toolki[^x]",
        # only the leading dot is spelled out under the home folder
        "rm -rf ~/.$(echo agent-toolkit)",
        "for d in gent-toolkit; do rm -rf ~/.a$d; done",
        "cp /tmp/record ~/.{agent-toolkit,zz}/",
        "cp /tmp/record ~/{.agent-toolkit,zz}/",
        "rm -rf $HOME/.a*",
        "rm -rf /Users/ana/.agent?toolkit",
        "rm -rf /Users/ana/.agent[[:punct:]]toolkit",
        "rm -rf ~/.agent\\\n-toolkit",
        # a file system that ignores case
        "echo /home/ana/app > ~/.Agent-Toolkit/dev-repo",
        "rm -rf ~/.AGENT-TOOLKIT",
        # code that keeps the start of the name in one piece
        """python3 -c "import os; s='toolkit'; open(os.path.expanduser('~/.agent-' + s + '/dev-repo'), 'w')" """,
        """python3 -c "import os; open(os.path.expanduser('~/.{}/flag'.format('agent-toolkit')), 'w')" """,
        """node -e "const s='toolkit'; require('fs').rmSync(`/home/ana/.agent-${s}`, {recursive: true})" """,
    ])
    def test_bash_writes_that_leave_part_of_the_name_to_run_time_blocked(self, command):
        blocked, msg = check_protected_paths(_state(), "Bash", "", command)
        assert blocked is True, command
        assert "G-CONFIG-1" in msg

    @pytest.mark.parametrize("command", [
        "cd /tmp/workdir && echo /home/ana/app > dev-repo",
        "shopt -s dotglob; echo /home/ana/app > ~/?agent-toolkit/dev-repo",
        "a=.a; b=gent-toolkit; cp /tmp/record ~/$a$b/dev-repo",
        """python3 -c "open('/home/ana/' + '-'.join(['.agent', 'toolkit']) + '/dev-repo', 'w')" """,
        "cp /tmp/record ~/.State/DEV-REPO",
        "cp /tmp/record '/home/ana/.a'*/dev-repo",
    ])
    def test_bash_writes_naming_the_developer_mode_record_blocked(self, command):
        """However the folder is reached, a write that names the record's file is refused."""
        blocked, msg = check_protected_paths(_state(), "Bash", "", command)
        assert blocked is True, command
        assert "G-CONFIG-1" in msg

    @pytest.mark.parametrize("command", [
        "find ~/.agent-toolkit -name dev-repo -delete",
        "find ~/.agent-toolki? -name dev-repo -delete",
        "find ~/.agent-toolkit -type f -exec rm {} +",
        "find ~ -maxdepth 1 -name '.agent-t*' -execdir rm -rf {} +",
    ])
    def test_find_that_deletes_or_runs_a_command_there_blocked(self, command):
        """`find` is on the read-only list; with -delete or -exec it is not reading."""
        blocked, msg = check_protected_paths(_state(), "Bash", "", command)
        assert blocked is True, command
        assert "G-CONFIG-1" in msg

    @pytest.mark.parametrize("command", [
        "find ~/.agent-toolkit -name dev-repo",
        "find ~/.agent-toolkit -type f -newer gates.json",
        "find src -name '*.pyc' -delete",
        "find . -name '*.orig' -exec rm {} +",
    ])
    def test_find_that_only_looks_or_acts_elsewhere_allowed(self, command):
        blocked, _ = check_protected_paths(_state(), "Bash", "", command)
        assert blocked is False, command

    @pytest.mark.parametrize("command", [
        # a pattern that only looks like a glob for a dotted name
        "sed -i 's/.*//' notes.txt",
        "sed -i 's/=.*/=1/' .env",
        "sed 's/.*=//' .env > values.txt",
        "perl -pi -e 's/.*//' invoice.txt",
        "grep -o 'name=.*' packages.txt > names.txt",
        """python3 -c "import re; print(re.match(r'(.+): (.*)', 'total: 47.99'))" > parsed.txt""",
        "rsync -a --exclude='.*' src/ dest/",
        "tar czf site.tgz --exclude='.*' .",
        "ruff check --fix . --exclude '.*'",
        'echo ".*" >> .gitignore',
        "rm .??*",
        "cp -r .[!.]* /tmp/backup/",
        'git commit -m "ignore .* files" && git checkout main',
        # other dotted names, in the project and under the home folder
        "touch .agent-config.yml",
        "mkdir -p ~/.agents/skills",
        "rm ~/.cache/pip/*",
        "cp settings.toml ~/.config/$APP/",
        "echo 'export PATH=$HOME/.local/bin:$PATH' >> ~/.zshrc",
        "chmod 600 ~/.ssh/*",
        "rm -rf ~/.npm/_cacache/*",
    ])
    def test_ordinary_writes_with_dots_and_globs_allowed(self, command):
        blocked, _ = check_protected_paths(_state(), "Bash", "", command)
        assert blocked is False, command

    @pytest.mark.parametrize("command", [
        "mkdir ~/.agent-$USER", "touch ~/.$PROFILE", 'echo ".agent-*" >> .gitignore',
        """python3 -c "import os; os.makedirs('.agent')" """, "rm .a*",
    ])
    def test_a_name_that_could_become_the_folder_is_refused_even_when_it_would_not(self, command):
        """The cost of the rule: the text alone cannot rule the folder out, so the user is asked instead."""
        blocked, msg = check_protected_paths(_state(), "Bash", "", command)
        assert blocked is True, command
        assert "Ask the user" in msg

    @pytest.mark.parametrize("command", [
        # the record's file name is also an ordinary word
        "cd ~/src/dev-repo && npm test",
        "git checkout dev-repo && npm install",
        "docker build -t dev-repo .",
        "rm -rf /tmp/dev-repo",
        "make dev-repo",
        "kubectl apply -f k8s/ -n dev-repo",
        "cp notes.txt $WORK/dev-repo",
        "cp /tmp/record \"$TARGET/DEV-REPO\"",
        "rm -rf build/my-dev-repo",
        "rm -rf vendor/dev-repo.git",
        "echo started > dev-repo.log",
        # dotted names under the home folder that cannot become the folder
        "cp ~/.zshrc{,.bak}",
        "touch ~/.{bashrc,zshrc}",
        "cp ~/.gitconfig ~/.gitconfig.$(date +%F)",
        "export PATH=$HOME/.deno:$PATH && deno --version",
        "export GOPATH=$HOME/.go:$GOPATH && go build",
        "echo 'alias ll=\"ls -la\"' >> ~/.${SHELL##*/}rc",
        "scp host:/home/deploy/.env.$STAGE ./",
        "touch ~/.env.$STAGE",
        # names under the home folder that a variable or a glob fills in
        "mkdir -p ~/$PROJECT/src",
        "cp notes.md ~/${PROJECT}/docs/",
        "mkdir ~/$PROJECT-backup",
        "cp -r ~/* /Volumes/backup/",
        "rm ~/*.tmp",
        "find ~ -maxdepth 2 -name '*.orig' -delete",
        "find ~/Downloads -name '*' -mtime +30 -delete",
        # other names that start the same way
        """python3 -c "open('.agent-config','w').write('{}')" """,
        "touch .agent-lock; npm test",
        "touch ~/.agent; echo done",
        "mkdir -p .agent/rules && cp rules.md .agent/rules/",
        "mkdir .agents",
        "rm -rf .*.swp",
        "echo '.a*' >> .gitignore",
        "grep -o \".ag[a-z]*\" words.txt > found.txt",
        "rm .??*.bak",
        "(touch ~/.agent)",
        "(cd pkg && touch .agent-lock)",
        "cp .agent-rules.md{,.bak}",
        "rm .agent-cache/*",
    ])
    def test_writes_that_share_a_word_or_a_prefix_with_the_folder_allowed(self, command):
        blocked, _ = check_protected_paths(_state(), "Bash", "", command)
        assert blocked is False, command

    @pytest.mark.parametrize("command", [
        "echo $(rm -rf ~/.agent-toolkit)",
        "echo `rm -rf ~/.agent-toolki?`",
        "cat <(rm -rf ~/.agent-toolkit)",
        "sort -o ~/.agent-toolkit/dev-repo /etc/hosts",
        "sort --output=/home/ana/.agent-toolkit/dev-repo /etc/hosts",
        "git config -f ~/.agent-toolkit/dev-repo core.editor vim",
        """awk 'BEGIN{system("rm -rf ~/.agent-toolkit")}'""",
        "find ~/.agent-toolkit -name dev-repo -fprint /tmp/found",
        "find ~/.agent-toolkit -type f -fls /tmp/found",
    ])
    def test_read_only_commands_told_to_write_or_run_something_there_blocked(self, command):
        blocked, msg = check_protected_paths(_state(), "Bash", "", command)
        assert blocked is True, command
        assert "G-CONFIG-1" in msg

    @pytest.mark.parametrize("command", [
        "rm -rf ~//.a*",
        "rm -rf ~/./.a*",
        "rm -rf ${HOME}/.a*",
        "rm -rf /root/.a*",
        "rm -rf /home/ana/.a*",
        "rm -rf '/Users/ana/.a'*",
        "rm -rf ~/.agent-" + "?" * 7,
        "rm -rf \"$HOME\"/'.agent'-\"toolkit\"",
        "rm -rf '/home/ana'/.a*",
        "p=.agent-; s=toolkit; cd /Users/ana; rm -rf $p$s",
        "p=.agen; s=t-toolkit; cd /Users/ana; rm -rf $p$s",
        # every dotted name at once, under each spelling of the home folder
        "rm -rf ${HOME}/.*",
        "rm -rf /root/.??*",
        "rm -rf /home/ana/.[!.]*",
        "rm -rf \"$HOME\"/.*",
        "rm -rf '/home/ana'/.??*",
        "v=.agent-toolkitx; rm -rf ~/${v%x}",
        "v=.bgent-toolkit; rm -rf ~/${v/b/a}",
        "a=.a; b=gent-toolkit; rm -rf ~/$a$b",
        "shopt -s dotglob; rm -rf ~/?agent-toolkit",
        "shopt -s dotglob; rm -rf ~/*gent-toolkit",
        "find ~ -maxdepth 1 -name '*gent-toolkit' -exec rm -rf {} +",
        "find ~ -maxdepth 1 -name '?agent-toolkit' -exec cp /etc/hosts {}/flag \\;",
        "find /Users/ana -maxdepth 1 -iname '.AGENT*' -delete",
        # a glob with part of the name in it, wherever the command happens to be
        "cd ~ && rm -rf .a*",
        "cd && rm -rf .[a]gent?toolkit",
        "rm -rf $PWD/.a*",
        "rm -rf ./.ag*",
        "h=$HOME; rm -rf $h/.a*",
        "rm -rf $(echo ~)/.a*",
        "cd ~ && echo x > .agen?-toolkit/flag",
        "cd ~ && e= && echo x > .agent${e}-toolkit/flag",
        # code that cuts the name right after its start
        """python3 -c "import pathlib; (pathlib.Path.home()/('.agent' + '-toolkit')/'flag').write_text('x')" """,
        """python3 -c "import os; open(os.path.expanduser('~/' + '-'.join(['.agent','toolkit']) + '/flag'),'w')" """,
        """python3 -c "import pathlib; [p.joinpath('flag').write_text('x') for p in pathlib.Path.home().glob('.agen*')]" """,
        """node -e 'require("fs").writeFileSync(require("os").homedir()+"/.agent"+"-toolkit/flag","x")'""",
        "rm -rf ~/." + "a" * 200 + "*",
    ])
    def test_every_way_of_writing_the_home_folder_is_covered(self, command):
        blocked, msg = check_protected_paths(_state(), "Bash", "", command)
        assert blocked is True, command
        assert "G-CONFIG-1" in msg

    @pytest.mark.parametrize("command", [
        "a=" + "$a" * 40 + "; rm $a",
        "rm '" + " " * 50_000 + "+" + " " * 50_000 + "' notes.txt",
        "rm ~/." + "[" * 20_000 + "a" + "]" * 20_000,
        "rm " + "~/.a*/" * 10_000,
        "rm " + ".agent-" * 10_000,
        "rm " + "${" * 20_000 + "x" + "}" * 20_000,
        "rm .agent-" + "[" * 50_000,
        "rm ~/." + "[" * 50_000,
        "rm " + "{" * 50_000 + "/dev-repo",
        "rm " + "/users/" * 20_000,
        "rm ~/.a" + "{b,c}" * 30,
    ])
    def test_a_long_or_tangled_command_is_judged_at_once(self, command):
        """Nothing is expanded, so no command can make the check slow."""
        started = time.perf_counter()
        check_protected_paths(_state(), "Bash", "", command)

        assert time.perf_counter() - started < 1.0

    def test_disguise_check_follows_gate_protect(self):
        command = "echo /home/ana/app > ~/.agent-toolki?/dev-repo"
        blocked, _ = check_protected_paths(_state(gate_protect=False), "Bash", "", command)
        assert blocked is False

    def test_config_protection_follows_gate_protect(self):
        blocked, _ = check_protected_paths(_state(gate_protect=False), "Write", "/home/ana/app/gates.json", "")
        assert blocked is False


class TestSecretFiles:
    """Signing and flag keys must never reach the agent, not even through Read."""

    @pytest.mark.parametrize("path", [
        "/home/ana/app/.gate/signing.key",
        "/home/ana/app/.gate/private.pem",
        "/home/ana/.agent-toolkit/flag.key",
        "/home/ana/app/.session/state.json",
    ])
    def test_read_of_secret_files_blocked(self, path):
        blocked, msg = check_protected_paths(_state(), "Read", path, "")
        assert blocked is True, path
        assert "secret" in msg.lower() or "hook-managed" in msg

    @pytest.mark.parametrize("path", [
        "/home/ana/app/.gates/precommit-passed",
        "/home/ana/app/reports/precommit/pc_login_1a2b3c4d.md",
        "/home/ana/app/.gate/signing.meta.json",
        "/home/ana/app/src/billing/invoice.py",
    ])
    def test_read_of_non_secret_files_allowed(self, path):
        blocked, _ = check_protected_paths(_state(), "Read", path, "")
        assert blocked is False, path

    @pytest.mark.parametrize("command", [
        "cat .gate/signing.key",
        "python3 -c 'print(open(\".gate/signing.key\").read())'",
        "cat ~/.agent-toolkit/flag.key",
        "base64 /home/ana/.agent-toolkit/flag.key",
        "cp .gate/signing.key /tmp/k",
    ])
    def test_bash_access_to_secret_files_blocked(self, command):
        blocked, _ = check_protected_paths(_state(), "Bash", "", command)
        assert blocked is True, command

    @pytest.mark.parametrize("tool", ["Write", "Edit"])
    def test_write_to_key_dir_blocked(self, tool):
        blocked, _ = check_protected_paths(_state(), tool, "/home/ana/app/.gate/gate-token.jwt", "")
        assert blocked is True


class TestGateWritingTools:
    """stamp_skill is a forgery on hook-stamping hosts and the real path elsewhere."""

    STAMP_TOOL = "mcp__agent-toolkit__stamp_skill"

    def test_registry_names_stamp_tool(self):
        assert self.STAMP_TOOL in GATE_WRITING_TOOLS

    @pytest.mark.parametrize("tool_name", [
        "mcp__agent-toolkit__stamp_skill",
        "mcp__agent_toolkit__stamp_skill",
    ])
    def test_blocks_mcp_stamp_tool(self, tool_name):
        blocked, msg = check_protected_paths(_state(), tool_name, "", "", agent="claude-code")
        assert blocked is True
        assert "stamp" in msg.lower()
        assert "G-GATE-1" in msg

    def test_detects_claude_code_from_environment(self, monkeypatch):
        monkeypatch.setenv("CLAUDECODE", "1")
        monkeypatch.delenv("AGENT_TOOLKIT_TOOL", raising=False)
        blocked, _ = check_protected_paths(_state(), self.STAMP_TOOL, "", "")
        assert blocked is True

    @pytest.mark.parametrize("agent", ["cursor", "gemini", "codex-cli", "grok-build", "windsurf", "default"])
    def test_cli_stamp_hosts_may_call_stamp_tool(self, agent):
        """Cursor, Gemini, Codex, Grok, Windsurf have no Skill hook — cli stamps are legitimate."""
        blocked, _ = check_protected_paths(_state(), self.STAMP_TOOL, "", "", agent=agent)
        assert blocked is False

    def test_gate_protect_off_allows_mcp_stamp_tool(self):
        blocked, _ = check_protected_paths(
            _state(gate_protect=False), self.STAMP_TOOL, "", "", agent="claude-code"
        )
        assert blocked is False

    def test_other_mcp_tools_allowed(self):
        blocked, _ = check_protected_paths(
            _state(), "mcp__agent-toolkit__get_skill", "", "", agent="claude-code"
        )
        assert blocked is False
