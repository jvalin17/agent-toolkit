#!/usr/bin/env bash
#
# Bootstrap foundational SE book knowledge into roles.
# Studies open-source notes/summaries from GitHub — not copyrighted books.
#
# Usage:
#   ANTHROPIC_API_KEY=sk-ant-... bash roles/bootstrap-books.sh
#
# Cost: ~$3-4 total
# Time: ~15-20 minutes
#

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LEARN_PY="$SCRIPT_DIR/learn.py"
CACHE_DIR="$SCRIPT_DIR/.learn-cache"

if [ -z "${ANTHROPIC_API_KEY:-}" ]; then
    echo "ANTHROPIC_API_KEY not set."
    echo "  read -s -p 'API key: ' ANTHROPIC_API_KEY && export ANTHROPIC_API_KEY"
    echo "  bash roles/bootstrap-books.sh"
    exit 1
fi

echo "========================================="
echo "  Book Knowledge Bootstrap"
echo "========================================="
echo ""

study() {
    local role="$1" repo="$2" name="$3"
    echo "  [$role] Studying $name..."
    if python3 "$LEARN_PY" --role "$role" --repo "$repo" --cache-dir "$CACHE_DIR" 2>&1 | sed 's/^/    /'; then
        echo "  [$role] ✓ $name"
    else
        echo "  [$role] ✗ $name FAILED (continuing...)"
    fi
}

synth() {
    local role="$1"
    echo "  Synthesizing $role..."
    python3 "$LEARN_PY" --role "$role" --synthesize 2>&1 | sed 's/^/    /'
}

echo "--- DDIA (Kleppmann) → architect, dba, data-engineer ---"
study architect "https://github.com/YZXBiz/ddia" "DDIA notes"
study dba "https://github.com/YZXBiz/ddia" "DDIA notes"
study data-engineer "https://github.com/YZXBiz/ddia" "DDIA notes"

echo ""
echo "--- Clean Architecture (Robert Martin) → architect, backend ---"
study architect "https://github.com/serodriguez68/clean-architecture" "Clean Architecture notes"
study backend "https://github.com/serodriguez68/clean-architecture" "Clean Architecture notes"

echo ""
echo "--- Clean Code (Robert Martin) → backend, code-health ---"
study backend "https://github.com/JuanCrg90/Clean-Code-Notes" "Clean Code notes"
study code-health "https://github.com/JuanCrg90/Clean-Code-Notes" "Clean Code notes"

echo ""
echo "--- GoF Design Patterns → backend, frontend ---"
study backend "https://github.com/mutasim77/design-patterns" "GoF patterns (TypeScript)"
study frontend "https://github.com/mutasim77/design-patterns" "GoF patterns (TypeScript)"

echo ""
echo "--- Engineering Principles → architect ---"
study architect "https://github.com/castorm/engineering-principles" "SE principles collection"

echo ""
echo "--- DDIA 2nd ed references → architect ---"
study architect "https://github.com/ept/ddia2-references" "DDIA 2nd ed references"

echo ""
echo "--- QA / Testing → qa, production ---"
study qa "https://github.com/goldbergyoni/javascript-testing-best-practices" "JS Testing Best Practices"
study qa "https://github.com/testjavascript/nodejs-integration-tests-best-practices" "Node.js Integration Testing"
study production "https://github.com/goldbergyoni/javascript-testing-best-practices" "JS Testing Best Practices"

echo ""
echo "--- Security → security ---"
study security "https://github.com/OWASP/CheatSheetSeries" "OWASP Cheat Sheets"
study security "https://github.com/paragonie/awesome-appsec" "Awesome AppSec"

echo ""
echo "--- iOS → ios ---"
study ios "https://github.com/vsouza/awesome-ios" "Awesome iOS"
study ios "https://github.com/ochococo/Design-Patterns-In-Swift" "GoF Patterns in Swift"

echo ""
echo "--- Android → android ---"
study android "https://github.com/nicehash/Android-Architecture-Samples" "Android Architecture"
study android "https://github.com/dbacinski/Design-Patterns-In-Kotlin" "Design Patterns in Kotlin"

echo ""
echo "--- Data Science → data-scientist ---"
study data-scientist "https://github.com/jakevdp/PythonDataScienceHandbook" "Python Data Science Handbook"

echo ""
echo "--- AI/ML → ai-ml ---"
study ai-ml "https://github.com/huggingface/cookbook" "HuggingFace Cookbook"

echo ""
echo "--- Infrastructure → infrastructure ---"
study infrastructure "https://github.com/bregman-arie/devops-exercises" "DevOps Exercises"

echo ""
echo "--- Research → research ---"
study research "https://github.com/papers-we-love/papers-we-love" "Papers We Love"

echo ""
echo "--- Embedded → embedded ---"
study embedded "https://github.com/nhivp/Awesome-Embedded" "Awesome Embedded"

echo ""
echo "--- Game Dev → game-dev ---"
study game-dev "https://github.com/miloyip/game-programmer" "Game Programmer Study Path"

echo ""
echo "--- Legal → legal ---"
study legal "https://github.com/github/choosealicense.com" "Choose A License"

echo ""
echo "--- Requirements → requirements-eng ---"
study requirements-eng "https://github.com/joelparkerhenderson/architecture-decision-record" "ADR examples"

echo ""
echo "========================================="
echo "  Re-synthesizing ALL updated roles"
echo "========================================="
echo ""

for role in architect backend dba data-engineer code-health frontend qa production security ios android data-scientist ai-ml infrastructure research embedded game-dev legal requirements-eng; do
    synth "$role"
done

echo ""
echo "Updating knowledge.json..."
python3 -c "
import json
from pathlib import Path

roles_dir = Path('$SCRIPT_DIR')
knowledge = {}

# Load existing knowledge.json
kj = roles_dir / 'knowledge.json'
if kj.is_file():
    knowledge = json.loads(kj.read_text())

# Update from fresh synthesis files
for role_dir in sorted(roles_dir.iterdir()):
    synthesis = role_dir / 'knowledge' / '_synthesis.md'
    if synthesis.is_file():
        content = synthesis.read_text()
        if content.startswith('---'):
            parts = content.split('---', 2)
            if len(parts) >= 3:
                content = parts[2].strip()
        knowledge[role_dir.name] = content
        print(f'  ✓ {role_dir.name} updated in knowledge.json')

kj.write_text(json.dumps(knowledge, indent=2))
print(f'  Written {len(knowledge)} roles to knowledge.json')
"

echo ""
echo "Cleaning up..."
rm -rf "$CACHE_DIR" 2>/dev/null && echo "✓ Cache cleaned"

echo ""
echo "========================================="
echo "  Book Bootstrap Complete"
echo "========================================="
echo ""
echo "Updated all 19 roles with foundational book knowledge."
echo ""
echo "Run: python3 roles/learn.py --health architect"
echo "Then update knowledge.json: python3 -c \"..."
echo ""
