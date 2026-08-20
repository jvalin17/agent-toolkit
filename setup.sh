#!/usr/bin/env bash
#
# One-command setup for any AI coding tool.
#
# Usage (in your project directory):
#   curl -s https://raw.githubusercontent.com/jvalin17/agent-toolkit/main/setup.sh | bash
#
# Or if already cloned:
#   bash /path/to/agent-toolkit/setup.sh
#
# What it does:
#   1. Clones agent-toolkit (if not already present)
#   2. Detects your AI tool (Claude, Cursor, Gemini, Codex, etc.)
#   3. Writes the right config file with role context
#   4. Done — your AI agent now has 19 specialized roles
#

set -e

echo ""
echo "  Agent Toolkit — Setup"
echo "  ====================="
echo ""

# Find or clone the toolkit
TOOLKIT_DIR=""

# Check if this script is inside the toolkit
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}" 2>/dev/null)" && pwd 2>/dev/null || echo "")"
if [ -f "$SCRIPT_DIR/roles/context.py" ]; then
    TOOLKIT_DIR="$SCRIPT_DIR"
fi

# Check common locations
if [ -z "$TOOLKIT_DIR" ]; then
    for dir in "$HOME/agent-toolkit" "$HOME/dev/agent-toolkit" "$HOME/.agent-toolkit"; do
        if [ -f "$dir/roles/context.py" ]; then
            TOOLKIT_DIR="$dir"
            break
        fi
    done
fi

# Clone if not found
if [ -z "$TOOLKIT_DIR" ]; then
    TOOLKIT_DIR="$HOME/.agent-toolkit"
    echo "  Downloading agent-toolkit..."
    git clone --depth 1 https://github.com/jvalin17/agent-toolkit.git "$TOOLKIT_DIR" 2>/dev/null
    echo "  ✓ Downloaded to $TOOLKIT_DIR"
fi

# Check Python
if ! command -v python3 &>/dev/null; then
    echo "  ✗ python3 not found. Install Python 3 first."
    exit 1
fi

# Run context.py --setup
PROJECT_DIR="$(pwd)"
echo "  Project: $PROJECT_DIR"
echo ""

result=$(python3 "$TOOLKIT_DIR/roles/context.py" --setup "$PROJECT_DIR" 2>&1)
echo "  $result"

echo ""
echo "  ✓ Done! Your AI agent now has 19 specialized roles."
echo ""
echo "  Just start coding — roles activate automatically."
echo "  The agent knows backend, frontend, security, database,"
echo "  infrastructure, testing, and 13 more specializations."
echo ""
echo "  Try asking your AI agent:"
echo "    'Build a login page with email and password'"
echo "    'Fix the slow database query'"
echo "    'Add dark mode to the app'"
echo ""
