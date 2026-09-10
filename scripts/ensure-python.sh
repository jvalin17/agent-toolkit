#!/usr/bin/env bash
# ensure-python.sh — Find Python >=3.10, create MCP venv if needed.
#
# Usage:
#   source scripts/ensure-python.sh          # sets TOOLKIT_PYTHON
#   scripts/ensure-python.sh --check         # exits 0 if python >=3.10 found
#   scripts/ensure-python.sh --venv          # creates .venv-mcp with fastmcp
#   scripts/ensure-python.sh --print         # prints path to best python

set -e

TOOLKIT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
MIN_VERSION=10  # 3.10

find_best_python() {
    # Try versioned binaries first (most specific), then generic python3
    for candidate in python3.13 python3.12 python3.11 python3.10 python3; do
        if command -v "$candidate" &>/dev/null; then
            minor=$("$candidate" -c "import sys; print(sys.version_info.minor)" 2>/dev/null || echo "0")
            if [ "$minor" -ge "$MIN_VERSION" ]; then
                echo "$candidate"
                return 0
            fi
        fi
    done
    return 1
}

ensure_venv() {
    local py="$1"
    local venv_dir="$TOOLKIT_DIR/.venv-mcp"

    if [ -f "$venv_dir/bin/python" ]; then
        # Venv exists — check if fastmcp is installed
        if "$venv_dir/bin/python" -c "import fastmcp" 2>/dev/null; then
            echo "$venv_dir/bin/python"
            return 0
        fi
    fi

    echo "  Creating MCP venv with $py..." >&2
    "$py" -m venv "$venv_dir" 2>/dev/null || {
        echo "  ✗ Failed to create venv. Install python3.10+ with venv support." >&2
        return 1
    }

    echo "  Installing fastmcp..." >&2
    "$venv_dir/bin/pip" install --quiet "fastmcp>=2.0,<3.0" 2>/dev/null || {
        # Try with --only-binary if build fails
        "$venv_dir/bin/pip" install --quiet --only-binary :all: "fastmcp>=2.0,<3.0" 2>/dev/null || {
            echo "  ✗ Failed to install fastmcp." >&2
            return 1
        }
    }

    echo "$venv_dir/bin/python"
}

# --- Main ---
BEST_PYTHON=$(find_best_python || true)

case "${1:-}" in
    --check)
        if [ -n "$BEST_PYTHON" ]; then
            exit 0
        else
            echo "Python >=3.10 not found. MCP server requires Python 3.10+." >&2
            echo "Install: brew install python@3.12  (macOS)" >&2
            echo "         apt install python3.12     (Ubuntu/Debian)" >&2
            exit 1
        fi
        ;;
    --venv)
        if [ -z "$BEST_PYTHON" ]; then
            echo "Python >=3.10 not found. Skipping MCP venv setup." >&2
            exit 1
        fi
        ensure_venv "$BEST_PYTHON"
        ;;
    --print)
        if [ -n "$BEST_PYTHON" ]; then
            echo "$BEST_PYTHON"
        else
            echo "python3"  # fallback, will fail at runtime
        fi
        ;;
    *)
        # Sourced — export TOOLKIT_PYTHON
        export TOOLKIT_PYTHON="${BEST_PYTHON:-python3}"
        ;;
esac
