# UI/UX Requirements
Keywords: screens, flows, design, wireframes, accessibility, responsive, components, UI, UX

Triggered when user selected "A visual interface" in Q5. Ask the user directly for all batches.

**Rules from real usage:**
- File input = always multi-modal (drag-drop + file picker + paste). Never file path strings.
- Every data-dependent screen needs an empty state with action link ("No data yet — import your resume").
- Name user-facing features BEFORE building ("Knowledge Bank" vs "My Superpowers" matters).
- Specify where the action lives AND where the result flows (upload on main page, data goes to knowledge bank).
- Core features must never be conditionally hidden — always show with empty state guidance.
- Get wireframe approval before coding. Frontend rebuilt 3x without this.

---

## Batch 0: Existing Designs (always ask first)

**Q-UI-0: Do you have any existing designs, mockups, or screenshots?**
If user provides files: follow G5 (File Safety Check), read images, extract screens/layout/components/colors/interactions, confirm with user. Use extracted info to pre-fill remaining batches.

## Batch 1: Screens & Flows

**Q-UI-1: What are the key screens / pages?** Infer from functional requirements, ask user to confirm.

**Q-UI-2: What's the primary user flow?** Walk through step by step, ask user to confirm.

## Batch 2: Look & Feel

**Q-UI-3: Do you have an existing design system or reference?** (designs/library/brand guide/from scratch/don't care)

**Q-UI-4: What's the visual style?** (clean/rich/dashboard/marketing/match existing)

## Batch 3: Responsive & Accessibility

**Q-UI-5: What devices should this work on?** (desktop only/+tablet/+mobile/mobile-first/native)

**Q-UI-6: Any accessibility requirements?** (WCAG AA/AAA/basic/none — recommend AA as baseline)

## Batch 4: Interaction Patterns (Standard + System Design modes only)

**Q-UI-7: Any specific interaction patterns needed?** (drag-drop, real-time, infinite scroll, wizards, rich text, data tables, charts, maps, file upload, etc.)

If user is confused: launch sub-agent to research how similar products handle their UI.

## Optional: Generate HTML Wireframes

After gathering all UI requirements, offer to generate simple HTML wireframes in `requirements/wireframes/`. Self-contained, gray-box, responsive, annotated with HTML comments. Get approval before coding.

## Output Section Template

Add to the requirements document: Key Screens table (with priority), Primary User Flow, Design Direction, Responsive Targets, Accessibility target, Interaction Patterns.
