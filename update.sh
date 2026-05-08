#!/usr/bin/env bash
# update.sh — Pull latest and symlink any new skills/agents/shared files
# Called automatically by the PreToolUse hook before every skill invocation

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# Pull latest
git -C "$SCRIPT_DIR" pull --ff-only 2>/dev/null || exit 0

# Symlink any new skill directories
for skill_dir in "$SCRIPT_DIR"/skills/*/; do
    [ -d "$skill_dir" ] || continue
    skill_name="$(basename "$skill_dir")"
    dest="$HOME/.claude/skills/$skill_name"
    [ -L "$dest" ] || ln -s "$skill_dir" "$dest" 2>/dev/null
done

# Symlink any new agent files
for agent_file in "$SCRIPT_DIR"/agents/*.md; do
    [ -f "$agent_file" ] || continue
    filename="$(basename "$agent_file")"
    dest="$HOME/.claude/agents/$filename"
    [ -L "$dest" ] || ln -s "$agent_file" "$dest" 2>/dev/null
done

# Symlink any new shared files
mkdir -p "$HOME/.claude/shared"
for shared_file in "$SCRIPT_DIR"/shared/*.md; do
    [ -f "$shared_file" ] || continue
    filename="$(basename "$shared_file")"
    dest="$HOME/.claude/shared/$filename"
    [ -L "$dest" ] || ln -s "$shared_file" "$dest" 2>/dev/null
done
