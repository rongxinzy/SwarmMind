# Agent Action Roadmap

> Document type: [B] agent execution guide.
> Audience: coding/design/product agents evolving SwarmMind from the current codebase.
> Rule: this document translates the target docs into action. It does not redefine product direction or architecture.

## 1. Mission

Every agent should advance the same product wedge:

**ChatSession -> DeerFlow execution -> visible state -> durable result -> Promote to Project -> governed project execution.**

If a task does not strengthen this path, it is probably platform breadth and should wait.

## 2. Source Order

When documents disagree, use this order:

1. `docs/product-positioning.md` for product bet and boundaries.
2. `docs/architecture.md` for terminology, runtime/control-plane boundaries, stores, and non-goals.
3. `docs/roadmap.md` for phase order and immediate milestones.
4. `DESIGN.md` for visual system, density, components, and UI style.
5. `docs/ui/*` for page structure, flows, and interaction details.
6. `AGENTS.md` for current implementation status and runnable commands.
7. `docs/sprint-*` for dated execution snapshots only.

Do not use sprint plans or current code to silently rewrite the target architecture. If the target is wrong, change the target docs explicitly first.

## 3. First Five Questions

Before coding, answer these in your scratch notes or PR summary:

1. Which phase does this work belong to: A, B, C, or D?
2. Which part of the main wedge does it improve?
3. Which control-plane state becomes more durable, visible, or recoverable?
4. Which DeerFlow detail is being hidden behind product language?
5. What user-visible behavior proves the slice is real?

If any answer is vague, narrow the slice before implementing.

## 4. Operating Loop

Use this loop for every meaningful product change:

1. **Orient**
   Read `AGENTS.md`, then the relevant target docs. Confirm current implementation with `rg`, tests, and local code inspection.

2. **Choose a Vertical Slice**
   Prefer one user-visible path over broad scaffolding. A slice should include backend state, API behavior, frontend surface, and tests when applicable.

3. **Preserve the Boundary**
   DeerFlow remains the only execution runtime. SwarmMind owns control-plane concepts such as `ChatSession`, `Project`, `Run`, `Artifact`, `Approval`, and `AuditLog`.

4. **Implement in Existing Shapes**
   Follow existing repository, service, route, React component, and shadcn/Tailwind patterns. Do not introduce a new framework or parallel runtime.

5. **Verify**
   Add or update focused tests. For UI work, verify light/dark behavior, text fit, interaction states, and Codex-like visual density.

6. **Update Status**
   If implementation status changes, update `AGENTS.md` or the relevant [B] plan. If product target changes, update the [A] docs explicitly.

## 5. Immediate Roadmap

### Track 0: UI v4 Convergence

Goal: make the implemented UI match `DESIGN.md` v4.0 and stop carrying the old warm/editorial style.

Work order:

1. Replace implementation-level warm/brass/serif styling with semantic v4 tokens.
2. Keep legacy `--warm-*` aliases only as migration compatibility, not as component language.
3. Convert floating-card-heavy surfaces into compact row groups, panels, tables, lists, settings rows, and native-feeling controls.
4. Validate light and dark themes against the Codex-like baseline:
   - accent `#339CFF`;
   - light background `#FFFFFF`;
   - dark background near `#181818`;
   - system UI font;
   - `ui-monospace` for code/log/diff surfaces.
5. Avoid new decorative gradients, parchment colors, heavy shadows, oversized cards, and serif headings.

Primary files:

- `DESIGN.md`
- `docs/ui/README.md`
- `ui/src/index.css`
- `ui/src/App.tsx`
- `ui/src/components/workspace/*`

Acceptance:

- UI reads as compact desktop software, not a landing page or notebook.
- Old v3 terms appear only as compatibility aliases or migration notes.
- Chat, Project, and settings-like surfaces share the same visual grammar.

### Track 1: ChatSession Reliability

Goal: keep the current work surface dependable before expanding platform breadth.

Work order:

1. Preserve stable create, switch, delete, recover, send, and stream behavior.
2. Keep model/mode language user-facing: fast, thinking, pro, ultra, planning, running, waiting, completed, blocked.
3. Make retry and failure states recoverable without losing the conversation.
4. Keep message persistence, titles, stream events, and trace references aligned.

Primary files:

- `swarmmind/services/conversation_execution.py`
- `swarmmind/services/conversation_support.py`
- `swarmmind/services/stream_events.py`
- `swarmmind/api/conversation_routes.py`
- `ui/src/components/workspace/*`
- `ui/src/core/chat/*`

Acceptance:

- A user can resume a recent conversation after refresh.
- A failed run leaves enough state to retry or explain failure.
- The UI never requires users to understand DeerFlow thread/checkpoint details.

### Track 2: Trace and Artifact Visibility

Goal: turn runtime execution into readable evidence without exposing raw checkpoints.

Work order:

1. Attach run identifiers and trace summary references to assistant outputs.
2. Produce a concise trace summary: steps, decisions, subagent activity, artifacts, blocked/waiting points.
3. Render trace as an expandable summary module, not raw runtime data.
4. Persist minimal artifact/evidence metadata that can later feed Project pages.

Primary files:

- `swarmmind/services/trace_service.py`
- `swarmmind/services/conversation_trace_service.py`
- `swarmmind/services/trace_provider.py`
- `swarmmind/services/trace_checkpoint_storage.py`
- `swarmmind/services/runtime_event_processing.py`
- `swarmmind/db_models.py`
- `swarmmind/repositories/*`
- `ui/src/components/workspace/*`

Acceptance:

- Completed runs can be explained from control-plane state.
- Trace output is useful to users and reviewers, not just developers.
- Artifact/evidence records have stable IDs and provenance.

### Track 3: Promote to Project

Goal: close the first real product loop from exploration to formal work.

Work order:

1. Add a minimal `Project` model, repository, API schema, and route.
2. Add a `Promote to Project` action from a valuable `ChatSession`.
3. Generate a structured project seed:
   - title;
   - goal;
   - scope;
   - constraints;
   - source conversation;
   - next step.
4. Keep the original ChatSession as provenance. Do not copy the raw chat into Project as the main state.
5. Render a Project page from real data, even if the page is still minimal.

Primary files:

- `swarmmind/db_models.py`
- `swarmmind/models.py`
- `swarmmind/repositories/conversation.py`
- `swarmmind/repositories/project.py`
- `swarmmind/api/conversation_routes.py`
- `swarmmind/api/supervisor.py`
- `ui/src/App.tsx`
- `ui/src/components/workspace/*`
- `docs/ui/30-projects-and-project-space.md`

Acceptance:

- A user can promote a completed session and land on a real Project page.
- The Project shows where it came from, what it is trying to do, and what happens next.
- The Project uses `project_id` as the formal boundary for future governance.

### Track 4: Governed Project Execution

Goal: make Project the enterprise execution boundary after Track 3 is real.

Work order:

1. Add `Run` records anchored on `project_id`.
2. Add minimal task and artifact surfaces only when they are fed by real project runs.
3. Add high-risk approval flow for real risk tiers, not ordinary low-risk actions.
4. Persist approval decisions and recovery behavior into audit history.
5. Introduce minimal project membership/RBAC only when Project collaboration needs it.

Primary files:

- `swarmmind/db_models.py`
- `swarmmind/repositories/*`
- `swarmmind/services/*`
- `swarmmind/api/*`
- `docs/ui/30-projects-and-project-space.md`
- `docs/ui/40-approval-center.md`

Acceptance:

- Project runs, artifacts, approvals, and audit entries share a stable `project_id`.
- High-risk actions pause with understandable approval context.
- Low-risk work remains fast and uncluttered.

### Track 5: Enterprise Scale

Goal: scale only after the main path has repeatable value.

Work order:

1. Add priority connectors based on actual Project needs.
2. Upgrade routing from keyword rules to embeddings/classifiers after enough labeled outcomes exist.
3. Add runtime pools by `tenant + runtime_profile_id` only after load or isolation requires it.
4. Add private skill/plugin governance after Project execution creates real governance pressure.

Do not start here unless Tracks 1-4 already prove the main loop.

## 6. Explicit Deferrals

Agents should not spend near-term effort on:

- full login, organization, and tenant administration;
- provider CRUD and API key management screens;
- broad placeholder pages for Teams, Skills, Knowledge, Assets, or Schedules;
- connector marketplace;
- generic multi-agent demos;
- a second workflow or agent runtime;
- raw DeerFlow checkpoint browsers as product UI.

These may become valid later, but only after the main wedge is useful.

## 7. Slice Template

Use this shape when proposing or implementing a new slice:

```text
Slice:
Phase:
Main wedge segment:
User-visible outcome:
Control-plane state touched:
Runtime boundary:
Files likely touched:
Tests / verification:
Docs to update:
Explicit non-goals:
```

Example:

```text
Slice: Promote completed ChatSession to minimal Project
Phase: B
Main wedge segment: durable result -> Promote to Project
User-visible outcome: user lands on a real Project page with title, goal, source, and next step
Control-plane state touched: ChatSessionStore, ProjectStore
Runtime boundary: source DeerFlow thread remains provenance; Project receives structured state
Files likely touched: db_models.py, models.py, repositories/project.py, conversation_routes.py, App.tsx
Tests / verification: repository tests, API tests, UI smoke test
Docs to update: AGENTS.md, docs/sprint-* if an active sprint exists
Explicit non-goals: full RBAC, project task engine, connector marketplace
```

## 8. Review Checklist

Before calling a change complete:

- It advances the main wedge.
- It preserves DeerFlow as the only runtime.
- It uses product terms instead of raw runtime terms.
- It creates durable state only where users, recovery, or governance need it.
- It is visible in the UI or API, not just scaffolded.
- It has focused tests or an explicit verification reason.
- It does not revive old v3 UI styling.
- It updates implementation-status docs when the status changed.

Good work here is not more surface area. Good work is a tighter path from a useful conversation to governed execution.
