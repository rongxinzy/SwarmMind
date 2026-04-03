# SwarmMind Design System

> Status: canonical design source of truth for `SwarmMind/ui/`
> Last updated: 2026-04-03
> Scope: V1 Supervisor UI, with immediate guidance for `v0 chat`

## 1. Purpose

SwarmMind is not a generic AI chat shell.
It is a supervised AI work surface for exploration, execution, and governance.

The UI must consistently communicate:

- structured work over casual conversation
- operational clarity over brand spectacle
- trust and traceability over novelty
- light exploration in chat, heavier control in project space

This file exists to stop visual drift between:

- `docs/ui/*` product rules
- `ui/src/index.css` token implementation
- page-level frontend decisions made during rapid iteration

If design decisions conflict, this file wins.

## 2. Product Character

SwarmMind V1 should feel:

- Structured
- Operational
- Trustworthy
- High-signal
- Human-supervised AI

This means:

- more control-room than chatbot
- more workspace than marketing page
- more calm hierarchy than visual entertainment

Chat can be lighter than Project, but never toy-like.

## 3. Design Principles

### 3.1 Primary Rules

- Information hierarchy beats decoration.
- Status semantics beat accent color experimentation.
- Layout beats card stacking.
- Motion serves feedback, focus, and continuity only.
- Empty states are working states, not filler space.

### 3.2 Subtraction Rules

- If a UI element does not clarify state, next action, or scope, remove it.
- If two surfaces say the same thing, merge them.
- If a section can be understood without a card, do not wrap it in a card.
- If an animation is noticeable before the content is useful, it is too loud.

## 4. Page Taxonomy

SwarmMind has two primary UI moods.

### 4.1 ChatSession

Use when the user is exploring, drafting, asking, or pressure-testing an idea.

Visual traits:

- lighter shell
- softer separation between surfaces
- strong input affordance
- weaker governance framing
- faster feedback loops

### 4.2 Project Space

Use when the user is executing formal work with team, approvals, artifacts, and risk.

Visual traits:

- more formal structure
- denser information
- persistent status visibility
- explicit governance surfaces
- stronger page chrome and clearer sectional framing

Rule:
Chat is for exploration.
Project is for execution.

They must not look interchangeable.

## 5. Typography

### 5.1 Canonical Font Decision

Canonical V1 typography is:

- Sans: `Geist`
- Mono: `Geist Mono`

Rationale:

- matches the existing UI docs
- reads as neutral, modern, and operational
- fits high-density product surfaces better than display-forward alternatives

### 5.2 Current Drift

Current implementation in `ui/src/index.css` uses:

- `Space Grotesk Variable` for sans and headings
- `IBM Plex Sans` for body

This is now considered temporary drift.

Target migration:

- `--font-sans` -> Geist
- `--font-heading` -> Geist
- `--font-body` -> Geist
- `--font-mono` -> Geist Mono

Until that migration happens, new UI work should behave as if Geist is the intended design baseline.

### 5.3 Type Scale

- Page title: 28/36, semibold
- Section title: 18/28, semibold
- Surface title: 15/22, medium or semibold
- Body: 14/22
- Dense supporting text: 13/20
- Metadata / labels: 12/18
- Tiny status text: 11/16

Rules:

- No oversized hero typography in product pages.
- Headings must be concise and utility-oriented.
- Avoid decorative all-caps except small metadata labels.

### 5.4 Tracking Rules

- Page title and large headings: tighten slightly, usually `-0.02em`
- Section and surface titles: near-neutral tracking, between `-0.01em` and `0`
- Body copy: default tracking, do not squeeze for style
- Metadata / all-caps labels at 11-12px: add tracking, usually `0.04em-0.08em`

Tracking is part of hierarchy.
If a label or title feels cheap, check tracking before changing color or weight.

## 6. Density, Spacing, and Rhythm

SwarmMind V1 is medium-high density.
It should feel efficient, not cramped.

### 6.1 Spacing Scale

Use a base 4px rhythm:

- 4
- 8
- 12
- 16
- 20
- 24
- 32
- 40
- 48

### 6.2 Surface Padding Rules

- Small controls: 8-12px internal padding
- Standard card / panel: 16px
- Large panel or composer: 20-24px
- Message bubble: 16-24px horizontal, 12-20px vertical depending on role

### 6.3 Vertical Rhythm

- Tight clusters inside one semantic block: 8-12px
- Between separate semantic blocks in the same surface: 16-20px
- Between major page sections: 24-32px

## 7. Color System

V1 color is neutral-first with semantic accents.
Accent color is not branding. Accent color is state.

### 7.1 Neutral Chassis

SwarmMind uses a warm gray chassis.
Target feeling is closer to Notion paper warmth than Vercel cold slate.

Use a strict neutral ladder from `Neutral-50` to `Neutral-900`:

- `Neutral-50`: warm paper background
- `Neutral-100`: primary canvas
- `Neutral-150`: sticky / elevated utility tint
- `Neutral-200`: secondary panel
- `Neutral-300`: low-contrast border
- `Neutral-500`: muted text
- `Neutral-700`: strong secondary text
- `Neutral-900`: primary text

Base surface intent:

- App background: warm near-white
- Primary panel: slightly brighter than background
- Secondary panel: soft warm gray
- Border: low-contrast warm gray
- Text: dark charcoal, never pure black
- Muted text: quiet warm gray

### 7.2 Semantic States

These colors are semantic and should stay consistent across all pages:

- running: desaturated steel blue
- approval: muted ochre / amber
- blocked: restrained terracotta
- done: sage / mint green
- draft: warm gray
- chat-only exploratory state: soft gray-violet only when useful, never as page theme

Rule:
If a semantic color looks like a Bootstrap default swatch, it is too pure.

### 7.3 Usage Rules

- State color is for badges, chips, borders, progress markers, and targeted emphasis.
- State color is not for large background washes.
- Never theme an entire page around a single mode color.
- Keep one dominant accent visible per area.

### 7.4 Dark Mode Mapping

Dark mode should not be a literal inversion of the warm light theme.

Rules:

- preserve the calm, human tone of the warm chassis
- avoid sepia-heavy dark browns that feel muddy or low-contrast
- allow dark neutrals to move slightly toward neutral or cool gray for legibility
- keep semantic accents desaturated in dark mode as well
- protect text contrast first, warmth second

Target feeling:

- more charcoal-paper than black glass
- more neutral ink than brown tint
- still calm and supervised, never neon or cyber-themed

## 8. Border Radius and Shadow

### 8.1 Radius System

- Inputs and buttons: 10-12px
- Standard cards: 14-18px
- Large floating panels / composer: 20-24px
- Message bubbles: 20-26px

Avoid using the same large rounded value on every surface.
Radius should express hierarchy, not style-for-style's-sake.

### 8.2 Shadow System

- Most surfaces: very soft or no visible shadow
- Elevated utility surfaces: one restrained shadow
- Sticky composer: slightly stronger shadow to separate from scroll content
- If shadow alone is not enough, use a low-opacity warm surface plus a very light backdrop blur

### 8.3 Micro-Depth

SwarmMind should avoid loud elevation but still preserve depth.

Allowed depth tools:

- low-contrast border
- subtle tonal separation between stacked neutrals
- one restrained shadow
- selective `backdrop-blur` on sticky or floating utility surfaces

Forbidden:

- glassmorphism as page identity
- frosted panels everywhere
- dark heavy shadow stacks
- blur used only for decoration

Rule:
If removing the shadow makes the UI look cheap, the layout is doing too little work.

## 9. Motion

### 9.1 Allowed Motion

SwarmMind V1 allows small, breathable motion.
It does not allow attention-seeking motion.

Allowed:

- soft fade-in on entering content
- subtle translateY transitions for new messages
- hover and focus transitions
- lightweight streaming indicators
- controlled sticky surface transitions
- low-amplitude accordion / collapse motion

### 9.2 Forbidden Motion

- decorative looping background animation
- large parallax or scene-level motion
- dramatic multi-stage entrance choreography
- motion used only to signal "AI-ness"
- motion that competes with text input or status reading

### 9.3 Timing Rules

- Micro transitions: 120-180ms
- Standard content transitions: 180-260ms
- Only one "strong" motion event visible at a time in a local region

### 9.4 Motion Purpose Test

Every animation must answer one of:

- what changed?
- where did it go?
- what should I notice?

If it answers none of these, cut it.

## 10. Layout System

### 10.1 App Shell

Global shell follows:

- fixed sidebar
- sticky top header where needed
- central work surface
- optional right-side contextual area

This should read as a working application, not a landing page.

### 10.2 Layout over Cards

Default to layout first.
Cards are allowed only when they represent a real semantic container:

- a settings group
- a state summary
- a message bubble
- a primary composer surface
- a reviewable artifact or approval item

Do not solve every composition problem by wrapping things in cards.

## 11. Accessibility Baseline

Non-negotiable:

- touch targets 44px minimum
- keyboard-reachable controls
- visible focus states
- semantic headings and landmarks
- status changes readable without color alone
- body text contrast remains high on all neutral surfaces

For chat specifically:

- composer controls must remain keyboard usable
- status text must be concise and persistent enough to read
- hover-only affordances must have a keyboard or always-visible fallback

## 12. Content Tone

SwarmMind copy should sound operational and calm.

Prefer:

- "输入问题或任务"
- "等待新的输入"
- "会话执行失败"
- "回到最新"

Avoid:

- hype language
- whimsical assistant personality text
- decorative slogans that say nothing

## 13. Component Guidance

### 13.1 Buttons

- primary buttons are compact and decisive
- secondary buttons should not visually compete with primary action
- icon-only buttons must still meet target size rules

### 13.2 Chips and Badges

- use for state and scope
- keep text short
- avoid rainbow badge clusters

### 13.3 Panels

- panels must signal hierarchy through spacing and border strength more than color
- avoid glassmorphism and heavy blur as a visual identity
- pinned bars, sticky composers, and utility overlays may use low-opacity blur if it improves separation from moving content

### 13.4 Iconography

Icon language must match the typography.

Rules:

- default to linear icons with restrained geometry
- prefer a consistent `1.5px`-style stroke feel across the product
- corners and joins should feel aligned with Geist's modern, rational skeleton
- use monochrome icons by default; state color enters only when it clarifies meaning
- do not mix unrelated icon families within the same product surface

If an icon looks softer, rounder, or more decorative than the surrounding type, it is the wrong icon.

### 13.5 Message Bubbles

- user bubble: slightly stronger tint, clearly authored by the user
- assistant response: neutral-first, optimized for reading
- assistant response may drop visible bubble chrome entirely in long-form reading views
- if assistant keeps a surface, it should be nearly invisible and exist only to preserve rhythm
- assistant response should prioritize text measure, markdown rhythm, and calm elevation

## 14. v0 Chat: Canonical Design Rules

This section is the immediate design contract for `ui/src/components/ui/v0-ai-chat.tsx`.

### 14.1 Job of the Page

The v0 chat page is a lightweight exploratory work surface.
Its primary job is to help the user start work quickly.

It is not:

- a consumer AI playground
- a mode gallery
- a prompt template showcase
- a brand statement page

### 14.2 Hierarchy

The visual order must be:

1. input/composer
2. active conversation content
3. current execution state
4. optional starter prompts
5. secondary controls

If the eye lands on anything before the composer in an empty chat, hierarchy is wrong.

### 14.3 Empty State

The empty state should be compact and warm, not theatrical.

Required:

- one restrained monochrome icon or mark
- short title
- one-line explanation
- visible primary composer
- 2-4 starter prompts maximum
- warmth should come from whitespace, type rhythm, and soft neutrals

Avoid:

- oversized intro blocks
- large decorative hero treatment
- multiple competing callouts

### 14.4 Composer

The composer is the anchor of the page.

Rules:

- must remain visible while reading history
- should read as the primary working surface
- status and model/mode controls belong to the composer region
- controls beneath the textarea should feel secondary to the text entry area
- sticky separation may use a subtle warm tint, restrained shadow, and very low blur
- composer should feel lifted from the transcript without becoming a floating gadget

Focus state:

- never rely on the browser default saturated blue outline
- focus should be expressed through one calm primary cue and one secondary cue only
- recommended pair: slightly stronger border contrast plus a soft local ring or shadow
- focus styling must stay within the warm-neutral system, not break page tone
- the focused composer should feel clearer and more intentional, not louder

### 14.5 Mode Picker

Execution mode is an advanced control, not the page headline.

Rules:

- visible, but low-to-medium emphasis
- color can help distinguish modes
- mode must not theme the whole page
- labels must read as execution strategy, not feature marketing

### 14.6 Message Stream

- optimize for readability over ornament
- left/right alignment is enough; do not over-style authorship
- markdown rhythm matters more than bubble decoration
- new message motion should be subtle
- assistant replies should feel more like an annotated document than a chat toy
- long answers should read as continuous content, not stacked decorated bubbles

### 14.7 Status

Status should explain progress and recovery.

Required states:

- model loading
- conversation loading
- streaming
- success/completed
- failed with retry path
- no available model

Rule:
Every error state should tell the user what they can do next.

## 15. Responsive Rules

### 15.1 Mobile

- composer remains pinned
- message width increases relative to viewport
- metadata and secondary actions collapse before text area does
- starter prompts reduce visual count before they reduce legibility

### 15.2 Tablet

- preserve desktop information hierarchy
- simplify side chrome before shrinking core reading area

### 15.3 Desktop

- prioritize comfortable reading width
- avoid giant center voids
- maintain fixed composer width aligned with message column

## 16. Do / Don't

### Do

- use semantic state colors consistently
- keep product surfaces calm
- let spacing and hierarchy do most of the visual work
- use restrained motion to add breathing room
- differentiate Chat and Project clearly

### Don't

- turn the app into a generic AI startup UI
- use gradients as decoration on every screen
- overuse colorful mode accents
- stack cards where layout would be cleaner
- make control surfaces louder than user content

## 17. Immediate Implementation Alignment

These are the first design alignment tasks implied by this file:

1. Align font tokens in `ui/src/index.css` to the canonical Geist decision.
2. Shift base neutrals toward a warm paper-gray chassis and desaturate semantic accents.
3. Reduce any chat-page visual patterns that feel like decorative AI product styling rather than operational UI.
4. Ensure sticky composer separation comes from micro-depth, not heavy card chrome.
5. Ensure all pinned composer actions meet 44px touch target guidance.
6. Standardize chat state surfaces so "error" and "recover" are visibly actionable.
7. Keep motion lightweight and local to content changes.

## 18. Change Management

When adding or changing UI:

- update this file first if the decision affects more than one page
- then update implementation tokens or components
- then update page docs in `docs/ui/*` if interaction or structure changed

If a UI change cannot be justified against this file, it should not ship.
