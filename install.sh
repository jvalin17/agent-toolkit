#!/bin/bash
# install.sh — Install agent-toolkit skills and agents into ~/.claude/ for global access
#
# Skills go to:  ~/.claude/skills/
# Agents go to:  ~/.claude/agents/
# Old commands:  ~/.claude/commands/ (cleaned up if migrated)

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SKILLS_SRC="$SCRIPT_DIR/skills"
AGENTS_SRC="$SCRIPT_DIR/agents"
SHARED_SRC="$SCRIPT_DIR/shared"
OLD_COMMANDS_SRC="$SCRIPT_DIR/commands"

SKILLS_DEST="$HOME/.claude/skills"
AGENTS_DEST="$HOME/.claude/agents"
SHARED_DEST="$HOME/.claude/shared"
OLD_COMMANDS_DEST="$HOME/.claude/commands"

installed=0
skipped=0
cleaned=0

# --- Helper ---
link_item() {
    local src="$1"
    local dest="$2"
    local name="$3"
    local type="$4"  # "file" or "dir"

    if [ "$type" = "dir" ]; then
        if [ -L "$dest" ]; then
            current="$(readlink "$dest")"
            if [ "$current" = "$src" ]; then
                echo "  [skip] $name (already linked)"
                skipped=$((skipped + 1))
                return
            fi
            rm "$dest"
        elif [ -d "$dest" ]; then
            echo "  [warn] $name exists as directory. Replace with symlink? (y/n)"
            read -r answer
            [ "$answer" != "y" ] && { skipped=$((skipped + 1)); return; }
            rm -rf "$dest"
        fi
        ln -s "$src" "$dest"
    else
        if [ -L "$dest" ]; then
            current="$(readlink "$dest")"
            if [ "$current" = "$src" ]; then
                echo "  [skip] $name (already linked)"
                skipped=$((skipped + 1))
                return
            fi
            rm "$dest"
        elif [ -f "$dest" ]; then
            echo "  [warn] $name exists as file. Replace? (y/n)"
            read -r answer
            [ "$answer" != "y" ] && { skipped=$((skipped + 1)); return; }
            mv "$dest" "${dest}.bak"
        fi
        ln -s "$src" "$dest"
    fi
    echo "  [installed] $name"
    installed=$((installed + 1))
}

# --- Install Skills ---
echo "Installing skills..."
mkdir -p "$SKILLS_DEST"

for skill_dir in "$SKILLS_SRC"/*/; do
    [ -d "$skill_dir" ] || continue
    skill_name="$(basename "$skill_dir")"
    link_item "$skill_dir" "$SKILLS_DEST/$skill_name" "$skill_name" "dir"
done

# --- Install Agents ---
echo ""
echo "Installing agents..."
mkdir -p "$AGENTS_DEST"

for agent_file in "$AGENTS_SRC"/*.md; do
    [ -f "$agent_file" ] || continue
    filename="$(basename "$agent_file")"
    link_item "$agent_file" "$AGENTS_DEST/$filename" "$filename" "file"
done

# --- Install Shared Files ---
echo ""
echo "Installing shared files..."
mkdir -p "$SHARED_DEST"

for shared_file in "$SHARED_SRC"/*.md; do
    [ -f "$shared_file" ] || continue
    filename="$(basename "$shared_file")"
    link_item "$shared_file" "$SHARED_DEST/$filename" "$filename" "file"
done

# --- Clean up old commands that migrated to skills ---
echo ""
echo "Checking for old commands to clean up..."

if [ -L "$OLD_COMMANDS_DEST/requirements.md" ]; then
    old_target="$(readlink "$OLD_COMMANDS_DEST/requirements.md")"
    if echo "$old_target" | grep -q "agent-toolkit"; then
        rm "$OLD_COMMANDS_DEST/requirements.md"
        echo "  [cleaned] commands/requirements.md (migrated to skill)"
        cleaned=$((cleaned + 1))
    fi
fi

# --- Install hooks ---
echo ""
echo "Setting up hooks..."

SETTINGS_FILE="$HOME/.claude/settings.json"
HOOKS_SRC="$SCRIPT_DIR/hooks"

install_hooks() {
    local toolkit_path="$SCRIPT_DIR"
    local update_command="$toolkit_path/update.sh 2>/dev/null || true"
    local gate_cmd="python3 $toolkit_path/hooks/gate.py"
    local skill_passed_cmd="python3 $toolkit_path/hooks/skill_passed.py"
    local gate_cleanup_cmd="python3 $toolkit_path/hooks/gate_cleanup.py"
    local route_cmd="python3 $toolkit_path/hooks/route_to_skill.py"
    local session_init_cmd="python3 $toolkit_path/hooks/session_init.py"
    local tdd_cmd="python3 $toolkit_path/hooks/tdd_enforce.py"
    local monitor_cmd="python3 $toolkit_path/hooks/session_monitor.py"
    local doc_guard_cmd="bash $toolkit_path/hooks/check_doc_write.sh"

    if [ ! -f "$SETTINGS_FILE" ]; then
        cat > "$SETTINGS_FILE" << HOOKEOF
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Skill",
        "hooks": [
          {
            "type": "command",
            "command": "$update_command",
            "timeout": 10,
            "statusMessage": "Checking for toolkit updates..."
          }
        ]
      },
      {
        "matcher": "Bash",
        "hooks": [
          {
            "type": "command",
            "command": "$gate_cmd",
            "timeout": 5,
            "statusMessage": "Checking quality gates..."
          }
        ]
      },
      {
        "matcher": "Edit|Write",
        "hooks": [
          {
            "type": "command",
            "command": "$tdd_cmd",
            "timeout": 5
          }
        ]
      },
      {
        "matcher": "Write",
        "hooks": [
          {
            "type": "command",
            "command": "$doc_guard_cmd",
            "timeout": 5,
            "statusMessage": "Checking write path..."
          }
        ]
      },
      {
        "matcher": "Bash|Write|Edit|Skill",
        "hooks": [
          {
            "type": "command",
            "command": "$monitor_cmd",
            "timeout": 5,
            "statusMessage": "Session monitor..."
          }
        ]
      }
    ],
    "PostToolUse": [
      {
        "matcher": "Skill",
        "hooks": [
          {
            "type": "command",
            "command": "$skill_passed_cmd",
            "timeout": 5
          }
        ]
      },
      {
        "matcher": "Bash",
        "hooks": [
          {
            "type": "command",
            "command": "$gate_cleanup_cmd",
            "timeout": 5
          }
        ]
      },
      {
        "matcher": "",
        "hooks": [
          {
            "type": "command",
            "command": "$monitor_cmd",
            "timeout": 5,
            "statusMessage": "Session monitor (post-tool)..."
          }
        ]
      }
    ],
    "PostCompact": [
      {
        "matcher": "",
        "hooks": [
          {
            "type": "command",
            "command": "$monitor_cmd",
            "timeout": 5,
            "statusMessage": "Session monitor (compact)..."
          }
        ]
      }
    ]
  }
}
HOOKEOF
        echo "  [installed] all hooks (created $SETTINGS_FILE)"

        # Add UserPromptSubmit and SessionStart hooks
        local tmp_file_fresh=$(mktemp)
        jq --arg route "$route_cmd" --arg init "$session_init_cmd" --arg monitor "$monitor_cmd" '
            .hooks.UserPromptSubmit = [{"matcher": "", "hooks": [{"type": "command", "command": $route, "timeout": 5}, {"type": "command", "command": $monitor, "timeout": 5}]}] |
            .hooks.SessionStart = [{"matcher": "startup", "hooks": [{"type": "command", "command": $init, "timeout": 5}]}, {"matcher": "compact", "hooks": [{"type": "command", "command": $init, "timeout": 5}]}]
        ' "$SETTINGS_FILE" > "$tmp_file_fresh" && mv "$tmp_file_fresh" "$SETTINGS_FILE"
        echo "  [installed] skill routing + session init + session monitor hooks"
        return
    fi

    # Merge hooks into existing settings — remove old hooks, add new ones
    local tmp_file=$(mktemp)

    # Remove old single-skill hooks if present
    jq '
        .hooks.PreToolUse = [(.hooks.PreToolUse // [])[] | select(.hooks | all(.command | (contains("precommit-gate") | not)))] |
        .hooks.PostToolUse = [(.hooks.PostToolUse // [])[] | select(.hooks | all(.command | ((contains("precommit-passed") | not) and (contains("post-commit-cleanup") | not))))]
    ' "$SETTINGS_FILE" > "$tmp_file" 2>/dev/null && mv "$tmp_file" "$SETTINGS_FILE"

    # Add/update auto-update hook
    if jq -e '.hooks.PreToolUse[]? | select(.hooks[]? | .command | contains("update.sh"))' "$SETTINGS_FILE" > /dev/null 2>&1; then
        jq --arg cmd "$update_command" '
            .hooks.PreToolUse = [.hooks.PreToolUse[]? | if (.hooks[]? | .command | contains("update.sh")) then .hooks = [.hooks[]? | if (.command | contains("update.sh")) then .command = $cmd else . end] else . end]
        ' "$SETTINGS_FILE" > "$tmp_file" && mv "$tmp_file" "$SETTINGS_FILE"
        echo "  [updated] auto-update hook"
    else
        jq --arg cmd "$update_command" '
            .hooks //= {} | .hooks.PreToolUse //= [] |
            .hooks.PreToolUse += [{"matcher": "Skill", "hooks": [{"type": "command", "command": $cmd, "timeout": 10, "statusMessage": "Checking for toolkit updates..."}]}]
        ' "$SETTINGS_FILE" > "$tmp_file" && mv "$tmp_file" "$SETTINGS_FILE"
        echo "  [installed] auto-update hook"
    fi

    # Migrate bash hooks → Python hooks
    local bash_py_migrations=(
        "gate.sh:gate.py:PreToolUse"
        "skill-passed.sh:skill_passed.py:PostToolUse"
        "gate-cleanup.sh:gate_cleanup.py:PostToolUse"
        "tdd-enforce.sh:tdd_enforce.py:PreToolUse"
        "route-to-skill.sh:route_to_skill.py:UserPromptSubmit"
    )
    for migration in "${bash_py_migrations[@]}"; do
        IFS=':' read -r old_name new_name event <<< "$migration"
        if jq -e ".hooks.${event}[]? | select(.hooks[]? | .command | contains(\"${old_name}\"))" "$SETTINGS_FILE" > /dev/null 2>&1; then
            local new_cmd="python3 $toolkit_path/hooks/$new_name"
            jq --arg old "$old_name" --arg new "$new_cmd" --arg evt "$event" '
                .hooks[($evt)] = [.hooks[($evt)][] | if (.hooks[]? | .command | contains($old)) then .hooks = [.hooks[] | if (.command | contains($old)) then .command = $new else . end] else . end]
            ' "$SETTINGS_FILE" > "$tmp_file" && mv "$tmp_file" "$SETTINGS_FILE"
            echo "  [migrated] $old_name → $new_name"
        fi
    done

    # Add gate hook
    if ! jq -e '.hooks.PreToolUse[]? | select(.hooks[]? | .command | contains("gate.py"))' "$SETTINGS_FILE" > /dev/null 2>&1; then
        jq --arg cmd "$gate_cmd" '
            .hooks.PreToolUse += [{"matcher": "Bash", "hooks": [{"type": "command", "command": $cmd, "timeout": 5, "statusMessage": "Checking quality gates..."}]}]
        ' "$SETTINGS_FILE" > "$tmp_file" && mv "$tmp_file" "$SETTINGS_FILE"
        echo "  [installed] quality gate hook (blocks commit/push without required skills)"
    else
        echo "  [skip] quality gate hook (already installed)"
    fi

    # Add skill-passed hook (replaces old precommit-passed)
    if ! jq -e '.hooks.PostToolUse[]? | select(.hooks[]? | .command | contains("skill_passed"))' "$SETTINGS_FILE" > /dev/null 2>&1; then
        jq --arg cmd "$skill_passed_cmd" '
            .hooks //= {} | .hooks.PostToolUse //= [] |
            .hooks.PostToolUse += [{"matcher": "Skill", "hooks": [{"type": "command", "command": $cmd, "timeout": 5}]}]
        ' "$SETTINGS_FILE" > "$tmp_file" && mv "$tmp_file" "$SETTINGS_FILE"
        echo "  [installed] skill-passed hook (tracks which skills have run)"
    else
        echo "  [skip] skill-passed hook (already installed)"
    fi

    # Add gate-cleanup hook (replaces old post-commit-cleanup)
    if ! jq -e '.hooks.PostToolUse[]? | select(.hooks[]? | .command | contains("gate_cleanup"))' "$SETTINGS_FILE" > /dev/null 2>&1; then
        jq --arg cmd "$gate_cleanup_cmd" '
            .hooks.PostToolUse += [{"matcher": "Bash", "hooks": [{"type": "command", "command": $cmd, "timeout": 5}]}]
        ' "$SETTINGS_FILE" > "$tmp_file" && mv "$tmp_file" "$SETTINGS_FILE"
        echo "  [installed] gate-cleanup hook (resets gates after commit)"
    else
        echo "  [skip] gate-cleanup hook (already installed)"
    fi

    # Add tdd-enforce hook (PreToolUse on Edit/Write)
    if ! jq -e '.hooks.PreToolUse[]? | select(.hooks[]? | .command | contains("tdd_enforce"))' "$SETTINGS_FILE" > /dev/null 2>&1; then
        jq --arg cmd "$tdd_cmd" '
            .hooks.PreToolUse += [{"matcher": "Edit|Write", "hooks": [{"type": "command", "command": $cmd, "timeout": 5}]}]
        ' "$SETTINGS_FILE" > "$tmp_file" && mv "$tmp_file" "$SETTINGS_FILE"
        echo "  [installed] TDD enforcement hook (reminds about test-first on source edits)"
    else
        echo "  [skip] TDD enforcement hook (already installed)"
    fi

    # Add doc-guard hook (PreToolUse on Write — blocks writes outside project dir)
    if ! jq -e '.hooks.PreToolUse[]? | select(.hooks[]? | .command | contains("check_doc_write"))' "$SETTINGS_FILE" > /dev/null 2>&1; then
        jq --arg cmd "$doc_guard_cmd" '
            .hooks.PreToolUse += [{"matcher": "Write", "hooks": [{"type": "command", "command": $cmd, "timeout": 5, "statusMessage": "Checking write path..."}]}]
        ' "$SETTINGS_FILE" > "$tmp_file" && mv "$tmp_file" "$SETTINGS_FILE"
        echo "  [installed] doc-guard hook (blocks writes outside project directory)"
    else
        echo "  [skip] doc-guard hook (already installed)"
    fi

    # Add route-to-skill hook (UserPromptSubmit)
    if ! jq -e '.hooks.UserPromptSubmit[]? | select(.hooks[]? | .command | contains("route_to_skill"))' "$SETTINGS_FILE" > /dev/null 2>&1; then
        jq --arg cmd "$route_cmd" '
            .hooks //= {} | .hooks.UserPromptSubmit //= [] |
            .hooks.UserPromptSubmit += [{"matcher": "", "hooks": [{"type": "command", "command": $cmd, "timeout": 5}]}]
        ' "$SETTINGS_FILE" > "$tmp_file" && mv "$tmp_file" "$SETTINGS_FILE"
        echo "  [installed] skill routing hook (detects intent, routes to correct skill)"
    else
        echo "  [skip] skill routing hook (already installed)"
    fi

    # Add session-monitor hook (PreToolUse on Bash|Write|Edit|Skill + UserPromptSubmit)
    if ! jq -e '.hooks.PreToolUse[]? | select(.hooks[]? | .command | contains("session_monitor"))' "$SETTINGS_FILE" > /dev/null 2>&1; then
        jq --arg cmd "$monitor_cmd" '
            .hooks.PreToolUse += [{"matcher": "Bash|Write|Edit|Skill", "hooks": [{"type": "command", "command": $cmd, "timeout": 5, "statusMessage": "Session monitor..."}]}]
        ' "$SETTINGS_FILE" > "$tmp_file" && mv "$tmp_file" "$SETTINGS_FILE"
        # Also add to UserPromptSubmit for exchange counting
        jq --arg cmd "$monitor_cmd" '
            .hooks //= {} | .hooks.UserPromptSubmit //= [] |
            .hooks.UserPromptSubmit = [.hooks.UserPromptSubmit[]? | .hooks += [{"type": "command", "command": $cmd, "timeout": 5}]]
        ' "$SETTINGS_FILE" > "$tmp_file" && mv "$tmp_file" "$SETTINGS_FILE"
        echo "  [installed] session monitor hook (tracks exchanges, enforces time/context limits)"
    else
        echo "  [skip] session monitor hook (already installed)"
    fi

    # Add session-monitor PostToolUse hook (byte tracking)
    if ! jq -e '.hooks.PostToolUse[]? | select(.hooks[]? | .command | contains("session_monitor"))' "$SETTINGS_FILE" > /dev/null 2>&1; then
        jq --arg cmd "$monitor_cmd" '
            .hooks //= {} | .hooks.PostToolUse //= [] |
            .hooks.PostToolUse += [{"matcher": "", "hooks": [{"type": "command", "command": $cmd, "timeout": 5, "statusMessage": "Session monitor (post-tool)..."}]}]
        ' "$SETTINGS_FILE" > "$tmp_file" && mv "$tmp_file" "$SETTINGS_FILE"
        echo "  [installed] session monitor PostToolUse hook (byte tracking)"
    else
        echo "  [skip] session monitor PostToolUse hook (already installed)"
    fi

    # Add session-monitor PostCompact hook (compaction detection)
    if ! jq -e '.hooks.PostCompact[]? | select(.hooks[]? | .command | contains("session_monitor"))' "$SETTINGS_FILE" > /dev/null 2>&1; then
        jq --arg cmd "$monitor_cmd" '
            .hooks //= {} | .hooks.PostCompact //= [] |
            .hooks.PostCompact += [{"matcher": "", "hooks": [{"type": "command", "command": $cmd, "timeout": 5, "statusMessage": "Session monitor (compact)..."}]}]
        ' "$SETTINGS_FILE" > "$tmp_file" && mv "$tmp_file" "$SETTINGS_FILE"
        echo "  [installed] session monitor PostCompact hook (compaction detection)"
    else
        echo "  [skip] session monitor PostCompact hook (already installed)"
    fi

    # Add session-init hook (SessionStart — startup + compact)
    if ! jq -e '.hooks.SessionStart[]? | select(.hooks[]? | .command | contains("session_init"))' "$SETTINGS_FILE" > /dev/null 2>&1; then
        jq --arg cmd "$session_init_cmd" '
            .hooks //= {} | .hooks.SessionStart //= [] |
            .hooks.SessionStart += [{"matcher": "startup", "hooks": [{"type": "command", "command": $cmd, "timeout": 5}]}, {"matcher": "compact", "hooks": [{"type": "command", "command": $cmd, "timeout": 5}]}]
        ' "$SETTINGS_FILE" > "$tmp_file" && mv "$tmp_file" "$SETTINGS_FILE"
        echo "  [installed] session init hook (loads toolkit rules at session start)"
    else
        echo "  [skip] session init hook (already installed)"
    fi
}

# Only install if jq is available (needed for safe JSON merging)
if command -v jq &> /dev/null; then
    install_hooks
else
    echo "  [skip] hooks (jq not installed — install jq for hook enforcement)"
fi

# --- Project gates bootstrap (auto — same install, no extra step) ---
if command -v python3 &> /dev/null; then
    "$SCRIPT_DIR/scripts/bootstrap-project-gates.sh" "$SCRIPT_DIR"
else
    echo ""
    echo "  [skip] project gates bootstrap (python3 required)"
fi

# --- agent-toolkit-continue entry point ---
echo ""
echo "Setting up agent-toolkit-continue..."
CONTINUE_SRC="$SCRIPT_DIR/scripts/agent-toolkit-continue"
LOCAL_BIN="$HOME/.local/bin"

if [ -x "$CONTINUE_SRC" ]; then
    if [ -d "$LOCAL_BIN" ] || mkdir -p "$LOCAL_BIN" 2>/dev/null; then
        # Clean up old claude-auto symlink if present
        if [ -L "$LOCAL_BIN/claude-auto" ]; then
            rm "$LOCAL_BIN/claude-auto"
            echo "  [removed] old claude-auto symlink"
        fi
        if [ -L "$LOCAL_BIN/agent-toolkit-continue" ]; then
            current="$(readlink "$LOCAL_BIN/agent-toolkit-continue")"
            if [ "$current" = "$CONTINUE_SRC" ]; then
                echo "  [skip] agent-toolkit-continue (already linked in $LOCAL_BIN)"
            else
                ln -sf "$CONTINUE_SRC" "$LOCAL_BIN/agent-toolkit-continue"
                echo "  [updated] agent-toolkit-continue → $LOCAL_BIN/agent-toolkit-continue"
            fi
        else
            ln -s "$CONTINUE_SRC" "$LOCAL_BIN/agent-toolkit-continue"
            echo "  [installed] agent-toolkit-continue → $LOCAL_BIN/agent-toolkit-continue"
        fi
        if ! echo "$PATH" | grep -q "$LOCAL_BIN"; then
            echo "  [note] Add $LOCAL_BIN to your PATH to use 'agent-toolkit-continue' directly"
        fi
    else
        echo "  [skip] agent-toolkit-continue symlink (could not create $LOCAL_BIN)"
        echo "  Run directly: python3 scripts/auto_continue.py"
    fi
else
    echo "  [skip] agent-toolkit-continue (script not found)"
fi

# --- agent-toolkit-setup entry point ---
echo ""
echo "Setting up agent-toolkit-setup..."
SETUP_SRC="$SCRIPT_DIR/scripts/agent-toolkit-setup"

if [ -x "$SETUP_SRC" ]; then
    if [ -d "$LOCAL_BIN" ] || mkdir -p "$LOCAL_BIN" 2>/dev/null; then
        if [ -L "$LOCAL_BIN/agent-toolkit-setup" ]; then
            current="$(readlink "$LOCAL_BIN/agent-toolkit-setup")"
            if [ "$current" = "$SETUP_SRC" ]; then
                echo "  [skip] agent-toolkit-setup (already linked in $LOCAL_BIN)"
            else
                ln -sf "$SETUP_SRC" "$LOCAL_BIN/agent-toolkit-setup"
                echo "  [updated] agent-toolkit-setup → $LOCAL_BIN/agent-toolkit-setup"
            fi
        else
            ln -s "$SETUP_SRC" "$LOCAL_BIN/agent-toolkit-setup"
            echo "  [installed] agent-toolkit-setup → $LOCAL_BIN/agent-toolkit-setup"
        fi
    else
        echo "  [skip] agent-toolkit-setup symlink (could not create $LOCAL_BIN)"
        echo "  Run directly: python3 scripts/setup_modes.py"
    fi
else
    echo "  [skip] agent-toolkit-setup (script not found)"
fi

# --- Summary ---
echo ""
echo "Done. Installed: $installed, Skipped: $skipped, Cleaned: $cleaned"
echo ""
echo "Skills available as slash commands:"
for skill_dir in "$SKILLS_SRC"/*/; do
    [ -d "$skill_dir" ] || continue
    echo "  /$(basename "$skill_dir")"
done
echo ""
echo "Sub-agents available for skills to spawn:"
for agent_file in "$AGENTS_SRC"/*.md; do
    [ -f "$agent_file" ] || continue
    echo "  $(basename "$agent_file" .md)"
done
