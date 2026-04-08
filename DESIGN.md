# SwarmMind Design System v3.0

> Status: Canonical design source of truth for `ui/` and `docs/ui/*`
> Last updated: 2026-04-08
> Scope: Workbench, ChatSession, Project Space, Approval and governance surfaces
> Rule: If implementation conflicts with this file, implementation must be refactored

---

## 1. Design Intent

### 1.1 Product Role

SwarmMind is a supervised AI work surface for exploration, execution, and governance.
It is not a generic AI chat shell, and it is not project management with a chatbot bolted on.

The product must always communicate four things:

- Structured work over casual conversation
- Human supervision over autonomous spectacle
- Traceable execution over fuzzy magic
- Warm operational clarity over cold technical theater

### 1.2 Visual Thesis

The canonical SwarmMind feeling is:

**A calm operations studio drawn on warm engineering paper.**

The interface should feel like a control room designed by people who value notebooks, margin rhythm, and auditability. It should read as precise and trustworthy, but never sterile. It is closer to a premium field manual than a glossy SaaS dashboard.

This means:

- Warm neutral surfaces, never icy blue-gray foundations
- Clear structural borders, never floating plastic cards everywhere
- Editorial typography moments for authority, but functional UI text for dense work
- Strong page hierarchy driven by spacing, rhythm, and containment
- Status visibility that feels sober and readable, not alarmist

### 1.3 Keywords

The visual language should consistently score high on these keywords:

- Calm
- Exact
- Warm
- Supervised
- Editorial
- Intentional
- Dense but breathable

### 1.4 What Users Should Remember

If a user remembers only one thing about SwarmMind's UI, it should be:

**"This feels like serious AI work happening on beautifully organized paper."**

### 1.5 Modes and Visual Separation

SwarmMind has three visual situations. They are related, but they must not feel interchangeable.

| Surface | Job | Character | Density |
|---------|-----|-----------|---------|
| `ChatSession` | Explore, clarify, draft, probe | Softer containment, faster entry, more breathing room around the composer | Medium |
| `Project Space` | Execute, coordinate, review, track | Stronger chrome, persistent status, more sectional framing | Medium-high |
| `Governance / Approval` | Pause, decide, unblock, audit | Highest contrast in hierarchy, explicit consequences, minimal decorative detail | High |

### 1.6 Non-Goals

SwarmMind should not become any of the following:

- A playful consumer AI playground
- A neon futuristic command center
- A glassmorphism-heavy startup dashboard
- A generic shadcn demo with warm colors
- A marketing site aesthetic pasted onto a work product

---

## 2. Visual Theme and Atmosphere

### 2.1 Atmosphere

The overall atmosphere is **warm operational clarity**.

Design reference, in words rather than brands:

- The paper warmth of a premium notebook
- The crisp containment of industrial control labels
- The pacing of an editorial layout
- The restraint of enterprise software that respects the user's attention

### 2.2 Signature Moves

SwarmMind should rely on a few repeatable signature moves rather than many decorative tricks.

#### Signature Move A: Warm Paper Chassis

The app shell is built on warm paper and ivory surfaces, not pure white.

- Primary canvas is slightly warm
- Elevated surfaces are brighter, not louder
- Large areas of pure white are reserved for high-focus inputs and specific reading surfaces

#### Signature Move B: Border-First Containment

Borders define structure before shadows do.

- Large surfaces need a clear edge
- Ring shadows are preferred over soft drop shadows
- If a surface only exists because of a shadow, the design is wrong

#### Signature Move C: Editorial Headline Moments

The UI is functional first, but it earns selective editorial headline moments.

- Page titles
- Empty-state titles
- Approval headlines
- Major section anchors

These moments can use a serif display face. Dense controls, tables, chips, tabs, and inline metadata should not.

#### Signature Move D: Stateful Warm Accents

Semantic colors should feel desaturated and operational.

- Running is steel blue, not electric blue
- Approval is ochre, not warning yellow
- Blocked is terracotta, not saturated red
- Done is sage, not bright green

#### Signature Move E: Quiet Motion

Motion should explain change, not perform intelligence.

- Streaming is subtle
- Entry transitions are soft
- Sticky elements breathe, they do not float theatrically

### 2.3 Background Strategy

Backgrounds should create structure, not spectacle.

Allowed:

- Gentle tonal separation between shell and surface
- Soft vertical gradients for sticky zones
- Very subtle paper-noise or grain only if it is nearly imperceptible

Forbidden:

- Loud mesh gradients
- Decorative aurora backgrounds
- Animated particle fields
- Purple-on-white startup gradients

### 2.4 Dark Mode Philosophy

Dark mode is not an inversion. It should feel like **charcoal paper and neutral ink**.

Dark mode must preserve the same product personality:

- Warm charcoal instead of black glass
- Ivory text instead of stark white
- Strong containment through borders and tonal separation
- Accents remain muted and supervised

---

## 3. Color Architecture

### 3.1 Core Palette

#### Chassis Neutrals

| Token | Hex | Role |
|-------|-----|------|
| `--warm-paper` | `#F7F7F5` | Primary app background |
| `--warm-ivory` | `#FAFAF8` | Elevated panels and cards |
| `--warm-mist` | `#F0EEEA` | Utility surfaces and soft separators |
| `--warm-sand` | `#E8E6E0` | Secondary controls and tactile surfaces |
| `--warm-border` | `#E5E3DD` | Standard borders |
| `--warm-ring` | `#D1CFC8` | Ring shadow and interactive containment |

#### Neutral Ladder

| Token | Hex | Role |
|-------|-----|------|
| `--neutral-50` | `#FAFAF8` | Lightest surface |
| `--neutral-100` | `#F7F7F5` | Base canvas |
| `--neutral-150` | `#F0EEEA` | Muted fill |
| `--neutral-200` | `#E8E6E0` | Secondary surface |
| `--neutral-300` | `#D8D6D0` | Visible border / quiet dividers |
| `--neutral-400` | `#B8B6B0` | Disabled text and icons |
| `--neutral-500` | `#8A8882` | Tertiary text |
| `--neutral-600` | `#6A6862` | Secondary text |
| `--neutral-700` | `#5A5852` | Strong secondary text |
| `--neutral-800` | `#3A3832` | Dense labels, table emphasis |
| `--neutral-900` | `#1E1E1C` | Primary text |

#### Semantic Signals

| State | Token | Hex | Role |
|-------|-------|-----|------|
| Running | `--status-running` | `#5A7A96` | Active process, streaming, current execution |
| Approval | `--status-approval` | `#B8956F` | Pending decision, caution, handoff |
| Blocked | `--status-blocked` | `#A67C6B` | Failure, blocked execution, invalid state |
| Done | `--status-done` | `#7A9A7E` | Success, completion, healthy resolved state |
| Draft | `--status-draft` | `#9A9894` | Inactive, placeholder, not-started |
| Chat | `--status-chat` | `#8A8298` | Exploratory states only, sparing use |

#### Semantic Backgrounds

| Token | Hex |
|-------|-----|
| `--status-running-bg` | `#EEF1F4` |
| `--status-running-border` | `#D5DCE3` |
| `--status-approval-bg` | `#F5F0EA` |
| `--status-approval-border` | `#E5DDD3` |
| `--status-blocked-bg` | `#F3EEEB` |
| `--status-blocked-border` | `#E3D9D3` |
| `--status-done-bg` | `#EDF2EE` |
| `--status-done-border` | `#D5E0D7` |
| `--status-chat-bg` | `#F0EEF3` |
| `--status-chat-border` | `#E0DCE6` |
| `--status-draft-bg` | `#F2F2F0` |
| `--status-draft-border` | `#E5E5E3` |

### 3.2 Color Roles

Use color by responsibility, not by decoration.

| Role | Rule |
|------|------|
| Chassis color | Defines canvas and containment |
| Ink color | Defines reading hierarchy |
| Semantic color | Defines state and consequence |
| Accent color | Reserved for narrow high-signal moments |

Operational rule:

- Any local area should usually contain at most one semantic color family
- If multiple semantic colors appear in the same card or row, hierarchy is likely broken

### 3.3 Surface Hierarchy

```text
App Background (#F7F7F5)
    -> Primary Surface (#FAFAF8)
        -> Utility Surface (#F0EEEA)
            -> High-Focus Input (#FFFFFF)
```

Rules:

- Large layout regions should differ mainly by tone and border
- White should feel earned, not default
- Secondary surfaces should not become a patchwork of many grays

### 3.4 Dark Mode Mapping

| Light Role | Light | Dark |
|------------|-------|------|
| App background | `#F7F7F5` | `#1A1A18` |
| Primary surface | `#FAFAF8` | `#242422` |
| Utility surface | `#F0EEEA` | `#2C2C29` |
| Primary text | `#1E1E1C` | `#E8E6E0` |
| Secondary text | `#5A5852` | `#B7B4AE` |
| Standard border | `#E5E3DD` | `#3A3935` |

Dark mode rules:

- Do not increase saturation in dark mode
- Do not use neon signal colors
- Do not switch to blue-gray as the base chassis

### 3.5 Color Budget

Per local view, keep the budget disciplined:

- One chassis family
- One text ladder
- One active semantic family
- Optional one accent family for CTA emphasis

If a page needs many colors to feel organized, its information architecture is failing.

### 3.6 Forbidden Color Habits

- Cool gray as base neutral
- Bright cyan, lime, or saturated magenta signals
- Generic purple gradients
- Pure black backgrounds on product pages
- Pure white full-page canvases

---

## 4. Typography

### 4.1 Canonical Font Stack

SwarmMind uses a split system:

| Role | Primary | Fallback |
|------|---------|----------|
| Display / Editorial heading | `Newsreader` | `Source Han Serif SC`, `Noto Serif SC`, `Georgia`, serif |
| Body / UI / Navigation | `Geist` | `PingFang SC`, `Hiragino Sans GB`, `Noto Sans SC`, `Microsoft YaHei`, sans-serif |
| Monospace | `Geist Mono` | `SFMono-Regular`, `IBM Plex Mono`, `Menlo`, `Consolas`, monospace |

Rationale:

- `Newsreader` gives SwarmMind a distinctive editorial authority without becoming theatrical
- `Geist` keeps dense controls rational and contemporary
- `Geist Mono` supports code, logs, and run metadata

### 4.2 Where Serif Is Allowed

Serif is a highlight, not a blanket rule.

Allowed:

- Page titles
- Empty-state titles
- Major section anchors
- Approval decision headlines
- Short dashboard stat headlines

Not allowed:

- Dense nav items
- Table headers in data-heavy grids
- Form labels
- Chips, badges, tabs, inline controls
- Paragraph-heavy assistant output by default

### 4.3 Type Scale

| Role | Font | Size | Line Height | Weight | Tracking | Usage |
|------|------|------|-------------|--------|----------|-------|
| Display | Serif | 40px | 1.15 | 500 | -0.02em | Main page title |
| H1 | Serif | 32px | 1.20 | 500 | -0.02em | Major section title |
| H2 | Serif | 24px | 1.25 | 500 | -0.01em | Section anchor |
| H3 | Sans | 20px | 1.35 | 600 | -0.01em | Surface title |
| Body Large | Sans | 16px | 1.65 | 400 | 0 | Intro copy, descriptive text |
| Body | Sans | 14px | 1.60 | 400 | 0 | Standard product text |
| Body Small | Sans | 13px | 1.55 | 400 | 0 | Dense UI text |
| Caption | Sans | 12px | 1.45 | 500 | 0.02em | Metadata |
| Label | Sans | 11px | 1.30 | 500 | 0.05em | Badges, field labels |
| Micro | Sans | 10px | 1.30 | 500 | 0.06em | Timestamp, tiny utilities |
| Code | Mono | 13px | 1.60 | 400 | -0.01em | Code and logs |

### 4.4 Typography Rules

#### Headings

- Headings should feel authored, not generated
- Tight tracking is allowed on titles
- Headlines should usually be short and direct
- Avoid oversized hero type in product surfaces

#### Body Copy

- Reading comfort matters more than compression
- 14px with 1.60 line height is the default product reading rhythm
- 13px is allowed in dense metadata zones, but not for primary explanations

#### Labels and Metadata

- Small labels should use positive tracking
- Uppercase is allowed only for small metadata or system labeling
- If everything becomes uppercase, the UI loses calmness

### 4.5 Bilingual Rules

SwarmMind contains Chinese and English content. The system must handle both cleanly.

#### Rhythm and Spacing

| Element | English | Chinese | Notes |
|---------|---------|---------|-------|
| Body line height | 1.60 | 1.75–1.80 | CJK characters need more breathing room |
| Heading line height | 1.15–1.25 | 1.30–1.40 | Prevent stacked characters from touching |
| Paragraph spacing | 1em | 1.2em | Visual separation for dense CJK text |

#### Typography Rules

- **Do not force all-uppercase on Chinese labels** — it is illegible and looks broken
- **Mixed-language headings** should prefer sans if the serif rendering becomes inconsistent
- **English technical terms** may remain inline when they are product vocabulary, for example `ChatSession`, `Project`, `Run`, `Artifact`
- **Avoid inline English words in Chinese body text** unless they are established product terms

#### Punctuation and Spacing

| Situation | Rule | Example |
|-----------|------|---------|
| Chinese text with English | Add hair space around English words | 启动 ChatSession 以开始工作 |
| Numbers in Chinese | Use full-width punctuation before/after | 共 15 个项目 |
| Parentheses | Prefer full-width `（）` for Chinese context | （参见上文） |
| Colons in labels | Use full-width `：` | 状态：运行中 |

#### Font Stack Adjustments for Chinese

```css
/* For Chinese-heavy content, slightly loosen the rhythm */
.chinese-body {
  font-family: "Geist", "PingFang SC", "Hiragino Sans GB", "Noto Sans SC", sans-serif;
  line-height: 1.75;
  letter-spacing: 0.02em;  /* Slight tracking for CJK readability */
}

/* Headings with Chinese should use tighter weight */
.chinese-heading {
  font-weight: 600;  /* Avoid 700+ which looks heavy in CJK */
}
```

#### Character Counts for Readability

| Context | English | Chinese | Max Width |
|---------|---------|---------|-----------|
| Optimal line length | 45–75 chars | 25–35 chars | ~680px |
| Comfortable reading | Up to 90 chars | Up to 40 chars | ~800px |
| Dense UI labels | 2–4 words | 2–6 characters | — |

---

## 5. Layout, Spacing, and Density

### 5.1 Shell Blueprint

Desktop web is the baseline.

```text
+------------------------------------------------------------------------------------------------------------------+
| Left Navigation 264-288 | Main Content min 720 | Context Rail 320-360 |
+------------------------------------------------------------------------------------------------------------------+
```

Recommended shell behavior:

- Left navigation is persistent
- Top bar stays compact and useful
- Main content carries the current task
- Right rail holds context, run state, approvals, artifacts, or detail panels

### 5.2 Spacing Scale

SwarmMind uses a 4px base.

| Token | Size | Usage |
|------|------|-------|
| `space-1` | 4px | Tightest alignment |
| `space-2` | 8px | Inline gaps |
| `space-3` | 12px | Compact grouping |
| `space-4` | 16px | Standard padding and gaps |
| `space-5` | 20px | Comfortable grouping |
| `space-6` | 24px | Spacious panel padding |
| `space-8` | 32px | Section gap |
| `space-10` | 40px | Large section break |
| `space-12` | 48px | Page-level break |

### 5.3 Density Bands

| Context | Density | Notes |
|---------|---------|------|
| Workbench | Medium | Scanable, summary-forward |
| ChatSession | Medium | Composer-first, readable stream |
| Project Space | Medium-high | Persistent context and execution status |
| Approval / Audit | High | Dense facts, explicit consequence framing |

### 5.4 Padding Rules

| Element | Padding |
|---------|---------|
| Small button | `8px 12px` |
| Standard button | `10px 14px` |
| Card / panel | `16px` |
| Elevated panel | `20px` |
| Large composer | `20px 20px 16px` |
| Table cell | `10px 12px` |

### 5.5 Rhythm Rules

Use spacing to express semantic structure.

- Inside a semantic block: `8px` to `12px`
- Between related blocks: `16px` to `20px`
- Between major sections: `24px` to `32px`
- Between page zones: `32px` to `48px`

If a surface needs many dividers because spacing is not carrying hierarchy, spacing is wrong.

### 5.6 Desktop-First Responsive Policy

Current product commitment is desktop web, not mobile product design.

Rules:

- Support laptop widths cleanly
- On narrow windows, collapse secondary rails before damaging the main work area
- Do not introduce mobile-only navigation patterns as a product promise
- Small-screen tolerance is allowed; mobile-first redesign is not in scope

---

## 6. Surfaces, Borders, Radius, and Depth

### 6.1 Surface Levels

| Level | Treatment | Usage |
|-------|-----------|------|
| `0 Flat` | No shadow, no raised border | Base canvas |
| `1 Contained` | `1px solid var(--warm-border)` | Standard sections and cards |
| `2 Ring` | `0 0 0 1px var(--warm-ring)` | Interactive emphasis |
| `3 Whisper` | `0 4px 12px rgba(0,0,0,0.04)` | Elevated card or floating utility |
| `4 Sticky` | `0 -2px 20px rgba(0,0,0,0.06)` | Sticky composer / sticky bars |

### 6.2 Shadow Philosophy

- Border defines the object
- Shadow supports, never replaces, containment
- Most surfaces should feel matte
- Large blurred shadows read as cheap gloss and are off-brand

### 6.3 Border Radius Scale

| Element | Radius |
|---------|--------|
| Inline small control | 8px |
| Button / input | 10px to 12px |
| Standard card | 14px |
| Large panel | 16px to 18px |
| Composer / prominent container | 20px to 24px |

Rule:

- Radius communicates hierarchy, not softness for its own sake
- If everything is equally rounded, the UI loses structure

### 6.4 Texture Rules

Allowed:

- Tonal separation
- Ring shadows
- Very faint divider lines
- Extremely subtle grain if it behaves like paper texture, not noise art

Forbidden:

- Glassmorphism as a product identity
- Frosted everything
- Multilayer heavy shadow stacks
- Ornamental borders that fight content

---

## 7. Component Grammar

### 7.1 Buttons

#### Primary Action

Default primary action should feel compact, deliberate, and trustworthy.

```css
background: #1E1E1C;
color: #FAFAF8;
border: 1px solid #1E1E1C;
border-radius: 12px;
padding: 10px 14px;
```

Usage:

- Highest-priority action in a local region
- Usually one per panel header or composer zone

#### Secondary Action

```css
background: #E8E6E0;
color: #1E1E1C;
border: 1px solid #D8D6D0;
border-radius: 12px;
padding: 10px 14px;
box-shadow: 0 0 0 1px #D1CFC8;
```

Usage:

- Safe default action
- Most toolbar and card-level actions

#### Ghost Action

```css
background: transparent;
color: #5A5852;
border: 1px solid #E5E3DD;
border-radius: 12px;
padding: 10px 14px;
```

Usage:

- Secondary controls
- Table or row actions
- Quiet utility actions

Button rules:

- Keep button copy short and operational
- Icon-only buttons must preserve a 44px touch target
- Avoid chromatic CTA buttons unless the flow truly needs extra urgency

### 7.2 Inputs and Composer

Text input and composer are high-trust surfaces.

```css
background: #FFFFFF;
color: #1E1E1C;
border: 1px solid #D8D6D0;
border-radius: 12px;
padding: 10px 14px;
```

Focus state:

```css
border-color: #C8C6C0;
box-shadow:
  0 0 0 3px rgba(90, 122, 150, 0.10),
  0 4px 20px rgba(0, 0, 0, 0.06);
```

Composer rules:

- The composer is the anchor of ChatSession
- Model picker, status, and send action belong in the composer zone
- A sticky composer may use a soft vertical gradient and sticky shadow, but never a theatrical floating tray

### 7.3 Cards and Panels

Standard card:

```css
background: #FAFAF8;
border: 1px solid #E5E3DD;
border-radius: 14px;
padding: 16px;
```

Elevated panel:

```css
background: #FFFFFF;
border: 1px solid #E5E3DD;
border-radius: 18px;
padding: 20px;
box-shadow: 0 4px 12px rgba(0,0,0,0.04);
```

Rules:

- Solve layout with structure before adding more cards
- Do not wrap every object in its own bordered box
- Panels should be grouped by meaning, not by implementation convenience

### 7.4 Badges and Status Pills

Status pills are functional metadata, not decoration.

Rules:

- Use short labels
- Match pill text, border, and background within one semantic family
- Avoid rainbow clusters
- In a tight area, one semantic pill is usually enough

### 7.5 Tabs, Lists, and Tables

#### Tabs

- Tabs should feel like structural switches, not playful chips
- Default to underline, border, or soft fill distinctions
- Avoid over-rounded segmented-control aesthetics unless the flow is conversational

#### Lists

- Prefer row dividers over nested cards
- Secondary metadata should align consistently
- Hover should clarify affordance, not repaint the whole row

#### Tables

- Use them when comparability matters
- Header typography stays sans
- Sorting and filtering controls must feel quieter than the data itself

### 7.6 Code Blocks and Logs

Code blocks are engineered texture surfaces.

```css
background: #1A1A1A;
border: 1px solid #282828;
border-radius: 10px;
overflow: hidden;
```

Header:

```css
background: #141414;
border-bottom: 1px solid rgba(255,255,255,0.05);
min-height: 36px;
padding: 0 14px;
font-family: "Geist Mono", monospace;
font-size: 10px;
letter-spacing: 0.1em;
text-transform: uppercase;
```

Code rules:

- Low-saturation syntax only
- No neon themes
- Body line-height stays around `1.60`
- Action buttons remain compact and quiet

### 7.7 Empty, Loading, and Error States

#### Empty State

- Compact
- Warm
- One clear next step
- No giant hero illustration inside product work surfaces

#### Loading State

- Prefer skeletons or localized progress indicators
- Avoid full-page loading theater when only one panel is changing

#### Error State

- Explain what failed
- Explain what the user can do next
- Provide retry or back-out path when possible
- Avoid vague copy like "something went wrong"

---

## 8. Motion

### 8.1 Allowed Motion

- Fade and slight translate on new content
- Hover and focus transitions
- Streaming indicators with restrained amplitude
- Sticky composer settling
- Accordion expand/collapse with clear spatial logic

### 8.2 Forbidden Motion

- Decorative looping backgrounds
- Overproduced AI-themed motion
- Large parallax scenes
- Multi-stage reveal choreography inside dense work surfaces
- Motion that competes with reading or typing

### 8.3 Timing

| Type | Duration |
|------|----------|
| Micro interaction | `120ms` to `180ms` |
| Standard surface transition | `180ms` to `260ms` |
| Page-level shift | `280ms` to `360ms` |

### 8.4 Easing Functions

Use standard easing curves for consistent motion personality:

| Name | Curve | Usage |
|------|-------|-------|
| `ease-standard` | `cubic-bezier(0.4, 0, 0.2, 1)` | Default for most transitions — enters with slight deceleration |
| `ease-decelerate` | `cubic-bezier(0, 0, 0.2, 1)` | Elements entering the view — soft arrival |
| `ease-accelerate` | `cubic-bezier(0.4, 0, 1, 1)` | Elements exiting — quick departure, less attention |
| `ease-spring` | `cubic-bezier(0.34, 1.56, 0.64, 1)` | Playful moments only — toggle switches, celebratory feedback |

Rules:

- Prefer `ease-standard` for 80% of transitions
- Avoid `ease-spring` in dense operational surfaces
- Never use linear easing for UI motion — it feels mechanical

### 8.4 Motion Test

Every animation must answer at least one of these:

- What changed?
- Where did it go?
- What should I notice?

If it answers none, remove it.

---

## 9. Page-Specific Rules

### 9.1 Workbench

Workbench is not a marketing homepage.

Its job:

- Surface what needs attention
- Show active work and recent work
- Provide immediate entry into `ChatSession` or `Project`

Rules:

- No hero section behavior
- Summary cards should stay utilitarian
- Important counts, status, and recent context should be glanceable

### 9.2 ChatSession

ChatSession is the lightweight exploratory work surface.

#### Hierarchy

The eye should land in this order:

1. Composer
2. Current conversation content
3. Execution status
4. Starter prompts or guidance
5. Secondary controls

#### Empty State

- One compact title
- One line of explanation
- Visible composer
- At most 2 to 4 starter prompts
- No theatrical launch-screen behavior

#### Message Stream

- Optimize for reading, not bubble ornament
- Assistant replies should feel like annotated working notes
- Long answers should flow as continuous content
- Bubble styling should stay quiet

### 9.3 Project Space

Project Space is a formal execution surface.

Rules:

- Status must remain visible without hunting
- Section boundaries are stronger than in ChatSession
- Artifacts, runs, approvals, and audit context should be reachable from the current view
- Denser layouts are acceptable, but they must remain breathable

Persistent elements:

- Project header
- Current project status
- Secondary navigation
- Context or governance rail where needed

### 9.4 Approval and Governance Surfaces

Approval moments are explicit pauses, not decorative banners.

Rules:

- Present consequence summary first
- Show requested action second
- Offer one clear primary decision path
- Show safe alternative or cancel path
- Highlight risk through hierarchy and wording before using color

Governance surfaces should look stricter, not louder.

---

## 10. Iconography and Illustrative Detail

### 10.1 Icon Rules

- Default to linear icons
- Target a `1.5px` stroke feel
- Corners should feel consistent with the rest of the type system
- Monochrome by default
- State color only when the icon conveys a real semantic state

### 10.2 Recommended Set

SwarmMind uses `lucide-react` unless there is a strong reason not to.

Standard sizes:

- 16px for compact metadata
- 18px to 20px for common controls
- 24px for larger empty-state or header contexts

### 10.3 Illustration Policy

Illustration is not a primary identity layer for product surfaces.

Allowed:

- Sparse monochrome or two-tone empty-state marks
- Small schematic diagrams in docs or marketing surfaces

Forbidden:

- Playful mascot systems in core work surfaces
- Decorative product illustrations that compete with task content

---

## 11. Content Tone

SwarmMind copy should sound operational, calm, and clear.

Prefer:

- "输入问题或任务"
- "继续当前会话"
- "等待新的输入"
- "会话执行失败，可重试"
- "需要审批后继续"

Avoid:

- Hype language
- Whimsical assistant personality
- Overpromising autonomy
- Decorative slogans inside product surfaces

Copy rules:

- State what happened
- State what the user can do next
- Keep labels short
- Avoid human-like emotional filler

---

## 12. Accessibility and QA Gates

### 12.1 Non-Negotiable

- 44px minimum touch target for pointer-relevant controls
- Keyboard reachability for all core controls
- Visible focus states
- Semantic headings and landmarks
- Status communication not dependent on color alone
- High contrast on all neutral surfaces

### 12.2 Chat-Specific Gates

- Composer controls must be keyboard-usable
- Streaming state must remain understandable during motion
- Hover-only actions require keyboard fallback
- Long assistant output must preserve readable line length

### 12.3 Visual QA Gates

Before shipping a UI change, confirm:

- Chat and Project still feel meaningfully different
- No new cool gray drift entered the chassis
- No heavy blur or glass effect became structural
- Status colors remain desaturated
- White surfaces are used intentionally, not by default

---

## 13. Implementation Reference

### 13.1 CSS Variables Template

```css
:root {
  --warm-paper: #F7F7F5;
  --warm-ivory: #FAFAF8;
  --warm-mist: #F0EEEA;
  --warm-sand: #E8E6E0;
  --warm-border: #E5E3DD;
  --warm-ring: #D1CFC8;

  --neutral-50: #FAFAF8;
  --neutral-100: #F7F7F5;
  --neutral-150: #F0EEEA;
  --neutral-200: #E8E6E0;
  --neutral-300: #D8D6D0;
  --neutral-400: #B8B6B0;
  --neutral-500: #8A8882;
  --neutral-600: #6A6862;
  --neutral-700: #5A5852;
  --neutral-800: #3A3832;
  --neutral-900: #1E1E1C;

  --status-running: #5A7A96;
  --status-running-bg: #EEF1F4;
  --status-running-border: #D5DCE3;
  --status-approval: #B8956F;
  --status-approval-bg: #F5F0EA;
  --status-approval-border: #E5DDD3;
  --status-blocked: #A67C6B;
  --status-blocked-bg: #F3EEEB;
  --status-blocked-border: #E3D9D3;
  --status-done: #7A9A7E;
  --status-done-bg: #EDF2EE;
  --status-done-border: #D5E0D7;
  --status-chat: #8A8298;
  --status-chat-bg: #F0EEF3;
  --status-chat-border: #E0DCE6;
  --status-draft: #9A9894;
  --status-draft-bg: #F2F2F0;
  --status-draft-border: #E5E5E3;

  --font-display: "Newsreader", "Source Han Serif SC", "Noto Serif SC", Georgia, serif;
  --font-sans: "Geist", "PingFang SC", "Hiragino Sans GB", "Noto Sans SC", "Microsoft YaHei", sans-serif;
  --font-mono: "Geist Mono", "SFMono-Regular", "IBM Plex Mono", Menlo, Consolas, monospace;

  --radius-sm: 8px;
  --radius-md: 10px;
  --radius-lg: 12px;
  --radius-xl: 14px;
  --radius-2xl: 18px;
  --radius-3xl: 24px;

  --space-1: 4px;
  --space-2: 8px;
  --space-3: 12px;
  --space-4: 16px;
  --space-5: 20px;
  --space-6: 24px;
  --space-8: 32px;
  --space-10: 40px;
  --space-12: 48px;

  --shadow-ring: 0 0 0 1px var(--warm-ring);
  --shadow-whisper: 0 4px 12px rgba(0,0,0,0.04);
  --shadow-sticky: 0 -2px 20px rgba(0,0,0,0.06);
}

.dark {
  --background-dark: #1A1A18;
  --surface-dark: #242422;
  --surface-dark-muted: #2C2C29;
  --text-dark: #E8E6E0;
  --text-dark-muted: #B7B4AE;
  --border-dark: #3A3935;
}
```

### 13.2 Tailwind and React Guidance

- Map warm neutrals to the chassis first, then map semantic tokens
- Keep utility classes aligned with the token names above
- Prefer reusable surface and text utility classes over ad hoc one-off values
- If a component needs many inline hex values, the token model is incomplete

### 13.3 Existing UI Alignment

Current `ui/src/index.css` should continue to align with this file's token names and hierarchy. Future implementation work should prioritize:

- Adding `--font-display`
- Keeping current warm chassis values
- Preserving ring-shadow interaction patterns
- Tightening page-level separation between ChatSession and Project Space

---

## 14. Agent Prompt Guide

When asking an agent to design or refine SwarmMind UI, prompts should reference concrete roles, tokens, and hierarchy.

### 14.1 Good Prompt Structure

Specify:

- Which page archetype this is
- Which visual density it belongs to
- Which tokens should dominate
- Which component is primary
- Which state colors are allowed

### 14.2 Example Prompts

- "Design a `ChatSession` empty state on `--warm-paper (#F7F7F5)`. Keep the composer visually primary. Use a serif page title at 32px with calm operational tone, one-line supporting copy in 14px Geist, and at most three starter prompts."
- "Create a `Project Space` header with stronger containment than chat. Use `--warm-ivory` cards, `1px` warm borders, persistent status pills, and one primary action. No marketing hero behavior."
- "Refine an approval panel so consequence summary appears before actions. Use muted approval colors (`#B8956F` family), strong spacing hierarchy, and no decorative illustration."
- "Build a run log card using the dark code/log surface pattern: `#1A1A1A` background, quiet header strip, 13px mono text, low-saturation syntax."
- "Improve a toolbar with compact secondary buttons in warm sand, ghost utilities for minor actions, and 44px touch targets for icon buttons."

### 14.3 Prompting Anti-Patterns

Do not ask for:

- "Make it more futuristic"
- "Add some AI vibe"
- "Use a cooler dashboard palette"
- "Give it a modern SaaS gradient"
- "Make the chat page more fun"

---

## 15. Do and Don't

### 15.1 Do

- Keep the chassis warm and restrained
- Let borders and spacing do most of the structural work
- Use serif strategically for authority moments
- Keep status colors muted and semantic
- Preserve a real visual difference between ChatSession and Project Space
- Use quiet motion and localized loading states
- Make the composer feel like the anchor of chat
- Keep governance surfaces explicit and consequence-first

### 15.2 Don't

- Do not turn the product into a generic AI startup dashboard
- Do not rely on gradients or blur as identity
- Do not use cool blue-gray as the foundation
- Do not over-card every layout problem
- Do not use saturated semantic colors
- Do not let decorative type compete with dense operational UI
- Do not make approval surfaces feel playful
- Do not hide the next action in error states

---

## 16. Change Management

When changing product UI:

1. Update this file first if the decision affects more than one page or component family
2. Update implementation tokens and shared primitives
3. Update `docs/ui/*` if layout or interaction behavior changed

Review rule:

- If a UI change cannot be justified by this file, it should not ship
- If a new component introduces a color, shadow, or layout behavior not described here, extend this file before implementation

---

## 17. Ship Checklist

Before shipping any meaningful UI change, verify the following:

- The page still reads as SwarmMind rather than generic shadcn
- Warm paper, ivory, and muted borders still define the chassis
- Headline typography is deliberate and not overused
- ChatSession remains exploration-first
- Project Space remains execution-and-governance-first
- State colors remain desaturated and role-driven
- Focus states are visible and calm
- Error and approval states tell the user what to do next

---

*End of Design System v3.0*
