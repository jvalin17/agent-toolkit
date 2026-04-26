# Dependencies Review
Keywords: weight, size, heavy, bloat, alternatives, package, bundle, dependency, outdated, deprecated

For guardrails and principles, see main SKILL.md.

## Step 1: Scan Package Manager File

Find and read the dependency manifest:
- `package.json` (Node.js)
- `pyproject.toml` / `requirements.txt` (Python)
- `Cargo.toml` (Rust)
- `go.mod` (Go)
- `Gemfile` (Ruby)
- `build.gradle` / `pom.xml` (Java)

List all dependencies with their purpose.

## Step 2: Weight Audit

For each dependency, check approximate install size. Flag packages over 10MB.

| Package | Size | Purpose | Verdict |
|---------|------|---------|---------|
| moment | 4.2MB | Date formatting | Replace with dayjs (2KB) or date-fns (tree-shakeable) |
| lodash | 4.7MB | 2 utility functions | Replace with native JS or lodash-es with tree shaking |
| aws-sdk | 64MB | S3 uploads only | Use @aws-sdk/client-s3 (3MB) |

Suggest lighter alternatives or pure implementations when:
- A large package is used for a single function
- A native/stdlib alternative exists
- A smaller drop-in replacement is available

## Step 3: Version Compatibility

- Check that dependency versions are compatible with the project's runtime (Node version, Python version, etc.).
- Flag any version pins that are very old (2+ major versions behind).
- Flag conflicting version requirements between dependencies.
- Run `npm audit` / `pip audit` / equivalent if available. Report vulnerabilities.

## Step 4: Health Check

For each dependency, assess maintenance status:

| Signal | Healthy | Concerning |
|--------|---------|------------|
| Last publish | < 12 months | > 24 months |
| Open issues | Actively triaged | 500+ untriaged |
| Downloads | Stable or growing | Declining sharply |
| Deprecated | No | Yes — find replacement |

Flag deprecated packages. Flag unmaintained packages (no commits in 2+ years) that handle security-sensitive operations (auth, crypto, parsing).

## Step 5: Unused Dependencies

Search the codebase for actual imports/requires of each dependency. Flag any that are listed in the manifest but never imported.

Run `npx depcheck` (Node.js) or equivalent tool if available.

## Output Format

> **Dependencies Review**
>
> | # | Package | Issue | Size | Recommendation |
> |---|---------|-------|------|----------------|
> | 1 | moment | Heavy, deprecated | 4.2MB | Replace with dayjs |
> | 2 | express-validator | Unused | 180KB | Remove |
> | 3 | node-fetch | Unnecessary in Node 18+ | 50KB | Use native fetch |
>
> **Total dependencies:** [count prod] + [count dev]
> **Flagged:** [count heavy] heavy, [count deprecated] deprecated, [count unused] unused
> **Vulnerabilities:** [count from audit tool, or "audit not available"]
