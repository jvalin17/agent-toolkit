# Agent Toolkit — Copy-Paste Install Prompt

Paste this into any AI coding session (Claude Code, Cursor, Gemini, Codex) to install or update the agent toolkit:

---

```
Check if agent-toolkit is installed. Look for these locations:
1. ~/.agent-toolkit/
2. ~/agent-toolkit/
3. ~/dev/agent-toolkit/

If found: run "cd <path> && git pull && ./install.sh --sync-only" to update.
If not found: run "git clone --depth 1 https://github.com/jvalin17/agent-toolkit.git ~/.agent-toolkit && cd ~/.agent-toolkit && ./install.sh"

After install/update, run: python3 ~/.agent-toolkit/roles/context.py --setup
Then tell me which roles were detected and what version is installed (git log --oneline -1 from the toolkit dir).
```

---

That's it. Works in any AI tool that can run terminal commands.
