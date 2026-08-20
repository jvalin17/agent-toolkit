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

BOOKS_DIR="$SCRIPT_DIR/books"

study() {
    local role="$1" repo="$2" name="$3"
    echo "  [$role] Studying $name..."
    # Store in roles/{role}/books/ instead of roles/{role}/knowledge/
    local book_dir="$SCRIPT_DIR/$role/books"
    mkdir -p "$book_dir"
    if python3 "$LEARN_PY" --role "$role" --repo "$repo" --cache-dir "$CACHE_DIR" 2>&1 | sed 's/^/    /'; then
        # Move the knowledge file from knowledge/ to books/
        local slug=$(python3 -c "from learn import slug; print(slug('$repo'))")
        local src="$SCRIPT_DIR/$role/knowledge/${slug}.md"
        local dst="$book_dir/${slug}.md"
        if [ -f "$src" ]; then
            mv "$src" "$dst"
        fi
        echo "  [$role] ✓ $name → books/"
    else
        echo "  [$role] ✗ $name FAILED (continuing...)"
    fi
}

synth_books() {
    local role="$1"
    echo "  Synthesizing $role books..."
    # Synthesize only from books/ directory into _books_synthesis.md
    local book_dir="$SCRIPT_DIR/$role/books"
    if [ ! -d "$book_dir" ] || [ -z "$(ls "$book_dir"/*.md 2>/dev/null)" ]; then
        echo "    No book knowledge for $role — skipping"
        return
    fi
    python3 -c "
import sys
sys.path.insert(0, '$SCRIPT_DIR')
from learn import call_llm
from pathlib import Path
import os, json
from datetime import datetime

role = '$role'
book_dir = Path('$book_dir')
files = sorted(book_dir.glob('*.md'))
files = [f for f in files if f.name != '_books_synthesis.md']
if not files:
    print('  No book files to synthesize')
    sys.exit(0)

all_knowledge = ''
for f in files:
    all_knowledge += f'\n\n--- SOURCE: {f.stem} ---\n\n'
    all_knowledge += f.read_text()

role_md = Path('$SCRIPT_DIR/$role/role.md')
scope = '$role'
if role_md.is_file():
    content = role_md.read_text()
    if content.startswith('---'):
        for line in content.split('---', 2)[1].split('\n'):
            if line.strip().startswith('scope:'):
                scope = line.partition(':')[2].strip()

prompt = f'''Synthesize foundational SE book knowledge for the {role} role.
Scope: {scope}

These are notes from authoritative SE books and resources (not repo patterns).
Extract PRINCIPLES, PATTERNS, and DECISION FRAMEWORKS — not implementation details.

RULES:
- Focus on timeless principles, not framework-specific advice
- These are foundational — they apply regardless of language or framework
- Rank by importance for this specific role
- Keep under 2000 tokens

SOURCES:
{all_knowledge}

OUTPUT:

## Foundational Principles
[Ranked by importance for this role]

## Design Patterns to Apply
[Patterns most relevant to this role, with when to use each]

## Decision Frameworks
[How to make decisions in this role\\'s domain — tradeoff analysis]

## Common Mistakes (from books)
[What the books say to avoid — with the correct approach]
'''

synth_model = os.environ.get('LEARN_SYNTH_MODEL', 'fable')
result = call_llm(prompt, max_tokens=3000, model=synth_model)

output = book_dir / '_books_synthesis.md'
output.write_text(f'''---
role: {role}
type: foundational_books
sources: {len(files)}
synthesized_at: {datetime.now().isoformat()}
---

{result}
''')
print(f'    ✓ {role}/books/_books_synthesis.md')
" 2>&1 | sed 's/^/    /'
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
    synth_books "$role"
done

echo ""
echo "Updating books-knowledge.json (separate from repo knowledge)..."
python3 -c "
import json
from pathlib import Path

roles_dir = Path('$SCRIPT_DIR')
books_knowledge = {}

for role_dir in sorted(roles_dir.iterdir()):
    synthesis = role_dir / 'books' / '_books_synthesis.md'
    if synthesis.is_file():
        content = synthesis.read_text()
        if content.startswith('---'):
            parts = content.split('---', 2)
            if len(parts) >= 3:
                content = parts[2].strip()
        books_knowledge[role_dir.name] = content
        print(f'  ✓ {role_dir.name}')

bkj = roles_dir / 'books-knowledge.json'
bkj.write_text(json.dumps(books_knowledge, indent=2))
print(f'  Written {len(books_knowledge)} roles to books-knowledge.json')
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
