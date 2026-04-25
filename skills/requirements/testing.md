# Testing Requirements Gathering

Sub-skill for the requirements agent. Covers testing culture, test types, CI/CD expectations, and quality gates. Available in Standard and System Design modes.

Enter this flow with: "Let's talk about how you want to ensure quality."

Use AskUserQuestion tool for all batches.

---

## Batch 1: Testing Culture & Expectations

**Q-TEST-1: What's your current testing situation?** (select one)
- No tests exist — starting fresh
- Some tests exist but coverage is low
- Good test coverage — want to maintain or improve
- Strict testing culture — everything must be tested
- I don't know what testing I need (explain: "Tests catch bugs before users do. I'll recommend a baseline for your project type.")

**Q-TEST-2: What level of testing do you need?** (explain each with cost)
- **Basic** — unit tests for critical logic only. Catches obvious bugs. Good for personal tools, prototypes.
- **Standard** — unit + integration tests. Catches most bugs. Good for team projects, internal tools.
- **Comprehensive** — unit + integration + end-to-end. Catches subtle bugs. Good for production apps with users.
- **Rigorous** — all of the above + performance + security + regression suites. For apps where bugs = money or safety.

> Show: "Each level adds cost: Basic = ~10% more dev time, Standard = ~20%, Comprehensive = ~30%, Rigorous = ~40%+."

If the user is unsure, recommend based on project type:
- Personal tool / prototype -> Basic
- Team project / internal tool -> Standard
- Production app with real users -> Comprehensive
- Financial, healthcare, safety-critical -> Rigorous

---

## Batch 2: Specific Test Types

**Q-TEST-3: Any specific testing requirements?** (multi-select)
- Automated regression tests (run on every PR/push)
- Integration tests against real services (not mocks)
- End-to-end / browser tests (Playwright, Cypress, Selenium)
- Performance / load testing (response times under load)
- Security testing (penetration tests, vulnerability scanning)
- Accessibility testing (automated WCAG checks)
- Visual regression testing (screenshot comparison)
- API contract testing (verify API shapes don't break)
- ML model evaluation tests (accuracy, drift, bias)
- None of these — just unit tests
- I'm not sure (recommend based on project type)

For each selected type, capture scope details:
- **Regression:** what flows must be regression-tested before every release?
- **Integration:** which external services need real integration tests vs mocks?
- **E2E:** which critical user flows need browser-level testing?
- **Performance:** what are the target response times and load levels?
- **Security:** what attack surfaces need scanning? (OWASP Top 10, dependency audits)
- **Accessibility:** what WCAG level? (ties back to UI/UX if that section was completed)
- **Visual regression:** which screens/components are visually sensitive?
- **Contract:** which API endpoints have external consumers?
- **ML evaluation:** what metrics matter? (accuracy, precision, recall, F1, drift detection)

---

## CI/CD Expectations

**Q-TEST-4: How should tests run?** (select one)
- Manually — I'll run them when I want
- On every commit / push (CI)
- On pull requests (CI with gate — tests must pass to merge)
- Full pipeline — lint + type check + test + deploy (CI/CD)
- I don't have CI set up yet (note: recommend setup in architecture)

---

## Output Section Template

Add this section to the requirements document:

```markdown
## Testing Requirements

### Testing Level
- **Level:** [basic / standard / comprehensive / rigorous]
- **Current state:** [none / low-coverage / good / strict]

### Required Test Types
| Test Type | Required? | Scope | Notes |
|----------|-----------|-------|-------|
| Unit tests | yes/no | [what to cover] | |
| Integration tests | yes/no | [real services or mocks] | |
| End-to-end tests | yes/no | [key flows] | |
| Performance tests | yes/no | [targets] | |
| Security tests | yes/no | [scope] | |
| Accessibility tests | yes/no | [WCAG level] | |
| Visual regression | yes/no | [key screens] | |
| API contract tests | yes/no | [endpoints] | |
| ML evaluation | yes/no | [metrics] | |

### CI/CD Expectations
- **Trigger:** [manual / commit / PR / full pipeline]
- **Gate:** [tests must pass to merge: yes/no]

### Regression Policy
- [what must be tested before every release]
```
