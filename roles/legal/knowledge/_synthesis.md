---
role: legal
sources: 3
synthesized_at: 2026-08-17T02:49:46.608444
---

## [DRAFT — HUMAN REVIEW REQUIRED]

## Role Summary
Legal knowledge synthesized from three content-publishing repos: choosealicense.com (license catalog, upstream source for GitHub's Licensee API), OWASP CheatSheetSeries (security guidance under CC-BY-SA-4.0), and privacyguides.org (privacy product recommendations). All three are static sites publishing legally sensitive content — the dominant legal concerns are licensing structure, translation of legal content, downstream reliance liability, and infrastructure-layer privacy obligations.

## Patterns Found (ranked by frequency across repos)

### 1. Static site = minimal application-layer privacy exposure (3/3 repos)
All three are static sites (Jekyll / MkDocs) with no user accounts, forms, or databases. Privacy obligations (GDPR/CCPA) shift entirely to the infrastructure layer:
- **choosealicense**: GitHub Pages/Actions → GitHub/Microsoft ToS govern data residency; no operator control
- **OWASP**: static site container (`EXPOSE 8000`); hosting infra not in repo
- **privacyguides**: self-hosted Caddy in Docker — Caddy access logs contain IP addresses (personal data under GDPR); log residency unresolved in repo; Caddy's auto-HTTPS talks to Let's Encrypt ACME servers (certificate transparency logs expose domain data)

### 2. Legal content stored as version-controlled flat files (3/3 repos)
- choosealicense: license texts in `_licenses/*.txt`, characterizations in `_data/rules.yml`
- privacyguides: `docs/about/donation-acceptance-policy.md`, `executive-policy.md`, `notices.md`
- OWASP: `cheatsheets/*.md`
**Implication (noted in privacyguides analysis):** superseded policy versions remain permanently discoverable in git history; no formal versioning scheme on legal docs.

### 3. Community/crowdsourced translation of legally significant content, no legal review (2/3 repos)
- **choosealicense**: Weblate (`TRANSLATING.md`, `WEBLATE.md`); translates UI/summaries but **never license legal text** — "the legal text of each license is never translated"
- **privacyguides**: Crowdin (`crowdin.yml`); each translation is a derivative work; translator IP/CLA framework unclear
**Shared risk:** mistranslated legal guidance in jurisdictions requiring local-language consumer content (Quebec Bill 96, French Toubon Law). choosealicense-specific wrinkle: EUPL has official equally-authoritative EU-language versions, but only English is shown.

### 4. Dual/separated licensing structure (2/3 repos)
- **privacyguides**: `LICENSE` (content) + `LICENSE-CODE` (code) — two instruments, contributors must know which applies
- **OWASP**: single `CC-BY-SA-4.0` in `package.json`, `LICENSE.md`, README badge — copyleft; derivatives (including commercial products and possibly AI training outputs) must use same license
- **choosealicense**: `LICENSE.md` at root + automated `spec/self_license_spec.rb` verifying the site's own license (self-compliance test)

### 5. SPDX-aligned identifiers (1/3, but ecosystem-wide relevance)
choosealicense uses SPDX naming (`apache-2.0.txt`, `gpl-3.0.txt`) and vendors `license-list-XML/` — interoperable with SBOM/REUSE tooling.

### 6. GPL components in Docker images (2/3 repos)
- privacyguides: `pngquant` (GPL v3) in runtime image — copyleft obligations if image is distributed
- OWASP: `python:3.14-slim` + `apt-get install build-essential gcc ...` (GPL/LGPL) — obligations attach only if image published (e.g., Docker Hub)

## How Problems Are Solved

**PROBLEM: Characterizing legal effect of licenses/products without giving legal advice**
- choosealicense: structured YAML summaries (`_data/rules.yml`, `_data/fields.yml`) separate from license text; disclaimer presumably in `about.md`, not in data layer
- privacyguides: public `docs/about/criteria.md` (representation framework) + documented delisting process (`blog/posts/delisting-startpage.md`, `delisting-wire.md`) as accountability/liability mitigation
- OWASP: no disclaimer mechanism identified for compliance reliance on cheat sheets

**PROBLEM: Draft vs. authoritative content**
- OWASP: separate `cheatsheets_draft/` dir excluded from linting and publication — drafts explicitly not quality-controlled
- OWASP: README flags markdown files as working sources — "aren't intended to be referenced in any external documentation" — a normative preference, **not legally enforceable against CC-BY-SA-4.0 rights**
- choosealicense: curated license list per `CONTRIBUTING.md` ("We catalog **select** licenses") — omissions (SSPL, BSL variants) carry editorial weight, no published curation policy

**PROBLEM: Downstream reliance on published legal data**
- choosealicense: content vendored into Licensee → GitHub's license-detection API; no versioned contract, SLA, or liability limitation for downstream compliance consumers; test dep pinned to `git master` (`gem 'licensee', git: '...', branch: 'master'`) — non-reproducible compliance testing
- privacyguides: specific service endorsements (`data-broker-removals.md`, EasyOptOuts review) — criteria + delisting docs are the mitigation

## Architecture Decisions Seen

| Decision | Chosen approach | Repo | Tradeoff noted |
|---|---|---|---|
| License summaries vs. text | Editable independently (`rules.yml` vs `_licenses/*.txt`) | choosealicense | Version-skew risk; no test cross-validates summary vs. text |
| Content license | CC-BY-SA-4.0 (copyleft) over CC-BY-4.0 | OWASP | Blocks proprietary derivatives; AI-training ShareAlike applicability legally unsettled |
| Legal guidance publication | Dedicated `activism/legal/` section; `no-permission.md` legal-status page | privacyguides; choosealicense | Unauthorized-practice-of-law exposure in broad-definition jurisdictions; disclaimers are key mitigations |
| AI content | `ai-chat.md` recommendations page; `AML_Sanctions_AI_Agent_Payments_Cheat_Sheet.md` | privacyguides; OWASP | EU AI Act exposure — AML/payments is a high-risk category; recommending AI systems may implicate deployer/facilitator questions |
| Deployment | Custom GitHub Actions (polyglot not on Pages whitelist) | choosealicense | Data residency fixed to GitHub/Azure, not configurable |

## Testing Approaches
- **choosealicense** (only repo with legal-relevant tests): `license_spec.rb`, `license_fields_spec.rb`, `license_meta_spec.rb`, `license_rules_spec.rb`, `license_bom_spec.rb`, `self_license_spec.rb`, `i18n_spec.rb`. **Gap: tests validate structure/presence, never accuracy of legal characterizations against license text.**
- **OWASP**: markdownlint/textlint only (`lint-terminology` targets `./cheatsheets/` only, excluding drafts)
- **privacyguides**: no visible testing — no link-rot checks on recommended products, no WCAG tooling, no policy-accuracy checks

## Deployment & Production
- All three: static output; GitHub-hosted source (Microsoft DPA / SCCs govern contributor data)
- choosealicense: GitHub Actions deploy → GitHub Pages infra (Azure); no residency control possible
- OWASP: `python:3.14-slim` container, port 8000; `^` caret version specifiers allow silent dependency (and license) drift; `package-lock.json` and `requirements.txt` not reviewed
- privacyguides: Caddy + tini in Docker; `HEALTHCHECK NONE`; `ENTRYPOINT ["/bin/bash"]` (no locked run command); OCI label `org.opencontainers.image.source` links to repo (supports source-availability disclosure); `Pipfile.lock` present (reproducible builds)
- **Accessibility: no WCAG/ADA/EN 301 549 tooling or documentation in any repo** — flagged as a gap in OWASP and privacyguides analyses

## Open Questions (for reviewer)
1. **Translation of legal content**: never translate legal text (choosealicense) vs. crowdsource everything (privacyguides Crowdin). Neither has legal review of translations. Which policy to adopt? What about licenses with official multilingual versions (EUPL)?
2. **Summary–text sync**: should license/policy characterizations be tested for accuracy against source text (no repo does this), or is structural validation sufficient?
3. **Copyleft content licensing**: CC-BY-SA-4.0 (OWASP) vs. dual content/code split (privacyguides). ShareAlike's effect on AI training data remains unsettled — position needed.
4. **Versioning of legal data consumed downstream**: choosealicense's rolling-master model vs. formal versioned releases — is an SLA/liability limitation needed for API consumers?
5. **GPL tooling in distributed Docker images** (pngquant, build-essential): adopt a policy on runtime-image license auditing?
6. **UPL risk**: two repos publish legal guidance (no-permission.md, activism/legal/) — standard disclaimer language and placement (data layer vs. about page)?
7. **Draft content**: OWASP's separate-directory approach vs. status metadata — which convention for unvetted legal content?
