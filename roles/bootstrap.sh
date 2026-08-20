#!/usr/bin/env bash
#
# Bootstrap role knowledge — indexes all repos for all starter roles
# and synthesizes knowledge. Run once, then remove your API key.
#
# Usage:
#   ANTHROPIC_API_KEY=sk-ant-... bash roles/bootstrap.sh
#
# What it does:
#   1. For each starter role (backend, frontend, dba, security, infrastructure, production)
#   2. Reads repos.json for that role
#   3. Clones each repo (shallow, cached)
#   4. Extracts key files (Python heuristics, no LLM)
#   5. Studies each repo through the role's lens (LLM call — this costs money)
#   6. Synthesizes all learnings into _synthesis.md (LLM call — Opus)
#
# Cost estimate: ~$12-15 for all 6 roles (30 repos total)
# Time estimate: ~15-30 minutes (depends on clone speed + API latency)
#
# After running:
#   - Each role has roles/{role}/knowledge/_synthesis.md ready for runtime
#   - unset ANTHROPIC_API_KEY (or close terminal)
#

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LEARN_PY="$SCRIPT_DIR/learn.py"
CACHE_DIR="$SCRIPT_DIR/.learn-cache"

# Check API key — prompt securely if not set
if [ -z "${ANTHROPIC_API_KEY:-}" ]; then
    echo "ANTHROPIC_API_KEY is not set."
    echo ""
    echo "Option 1 (secure — key not in shell history):"
    echo "  read -s -p 'Paste API key: ' ANTHROPIC_API_KEY && export ANTHROPIC_API_KEY"
    echo "  bash roles/bootstrap.sh"
    echo ""
    echo "Option 2 (quick):"
    echo "  export ANTHROPIC_API_KEY=sk-ant-..."
    echo "  bash roles/bootstrap.sh"
    echo ""
    echo "Get your key from: https://console.anthropic.com/settings/keys"
    exit 1
fi

# Check Python
if ! command -v python3 &>/dev/null; then
    echo "ERROR: python3 not found"
    exit 1
fi

# Check httpx
if ! python3 -c "import httpx" 2>/dev/null; then
    echo "Installing httpx..."
    pip3 install httpx --quiet
fi

ROLES=(
    "backend" "frontend" "dba" "security" "infrastructure" "production"
    "ios" "android" "data-engineer" "data-scientist" "ai-ml"
    "qa" "architect" "code-health" "requirements-eng" "research"
    "game-dev" "embedded" "legal"
)

echo "========================================="
echo "  Role Knowledge Bootstrap"
echo "========================================="
echo ""
echo "Roles to index: ${ROLES[*]}"
echo "Cache directory: $CACHE_DIR"
echo ""

total_repos=0
total_roles=${#ROLES[@]}
current_role=0

for role in "${ROLES[@]}"; do
    current_role=$((current_role + 1))
    repos_file="$SCRIPT_DIR/$role/repos.json"

    if [ ! -f "$repos_file" ]; then
        echo "[$current_role/$total_roles] SKIP $role — no repos.json"
        continue
    fi

    # Count repos
    repo_count=$(python3 -c "import json; print(len(json.load(open('$repos_file'))))")
    echo ""
    echo "[$current_role/$total_roles] === $role ($repo_count repos) ==="
    echo ""

    # Study each repo
    repo_index=0
    python3 -c "
import json, sys
repos = json.load(open('$repos_file'))
for r in repos:
    print(r['url'])
" | while read -r repo_url; do
        repo_index=$((repo_index + 1))
        total_repos=$((total_repos + 1))
        repo_name=$(basename "$repo_url")
        echo "  [$repo_index/$repo_count] Studying $repo_name as $role..."

        if python3 "$LEARN_PY" \
            --role "$role" \
            --repo "$repo_url" \
            --cache-dir "$CACHE_DIR" 2>&1 | sed 's/^/    /'; then
            echo "  [$repo_index/$repo_count] ✓ $repo_name done"
        else
            echo "  [$repo_index/$repo_count] ✗ $repo_name FAILED (continuing...)"
        fi
        echo ""
    done

    # Study engineering blogs (if any for this role)
    blogs_file="$SCRIPT_DIR/blogs.json"
    if [ -f "$blogs_file" ]; then
        blog_urls=$(python3 -c "
import json, sys
blogs = json.load(open('$blogs_file'))
role_blogs = blogs.get('$role', [])
for b in role_blogs:
    print(b['url'])
" 2>/dev/null)

        if [ -n "$blog_urls" ]; then
            echo "$blog_urls" | while read -r blog_url; do
                blog_name=$(python3 -c "
import json
blogs = json.load(open('$blogs_file'))
for b in blogs.get('$role', []):
    if b['url'] == '$blog_url':
        print(b['name']); break
")
                echo "  [blog] Studying $blog_name..."
                if python3 "$LEARN_PY" \
                    --role "$role" \
                    --url "$blog_url" \
                    --cache-dir "$CACHE_DIR" 2>&1 | sed 's/^/    /'; then
                    echo "  [blog] ✓ $blog_name done"
                else
                    echo "  [blog] ✗ $blog_name FAILED (continuing...)"
                fi
            done
        fi
    fi

    # Synthesize
    echo "  Synthesizing $role knowledge..."
    if python3 "$LEARN_PY" \
        --role "$role" \
        --synthesize 2>&1 | sed 's/^/    /'; then
        echo "  ✓ $role synthesis complete"
    else
        echo "  ✗ $role synthesis FAILED"
    fi
done

echo ""
echo "========================================="
echo "  Bootstrap Complete"
echo "========================================="
echo ""
echo "Knowledge files created:"
for role in "${ROLES[@]}"; do
    synthesis="$SCRIPT_DIR/$role/knowledge/_synthesis.md"
    if [ -f "$synthesis" ]; then
        size=$(wc -c < "$synthesis" | tr -d ' ')
        echo "  ✓ $role — _synthesis.md (${size} bytes)"
    else
        echo "  ✗ $role — NO synthesis generated"
    fi
done

echo ""
echo "Cleaning up cloned repos to free disk space..."
if [ -d "$CACHE_DIR" ]; then
    cache_size=$(du -sh "$CACHE_DIR" 2>/dev/null | cut -f1)
    rm -rf "$CACHE_DIR"
    echo "  ✓ Removed $CACHE_DIR ($cache_size freed)"
fi

echo ""
echo "Next steps:"
echo "  1. unset ANTHROPIC_API_KEY  (remove your key)"
echo "  2. Review: cat roles/backend/knowledge/_synthesis.md"
echo "  3. Health check: python3 roles/learn.py --health backend"
echo ""
echo "The role system is now active. Start a new session and roles"
echo "will be auto-detected and injected into your workflow."
