#!/bin/bash
# demo-modes.sh — Demonstrate all 4 agent-toolkit modes building the same Todo API
#
# Usage:
#   ./scripts/demo-modes.sh                    # run all 4 modes
#   ./scripts/demo-modes.sh quick              # run one mode
#   ./scripts/demo-modes.sh --dry-run          # show commands without running
#
# Each mode builds a Todo API in a separate directory under /tmp/agent-toolkit-demo/
# so you can compare the results side by side.

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
TOOLKIT_DIR="$(dirname "$SCRIPT_DIR")"
SETUP="$SCRIPT_DIR/setup_modes.py"
DEMO_ROOT="/tmp/agent-toolkit-demo"
GOAL="Build a Todo API with FastAPI. Create a main.py with CRUD endpoints (GET /todos, POST /todos, GET /todos/{id}, DELETE /todos/{id}). Use an in-memory list as storage. Include tests in test_main.py using pytest + httpx. Keep it simple."
DRY_RUN=0
MAX_BUDGET="1.00"

# --- Parse args ---
MODES_TO_RUN=()
while [ $# -gt 0 ]; do
    case "$1" in
        --dry-run) DRY_RUN=1; shift ;;
        --budget) MAX_BUDGET="$2"; shift 2 ;;
        quick|balanced|guarded|lockdown) MODES_TO_RUN+=("$1"); shift ;;
        -h|--help)
            echo "Usage: $0 [--dry-run] [--budget USD] [quick|balanced|guarded|lockdown]"
            echo ""
            echo "Runs all 4 modes by default. Specify mode names to run specific ones."
            echo "Results saved to /tmp/agent-toolkit-demo/<mode>/"
            exit 0
            ;;
        *) echo "Unknown arg: $1"; exit 1 ;;
    esac
done

# Default: all modes
if [ ${#MODES_TO_RUN[@]} -eq 0 ]; then
    MODES_TO_RUN=(quick balanced guarded lockdown)
fi

# --- Mode descriptions ---
describe_mode() {
    case "$1" in
        quick)    echo "No TDD, no routing, warnings only — just code" ;;
        balanced) echo "TDD + routing + commit gate — guided development" ;;
        guarded)  echo "Eval on push, 70m time limit — production quality" ;;
        lockdown) echo "Strict mode, all reviews, paranoid gates — full review" ;;
    esac
}

# --- Run one mode ---
run_mode() {
    local mode="$1"
    local project_dir="$DEMO_ROOT/$mode"
    local desc
    desc=$(describe_mode "$mode")

    echo ""
    echo "============================================"
    echo "  Mode: $mode"
    echo "  $desc"
    echo "============================================"
    echo ""

    # Clean and create project dir
    rm -rf "$project_dir"
    mkdir -p "$project_dir"

    # Apply preset
    echo "[1/3] Applying $mode preset..."
    python3 "$SETUP" --"$mode" --project-dir "$project_dir"

    # Copy toolkit install for hooks to work
    echo "[2/3] Bootstrapping project..."
    cp "$TOOLKIT_DIR/templates/gates.json" "$project_dir/gates.json" 2>/dev/null || true
    python3 "$SETUP" --"$mode" --project-dir "$project_dir" > /dev/null

    # Build command
    local cmd=(
        claude -p "$GOAL"
        --output-format json
        --dangerously-skip-permissions
        --max-budget-usd "$MAX_BUDGET"
    )

    if [ "$DRY_RUN" -eq 1 ]; then
        echo "[3/3] Would execute:"
        echo "  cd $project_dir && ${cmd[*]}"
        echo ""
        echo "  gates.json:"
        cat "$project_dir/gates.json" | python3 -c "
import sys,json
d=json.load(sys.stdin)
for k in ['tdd','skill_routing','enforcement','profile','mode','max_session_minutes','auto','model']:
    print(f'    {k}: {d.get(k, \"n/a\")}')
"
        return 0
    fi

    echo "[3/3] Running claude -p (budget: \$$MAX_BUDGET)..."
    echo ""

    cd "$project_dir"
    local start_time=$SECONDS

    if "${cmd[@]}" > output.json 2>&1; then
        local duration=$(( SECONDS - start_time ))
        echo ""
        echo "  Completed in ${duration}s"

        # Extract stats from JSON output
        if [ -f output.json ]; then
            python3 -c "
import json, sys
try:
    d = json.load(open('output.json'))
    print(f'  Turns: {d.get(\"num_turns\", \"?\")}')
    print(f'  Cost: \${d.get(\"total_cost_usd\", 0):.4f}')
    print(f'  Result: {d.get(\"result\", \"?\")[:100]}...')
except: pass
" 2>/dev/null
        fi

        # Check what files were created
        echo ""
        echo "  Files created:"
        find . -name "*.py" -not -path "./output.json" | sort | while read -r f; do
            lines=$(wc -l < "$f" | tr -d ' ')
            echo "    $f ($lines lines)"
        done
    else
        echo "  Session ended (non-zero exit)"
    fi

    cd "$TOOLKIT_DIR"
    echo ""
}

# --- Main ---
echo "=== Agent Toolkit Mode Demo ==="
echo "Goal: $GOAL"
echo "Modes: ${MODES_TO_RUN[*]}"
echo "Output: $DEMO_ROOT/<mode>/"
echo ""

for mode in "${MODES_TO_RUN[@]}"; do
    run_mode "$mode"
done

echo ""
echo "=== Demo Complete ==="
echo ""
echo "Compare results:"
for mode in "${MODES_TO_RUN[@]}"; do
    echo "  $DEMO_ROOT/$mode/"
done
echo ""
echo "Each directory has the generated code + gates.json showing the mode config."
