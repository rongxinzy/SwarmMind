# SwarmMind Design System v2.0

> Status: Canonical design source of truth for `SwarmMind/ui/`
> Last updated: 2026-04-08
> Scope: V1 Supervisor UI, ChatSession + Project Space

## 1. Design Philosophy

### 1.1 Product Character

SwarmMind is a **supervised AI work surface** for exploration, execution, and governance. It is not a generic AI chat shell—it is a control room for human-supervised AI operations.

**Core Identity:**
- Structured work over casual conversation
- Operational clarity over brand spectacle
- Trust and traceability over novelty
- Light exploration in chat, heavier control in project space

**The SwarmMind Feeling:**

Imagine a **modern mission control center** reimagined through the lens of **premium Japanese stationery**—precise, warm, and purposefully designed. The interface balances operational density with human warmth, like a well-organized engineer's notebook: every element has its place, every color serves a function, and white space is used with intention.

Where consumer AI products feel like playgrounds, SwarmMind feels like a **professional cockpit**—trustworthy, efficient, and quietly sophisticated.

### 1.2 Two Modes, One System

| Mode | Purpose | Visual Character |
|------|---------|------------------|
| **ChatSession** | Exploration, drafting, ideation | Lighter shell, softer separation, fast feedback |
| **Project Space** | Formal execution with governance | Dense information, persistent status, explicit controls |

**Golden Rule:** Chat is for exploration. Project is for execution. They must not look interchangeable.

---

## 2. Color System

### 2.1 Design Tokens

SwarmMind uses a **warm neutral chassis** with semantic accents. Every gray has a subtle warm undertone—closer to Notion's paper warmth than Vercel's cold slate.

#### Primary Palette

| Token | Hex | Usage |
|-------|-----|-------|
| `--warm-paper` | `#F7F7F5` | App background, primary canvas |
| `--warm-ivory` | `#FAFAF8` | Elevated cards, panels |
| `--warm-sand` | `#E8E6E0` | Secondary surfaces, button backgrounds |
| `--warm-border` | `#E5E3DD` | Subtle borders, dividers |
| `--warm-ring` | `#D1CFC8` | Interactive ring shadows |

#### Neutral Ladder

| Token | Hex | Usage |
|-------|-----|-------|
| `--neutral-50` | `#FAFAF8` | Lightest surface |
| `--neutral-100` | `#F7F7F5` | Primary background (warm paper) |
| `--neutral-150` | `#F0EEEA` | Elevated utility tint |
| `--neutral-200` | `#E8E6E0` | Secondary panels |
| `--neutral-300` | `#D8D6D0` | Low-contrast borders |
| `--neutral-500` | `#8A8882` | Muted text, placeholders |
| `--neutral-700` | `#5A5852` | Strong secondary text |
| `--neutral-900` | `#1E1E1C` | Primary text (near black) |

#### Semantic Accents (Desaturated)

| State | Color | Hex | Usage |
|-------|-------|-----|-------|
| **Running** | Steel Blue | `#5A7A96` | Active processes, loading states |
| **Approval** | Ochre/Amber | `#B8956F` | Pending approvals, warnings |
| **Blocked** | Terracotta | `#A67C6B` | Errors, blocked states |
| **Done** | Sage | `#7A9A7E` | Success, completed states |
| **Draft** | Warm Gray | `#9A9894` | Draft states, inactive |
| **Chat** | Gray-Violet | `#8A8298` | Exploratory states (subtle use) |

**Accent Rule:** If a semantic color looks like a Bootstrap default, it is too pure. Desaturate by 20-30%.

### 2.2 Usage Rules

#### Surface Hierarchy

```
App Background (#F7F7F5)
    └── Primary Panel (#FAFAF8) — slightly brighter, 1px border
        └── Secondary Panel (#F0EEEA) — soft warm gray
            └── Elevated Utility (#FFFFFF) — pure white only for high-focus inputs
```

#### Anti-Gloss Principles

- **Border first:** Use `1px solid #E5E3DD` to define surfaces. Shadow supports edges, never replaces them.
- **No borderless large-shadow cards:** This creates cheap plastic sheen—off-brand for SwarmMind.
- **Matte and crisp:** Avoid diffused shadows. Blur radius stays small.

#### Dark Mode Mapping

Dark mode is **not** a literal inversion. Target feeling:

- More **charcoal-paper** than black glass
- More **neutral ink** than brown tint
- Still calm and supervised, never neon

| Light | Dark |
|-------|------|
| `#F7F7F5` | `#1A1A18` (warm charcoal) |
| `#FAFAF8` | `#242422` (elevated surface) |
| `#1E1E1C` | `#E8E6E0` (primary text) |

---

## 3. Typography

### 3.1 Font Families

**Canonical V2 Stack:**

| Role | Font | Fallback |
|------|------|----------|
| Display / Headlines | `Geist` | `Inter`, `system-ui` |
| Body / UI | `Geist` | `Inter`, `system-ui` |
| Monospace | `Geist Mono` | `JetBrains Mono`, `Consolas` |

**Rationale:** Geist provides a neutral, modern, operational feel that fits high-density product surfaces better than display-forward alternatives.

### 3.2 Type Scale

| Role | Size | Line Height | Weight | Tracking | Usage |
|------|------|-------------|--------|----------|-------|
| **Display** | 36px | 1.20 | 600 | -0.02em | Page titles |
| **H1** | 28px | 1.30 | 600 | -0.02em | Major sections |
| **H2** | 22px | 1.30 | 600 | -0.01em | Section headers |
| **H3** | 18px | 1.40 | 500 | 0 | Surface titles |
| **Body Large** | 16px | 1.60 | 400 | 0 | Primary content |
| **Body** | 14px | 1.60 | 400 | 0 | Standard text |
| **Body Small** | 13px | 1.50 | 400 | 0 | Dense text |
| **Caption** | 12px | 1.40 | 500 | 0.02em | Metadata |
| **Label** | 11px | 1.20 | 500 | 0.04em | Tags, badges |
| **Code** | 13px | 1.60 | 400 | -0.01em | Monospace content |

### 3.3 Typography Rules

**Headings:**
- Tighten tracking slightly (`-0.02em`) for page titles
- Near-neutral tracking (`-0.01em`) for section titles
- No decorative all-caps except small metadata labels
- Utility-oriented, never oversized hero typography

**Body Text:**
- Default tracking, do not squeeze for style
- Relaxed line-height (1.50–1.60) for reading comfort
- High contrast on all neutral surfaces

**Small Text (11-12px):**
- Add tracking (`0.02em–0.08em`) for readability
- Uppercase labels use positive tracking

---

## 4. Spacing & Layout

### 4.1 Spacing Scale (4px Base)

```
4px   — Tightest
8px   — Tight
12px  — Compact
16px  — Standard
20px  — Comfortable
24px  — Spacious
32px  — Generous
40px  — Section gaps
48px  — Major sections
```

### 4.2 Surface Padding

| Element | Padding |
|---------|---------|
| Small controls | 8–12px |
| Standard card / panel | 16px |
| Large panel / composer | 20–24px |
| Message bubbles | 16–24px horizontal, 12–20px vertical |

### 4.3 Vertical Rhythm

| Context | Gap |
|---------|-----|
| Tight clusters (same block) | 8–12px |
| Between semantic blocks | 16–20px |
| Major page sections | 24–32px |

### 4.4 Layout Principles

**App Shell:**
- Fixed sidebar for navigation
- Sticky top header where needed
- Central work surface
- Optional right-side contextual area

**Layout over Cards:**
- Default to layout first
- Cards only for semantic containers: settings groups, state summaries, message bubbles, composers, artifacts
- Do not solve composition problems by wrapping everything in cards

---

## 5. Components

### 5.1 Buttons

**Primary Button (Warm Sand)**
```css
background: #E8E6E0;
color: #1E1E1C;
padding: 8px 16px;
border-radius: 10px;
border: 1px solid #D8D6D0;
/* Ring shadow on hover */
box-shadow: 0 0 0 1px #D1CFC8;
```

**Secondary Button (Ghost)**
```css
background: transparent;
color: #5A5852;
padding: 8px 16px;
border-radius: 10px;
border: 1px solid #E5E3DD;
/* Hover: subtle fill */
```

**Brand Button (Caution: Sparingly)**
```css
background: #5A7A96;  /* Steel blue variant */
color: #FAFAF8;
padding: 8px 16px;
border-radius: 10px;
/* Use only for primary CTAs */
```

**Button Rules:**
- Compact and decisive primary actions
- Secondary buttons must not compete visually
- Icon-only buttons: minimum 44px touch target

### 5.2 Cards & Panels

**Standard Card:**
```css
background: #FAFAF8;
border: 1px solid #E5E3DD;
border-radius: 14px;
padding: 16px;
```

**Elevated Card:**
```css
background: #FFFFFF;
border: 1px solid #E5E3DD;
border-radius: 16px;
box-shadow: 0 4px 12px rgba(0,0,0,0.04);
padding: 20px;
```

**Panel Hierarchy:**
- Signal hierarchy through spacing and border strength, not color
- Avoid glassmorphism and heavy blur as visual identity
- Pinned bars may use low-opacity blur for separation

### 5.3 Border Radius Scale

| Element | Radius |
|---------|--------|
| Inputs, buttons | 10–12px |
| Standard cards | 14–16px |
| Large floating panels | 18–20px |
| Message bubbles | 20–24px |
| Composer | 20–24px |

**Rule:** Radius expresses hierarchy, not style-for-style's-sake.

### 5.4 Input Fields

**Text Input:**
```css
background: #FFFFFF;
border: 1px solid #D8D6D0;
border-radius: 12px;
padding: 10px 14px;
color: #1E1E1C;
/* Focus state */
border-color: #5A7A96;
box-shadow: 0 0 0 3px rgba(90,122,150,0.1);
```

**Focus State Rules:**
- Never rely on default browser blue outline
- One calm primary cue + one secondary cue
- Stay within warm-neutral system
- Focus should feel clearer, not louder

### 5.5 Chips & Badges

- Use for state and scope
- Keep text short (1–2 words)
- Avoid rainbow badge clusters
- Maximum one semantic color per area

### 5.6 Code Blocks

Code blocks are core texture surfaces—they must look engineered, not like generic text cards.

```css
/* Container */
background: #1E1E1E;  /* Dark neutral inversion */
border-radius: 10px;
overflow: hidden;

/* Header */
background: #2A2A2A;
padding: 10px 16px;
border-bottom: 1px solid #3A3A3A;

/* Code area */
font-family: 'Geist Mono', monospace;
font-size: 13px;
line-height: 1.60;
padding: 16px;
```

**Code Block Rules:**
- Background: Dark neutral (`#1E1E1E`) or cool `neutral-150`
- Typography: `Geist Mono`, 13px, 1.5 line-height
- Header: 32–36px height, language label (11px uppercase)
- Syntax highlighting: Low-saturation, cold-neutral (no neon themes)
- Radius: 8–10px (engineered, not bubbly)

---

## 6. Elevation & Depth

### 6.1 Shadow System

| Level | Treatment | Use Case |
|-------|-----------|----------|
| **Flat (0)** | No shadow, no border | Background, inline text |
| **Contained (1)** | `1px solid #E5E3DD` | Standard cards, sections |
| **Ring (2)** | `0 0 0 1px #D1CFC8` | Interactive cards, buttons |
| **Whisper (3)** | `0 4px 12px rgba(0,0,0,0.04)` | Elevated cards |
| **Sticky (4)** | `0 -2px 20px rgba(0,0,0,0.06)` | Sticky composer |

### 6.2 Shadow Philosophy

- Most surfaces: very soft or no visible shadow
- Border defines the surface; shadow only supports
- No diffused shadows—blur radius stays small
- Matte and crisp, never consumer-product gloss

### 6.3 Micro-Depth Tools

**Allowed:**
- Low-contrast border
- Subtle tonal separation between stacked neutrals
- One restrained shadow
- Selective `backdrop-blur` on sticky surfaces

**Forbidden:**
- Glassmorphism as page identity
- Frosted panels everywhere
- Dark heavy shadow stacks
- Blur used only for decoration

---

## 7. Motion

### 7.1 Allowed Motion

SwarmMind allows **small, breathable motion**—not attention-seeking motion.

**Allowed:**
- Soft fade-in on entering content (180–260ms)
- Subtle translateY for new messages (8–16px)
- Hover and focus transitions (120–180ms)
- Lightweight streaming indicators
- Controlled sticky surface transitions
- Low-amplitude accordion motion

### 7.2 Forbidden Motion

- Decorative looping background animation
- Large parallax or scene-level motion
- Dramatic multi-stage entrance choreography
- Motion used only to signal "AI-ness"
- Motion competing with text input or status reading

### 7.3 Timing Rules

| Type | Duration |
|------|----------|
| Micro transitions | 120–180ms |
| Standard content | 180–260ms |
| Page-level | 300–400ms |

**Rule:** Only one "strong" motion event visible at a time in a local region.

### 7.4 Motion Purpose Test

Every animation must answer one of:
- What changed?
- Where did it go?
- What should I notice?

If it answers none, cut it.

---

## 8. ChatSession Specific Rules

### 8.1 Job of the Page

The chat page is a **lightweight exploratory work surface**. Its primary job is helping users start work quickly.

**Not:**
- A consumer AI playground
- A mode gallery
- A prompt template showcase
- A brand statement page

### 8.2 Visual Hierarchy

1. Input / composer
2. Active conversation content
3. Current execution state
4. Optional starter prompts
5. Secondary controls

**Rule:** If the eye lands on anything before the composer in an empty chat, hierarchy is wrong.

### 8.3 Empty State

- Compact and warm, not theatrical
- One restrained monochrome icon
- Short title + one-line explanation
- Visible primary composer
- 2–4 starter prompts maximum
- Warmth from whitespace, type rhythm, soft neutrals

**Avoid:**
- Oversized intro blocks
- Large decorative hero treatment
- Multiple competing callouts

### 8.4 Composer Design

The composer is the **anchor of the page**:

- Remains visible while reading history
- Reads as primary working surface
- Status and model controls belong to composer region
- Controls beneath textarea feel secondary
- Sticky separation: subtle warm tint + restrained shadow

**Focus State:**
```css
border-color: #C8C6C0;
box-shadow: 0 0 0 3px rgba(90,122,150,0.08),
            0 4px 20px rgba(0,0,0,0.06);
```

### 8.5 Message Stream

- Optimize for readability over ornament
- Left/right alignment is enough
- Markdown rhythm matters more than bubble decoration
- New message motion: subtle (translateY 8px, fade)
- Assistant replies: annotated document feel, not chat toy
- Long answers: continuous content, not stacked decorated bubbles

### 8.6 Status States

**Required:**
- Model loading
- Conversation loading
- Streaming
- Success / completed
- Failed with retry path
- No available model

**Rule:** Every error state tells the user what they can do next.

---

## 9. Project Space Specific Rules

### 9.1 Visual Character

- More formal structure
- Denser information
- Persistent status visibility
- Explicit governance surfaces
- Stronger page chrome and sectional framing

### 9.2 Information Density

- Medium-high density
- Efficient, not cramped
- Status badges visible at glance
- Approval workflows explicit
- Artifacts and audit trails accessible

---

## 10. Iconography

### 10.1 Icon Rules

- Default to linear icons with restrained geometry
- Consistent `1.5px` stroke feel across product
- Corners and joins aligned with Geist's rational skeleton
- Monochrome by default; state color only for meaning
- Do not mix unrelated icon families

**Test:** If an icon looks softer/rounder than surrounding type, it is wrong.

### 10.2 Lucide Icons (Recommended)

SwarmMind uses Lucide icons for consistency:
- `lucide-react` for React components
- Stroke width: 1.5px default
- Size: 16px (small), 20px (default), 24px (large)

---

## 11. Accessibility

### 11.1 Non-Negotiable

- Touch targets: 44px minimum
- Keyboard-reachable controls
- Visible focus states
- Semantic headings and landmarks
- Status changes readable without color alone
- High contrast on all neutral surfaces

### 11.2 Chat Specific

- Composer controls keyboard-usable
- Status text concise and persistent
- Hover-only affordances have keyboard fallback

---

## 12. Content Tone

SwarmMind copy should sound **operational and calm**.

**Prefer:**
- "输入问题或任务"
- "等待新的输入"
- "会话执行失败"
- "回到最新"

**Avoid:**
- Hype language
- Whimsical assistant personality
- Decorative slogans

---

## 13. Implementation Reference

### 13.1 CSS Variables Template

```css
:root {
  /* Warm Neutrals */
  --warm-paper: #F7F7F5;
  --warm-ivory: #FAFAF8;
  --warm-sand: #E8E6E0;
  --warm-border: #E5E3DD;
  --warm-ring: #D1CFC8;

  /* Neutral Ladder */
  --neutral-50: #FAFAF8;
  --neutral-100: #F7F7F5;
  --neutral-150: #F0EEEA;
  --neutral-200: #E8E6E0;
  --neutral-300: #D8D6D0;
  --neutral-500: #8A8882;
  --neutral-700: #5A5852;
  --neutral-900: #1E1E1C;

  /* Semantic */
  --status-running: #5A7A96;
  --status-approval: #B8956F;
  --status-blocked: #A67C6B;
  --status-done: #7A9A7E;
  --status-draft: #9A9894;

  /* Typography */
  --font-sans: 'Geist', 'Inter', system-ui, sans-serif;
  --font-mono: 'Geist Mono', 'JetBrains Mono', Consolas, monospace;

  /* Spacing */
  --space-1: 4px;
  --space-2: 8px;
  --space-3: 12px;
  --space-4: 16px;
  --space-5: 20px;
  --space-6: 24px;
  --space-8: 32px;
  --space-10: 40px;
  --space-12: 48px;

  /* Radius */
  --radius-sm: 8px;
  --radius-md: 10px;
  --radius-lg: 14px;
  --radius-xl: 18px;
  --radius-2xl: 24px;

  /* Shadows */
  --shadow-ring: 0 0 0 1px var(--warm-ring);
  --shadow-whisper: 0 4px 12px rgba(0,0,0,0.04);
  --shadow-sticky: 0 -2px 20px rgba(0,0,0,0.06);
}
```

### 13.2 Tailwind Config Additions

```javascript
// tailwind.config.js
module.exports = {
  theme: {
    extend: {
      colors: {
        warm: {
          paper: '#F7F7F5',
          ivory: '#FAFAF8',
          sand: '#E8E6E0',
          border: '#E5E3DD',
          ring: '#D1CFC8',
        },
        neutral: {
          50: '#FAFAF8',
          100: '#F7F7F5',
          150: '#F0EEEA',
          200: '#E8E6E0',
          300: '#D8D6D0',
          500: '#8A8882',
          700: '#5A5852',
          900: '#1E1E1C',
        },
        status: {
          running: '#5A7A96',
          approval: '#B8956F',
          blocked: '#A67C6B',
          done: '#7A9A7E',
          draft: '#9A9894',
        },
      },
      fontFamily: {
        sans: ['Geist', 'Inter', 'system-ui', 'sans-serif'],
        mono: ['Geist Mono', 'JetBrains Mono', 'Consolas', 'monospace'],
      },
      boxShadow: {
        'ring': '0 0 0 1px #D1CFC8',
        'whisper': '0 4px 12px rgba(0,0,0,0.04)',
        'sticky': '0 -2px 20px rgba(0,0,0,0.06)',
      },
    },
  },
}
```

---

## 14. Do / Don't

### ✅ Do

- Use semantic state colors consistently
- Keep product surfaces calm
- Let spacing and hierarchy do visual work
- Use restrained motion for breathing room
- Differentiate Chat and Project clearly
- Choose Geist as the canonical typeface
- Keep neutrals warm-toned
- Use ring shadows for interactive states
- Maintain generous body line-height (1.50–1.60)
- Apply thoughtful border-radius (soft, approachable)

### ❌ Don't

- Turn the app into generic AI startup UI
- Use gradients as decoration on every screen
- Overuse colorful mode accents
- Stack cards where layout would be cleaner
- Make control surfaces louder than user content
- Use cool blue-grays in the neutral palette
- Apply heavy drop shadows
- Use pure white as page background
- Reduce body line-height below 1.40
- Use decorative looping animations

---

## 15. Change Management

When adding or changing UI:

1. **Update this file first** if the decision affects more than one page
2. **Update implementation tokens** or components
3. **Update page docs** in `docs/ui/*` if interaction changed

**Rule:** If a UI change cannot be justified against this file, it should not ship.

---

## 16. Implementation Checklist

### Immediate Alignment Tasks

- [ ] Align font tokens to Geist (remove Space Grotesk drift)
- [ ] Implement warm paper-gray chassis (`#F7F7F5`)
- [ ] Desaturate semantic accents per §2.1
- [ ] Reduce decorative chat-page patterns
- [ ] Implement sticky composer with micro-depth
- [ ] Ensure 44px touch targets on composer actions
- [ ] Standardize chat state surfaces (error, recover)
- [ ] Keep motion lightweight and local

### Component Audit

- [ ] Buttons follow §5.1 specifications
- [ ] Cards use correct radius and borders
- [ ] Code blocks match §5.6 requirements
- [ ] Input focus states follow §5.4
- [ ] Shadows follow §6.1 elevation system

---

*End of Design System v2.0*
