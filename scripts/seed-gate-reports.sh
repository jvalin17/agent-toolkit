#!/bin/bash
# Copy CI fixture reports into reports/ for toolkit self-attestation.
set -e
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
FIXTURES="$ROOT/tests/fixtures/gate-reports"
for skill in precommit evaluate reviewer assess; do
  mkdir -p "$ROOT/reports/$skill"
done
cp "$FIXTURES/pc_toolkit_ci.md" "$ROOT/reports/precommit/"
cp "$FIXTURES/eval_toolkit_ci.md" "$ROOT/reports/evaluate/"
cp "$FIXTURES/review_toolkit_ci.md" "$ROOT/reports/reviewer/"
cp "$FIXTURES/assess_toolkit_ci.md" "$ROOT/reports/assess/"
echo "Seeded gate reports from tests/fixtures/gate-reports/"
