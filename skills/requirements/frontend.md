# UI/UX Requirements Gathering

Sub-skill for the requirements agent. Covers screens, flows, design systems, responsive targets, accessibility, and interaction patterns. Triggered when the user selected "A visual interface" in intake Q5.

Enter this flow with: "Let's talk about the visual side."

Use AskUserQuestion tool for all batches.

---

## Batch 0: Existing Designs (always ask first)

**Q-UI-0: Do you have any existing designs, mockups, or screenshots?**
- Yes, I have files to share (ask for file paths)
- Yes, I have a URL / link (ask for link)
- No, starting from scratch (skip to Batch 1)

**If user provides files:**
Follow G5 (File Safety Check). Accept images (`.png`, `.jpg`, `.svg`, `.webp`) and documents (`.pdf`). Reject proprietary design files (`.fig`, `.sketch`, `.xd`) and ask for an exported PNG or PDF instead.

Read each image using the Read tool (Claude can analyze images). For each uploaded design, extract and present:

> "Here's what I see in your design:"
> - **Screens identified:** [list]
> - **Layout pattern:** [grid / sidebar / cards / list / etc.]
> - **Key components:** [nav, forms, tables, modals, etc.]
> - **Color palette:** [primary, secondary, accent — approximate hex values]
> - **Typography:** [heading style, body style — approximate]
> - **Interaction hints:** [buttons, links, dropdowns, tabs visible]
> - **Accessibility observations:** [contrast issues, missing labels, etc.]

Ask: "Did I capture this correctly? Anything I missed or got wrong?"

Use extracted information to pre-fill answers for the remaining UI batches. Do not re-ask questions the designs already answer.

---

## Batch 1: Screens & Flows

**Q-UI-1: What are the key screens / pages?**
List what you infer from the functional requirements, then ask the user to confirm, add, or remove.

> "Based on what you described, I think you'll need these screens:"
> - [inferred screen list]
> "Anything missing or wrong?"

**Q-UI-2: What's the primary user flow?** (the number-one thing a user does, step by step)
Walk through it: "User lands on [X] -> clicks [Y] -> sees [Z] -> ..."
Ask the user to confirm or correct.

---

## Batch 2: Look & Feel

**Q-UI-3: Do you have an existing design system or reference?**
- I have designs / mockups / Figma (ask for link or description)
- Use an existing component library (Material UI, shadcn/ui, Ant Design, etc.)
- I have a brand guide (colors, fonts, logo)
- No — start from scratch
- I don't care about styling yet (note: will use sensible defaults)

**Q-UI-4: What's the visual style?**
- Clean / minimal
- Rich / detailed
- Dashboard / data-heavy
- Marketing / landing page style
- Match an existing product (which one?)
- I don't know (show best option with one alternative)

---

## Batch 3: Responsive & Accessibility

**Q-UI-5: What devices should this work on?**
- Desktop only
- Desktop + tablet
- Desktop + mobile (responsive)
- Mobile-first
- Native mobile app (note: impacts architecture significantly)

**Q-UI-6: Any accessibility requirements?**
- Must meet WCAG 2.1 AA (standard for most apps)
- Must meet WCAG 2.1 AAA (high — government, healthcare)
- Basic accessibility (keyboard nav, alt text, contrast)
- No specific requirements (recommend WCAG AA as baseline)

---

## Batch 4: Interaction Patterns (Standard + System Design modes only)

Skip in Quick mode.

**Q-UI-7: Any specific interaction patterns needed?**
- Drag and drop
- Real-time updates / live data
- Infinite scroll / pagination
- Multi-step forms / wizards
- Rich text editing
- Data tables with sorting/filtering
- Charts / data visualization
- Maps
- File upload with preview
- None of these / not sure

**If user is confused about UI approach:** Launch a sub-agent to research how similar products handle their UI.

> "Let me research how similar products design their [feature] UI — one moment."

Spawn Agent tool with: "Research how [similar products] design their UI for [feature]. Return: key screens, layout patterns, interaction patterns, component patterns. Keep it concise — 5-10 bullet points with examples."

Present findings to user and let them pick what applies.

---

## Optional: Generate HTML Wireframes

After gathering all UI requirements, offer:

> "I can generate simple HTML wireframes for your key screens so you can open them in a browser and validate the layout before we move on. Want me to?"
> - **Yes, for all key screens** (generate all)
> - **Yes, just for [specific screen]** (generate one)
> - **No, the requirements are enough** (skip)

**If yes:**

Generate one HTML file per screen in `requirements/wireframes/`. Each file should be:
- Self-contained (inline CSS, no external dependencies)
- Simple gray-box wireframes — rectangles for images, lines for text, basic layout structure
- Responsive (works on desktop and mobile)
- Annotated with HTML comments marking each component: `<!-- Navigation Bar -->`, `<!-- Search Form -->`, etc.
- Includes a small legend/key at the top explaining what the gray boxes represent

File naming: `requirements/wireframes/<screen-name>.html`

After generating, tell the user:
> "Wireframes are in `requirements/wireframes/`. Open them in your browser to review. Let me know if any layout needs adjustment before we continue."

If the user requests changes, update the wireframes and the UI requirements to stay in sync.

---

## Output Section Template

Add this section to the requirements document:

```markdown
## UI/UX Requirements

### Key Screens
| Screen | Purpose | Key Elements | Priority |
|--------|---------|-------------|----------|
| ... | ... | ... | must/should/could |

### Primary User Flow
1. User [action] -> [screen]
2. -> [action] -> [screen]
3. -> [outcome]

### Design Direction
- **Style:** [clean / rich / dashboard / etc.]
- **Design system:** [library name or "custom"]
- **Reference:** [link or "none"]

### Responsive Targets
- **Primary:** [desktop / mobile / both]
- **Breakpoints:** [mobile-first / desktop-first]

### Accessibility
- **Target:** [WCAG AA / AAA / basic]

### Interaction Patterns
- [pattern 1]
- [pattern 2]
```
